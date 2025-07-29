import pymupdf

from .caption import LLM, ChatMessage, Captions
from .exceptions import PDFScrapeException
from .tool import ExsclaimTool

from asyncio import gather, Lock
from base64 import b64encode
from io import BytesIO
from pathlib import Path
from typing import Any
from textwrap import dedent


__all__ = ["PDFScraper"]


class PDFScraper(ExsclaimTool):
	def __init__(self, search_query:dict, **kwargs):
		kwargs.setdefault("logger", __name__ + ".PDFScraper")
		super().__init__(search_query, **kwargs)

		if "pdf_path" not in search_query:
			raise PDFScrapeException("No pdf_path provided.")

		pdf_path = Path(search_query["pdf_path"]).resolve()
		if not (pdf_path.exists() and pdf_path.is_dir()):
			raise PDFScrapeException(f"\"{pdf_path}\" does not exist or is not a directory.")

		self.pdf_path = pdf_path
		self.new_pdfs_visited = set()

	async def load(self):
		await LLM.from_search_query(self.search_query).load()

	async def unload(self):
		await LLM.from_search_query(self.search_query).unload()

	def extract_authors_from_pdf(self, pdf:pymupdf.Document) -> list[str]:
		metadata = pdf.metadata
		authors = metadata.get("author", None)

		if authors:
			return authors

		self.logger.info(f"No authors found in {pdf.article}'s metadata, returning empty list.")
		return []

	def extract_title_from_pdf(self, pdf: pymupdf.Document) -> str:
		metadata = pdf.metadata
		title = metadata.get("title", None)

		if title:
			return title

		# If there is no title in the metadata, try to extract from text in the first page
		self.logger.info(f"No title found in {pdf.article}'s metadata, using text from the first page.")
		first_page = pdf.load_page(0)
		text = first_page.get("text")
		first_lines = text.splitlines()[:5]
		return " ".join(first_lines).strip()

	def extract_images_from_pdf(self, pdf: pymupdf.Document, figures_path: Path, logo_hashes: set[str]) -> list[dict[str, Any]]:
		image_metadata = []

		article = pdf.article
		for page_num, page in enumerate(pdf.pages()):
			# Get images on the page with detailed info
			image_list = page.get_images(full=True)
			images = []

			for image in image_list:
				# Get the XREF of the image
				xref = image[0]

				# Get the rectangles where this image is used
				rects = page.get_image_rects(xref)

				if rects:
					for rect in rects:
						images.append(dict(xref=xref, rect=rect))
				else:
					self.logger.info(f"No rectangles found for image xref {xref} on page {page_num+1:,}.")

			if not images:
				self.logger.info(f"No images with positions found on page {page_num+1:,}.")
				continue

			# Get the page width to determine left and right halves
			page_width = page.rect.width
			half_width = page_width / 2

			# Classify images into left and right based on x_center
			left_images, right_images = [], []

			for image in images:
				rect = image["rect"]
				image.update(dict(
					x_center=(rect.x0 + rect.x1) / 2,
					y_top=rect.y1	# Top edge of the image
				))

				if image["x_center"] < half_width:
					left_images.append(image)
				else:
					right_images.append(image)

			# Sort images in each group from top to bottom (higher y to lower y)
			left_images.sort(key=lambda img: img["y_top"], reverse=True)
			right_images.sort(key=lambda img: img["y_top"], reverse=False)

			# Combine the lists: left images first, right images second
			sorted_images = left_images + right_images

			# Save images in the sorted order
			for image_num, image in enumerate(sorted_images):
				xref = image["xref"]
				rect = image["rect"]

				try:
					# Create a pixmap
					pix = pymupdf.Pixmap(pdf, xref)

					# Skip logo images
					if pix.digest.hex() in logo_hashes:
						self.logger.info(f"Skipping logo xref {xref} on page {page_num+1:,} in article {article}.")
						continue

					# Skip images with NULL colorspace
					if pix.colorspace is None:
						self.logger.info(f"Skipping image xref {xref} on page {page_num+1:,} in article {article} due to NULL colorspace.")
						continue

					# Skip small images (e.g., logos) based on size
					image_width = pix.width
					image_height = pix.height

					if image_width <= 100 and image_height <= 100:
						self.logger.info(f"Skipping small image xref {xref} on page {page_num+1:,} in article {article} (likely a logo).")
						continue

					# Convert CMYK and other unsupported color spaces RGB
					if pix.colorspace.name == "DeviceCMYK" or pix.n > 4:
						self.logger.info(f"Converting image xref {xref} from color space {pix.colorspace.name} to RGB.")
						pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
					# Convert grayscale images to RGB
					elif pix.colorspace.n == 1:
						self.logger.info(f"Converting image xref {xref} from grayscale to RGB.")
						pix = pymupdf.Pixmap(pymupdf.csRGB, pix)

					# Save the image as PNG
					image_filename = f"{article}_p{page_num+1}_img_{image_num+1}.png"
					pix.save(figures_path / image_filename)
					del pix # Free resources

					image_metadata.append(dict(
						page_num=page_num+1,
						image_num=image_num+1,
						image_filename=image_filename,
						rect=[rect.x0, rect.y0, rect.x1, rect.y1]
					))
				except Exception:
					self.logger.exception(f"Error processing image xref {xref} on page {page_num+1:,}.")

		return image_metadata

	async def read_figure_captions(self, encoded_image:str) -> dict[str, Any]:
		prompt = dedent("""\
			The provided image is a page from a literature paper. Please perform the following steps as accurately as possible:
	        1. Identify and return in the correct order they are located (the index 0 figure or scheme is located on the top left of the page) in the page the figure name and the full caption that describe the figure or scheme depicted on this page.
	        2. If a figure caption or scheme is not found directly above or under the image then do not consider it as an image caption or scheme and return 'N/A'.
	        3. If a figure doesn't have a directly associated caption found directly above or under the image that starts with 'Fig.' or 'Figure' or 'Scheme' return 'N/A'. 
	        4. The figure name or scheme should be found directly above or under the figure and not as part of the main text.
	        5. You should not extract image captions from the paper abstract or toc of the paper.
	        6. Provide the full caption without splitting it or modifying the content or adding a figure name that is not directly associated with the image.
	       """)

		llm = self.search_query["llm"]
		model_key = self.search_query.get("model_key", None)
		llm = LLM(llm, model_key)

		messages = [
			ChatMessage(role="user", content=prompt, images=[encoded_image], temperature=0),
		]

		captions = await llm.get_response(messages, Captions)
		return captions.captions

	async def extract_captions_from_pdf(self, pdf: pymupdf.Document, dpi:int = 300, check_toc: bool = False) -> dict[int, list[str]]:
		captions = dict()

		for page_num, page in enumerate(pdf.pages()):
			# Extract text from the page
			page_text = page.get_text()

			# Check if the page is the Table of Contents
			if check_toc and "table of contents" in page_text.lower() or "contents" in page_text.lower():
				self.logger.info(f"Skipping page {page_num + 1} in {pdf.article} as it appears to be Table of Contents.")
				continue

			scale_factor = dpi / 72
			pix = page.get_pixmap(matrix=pymupdf.Matrix(scale_factor, scale_factor))

			image_bytes = BytesIO(pix.tobytes())
			encoded_image = b64encode(image_bytes.read()).decode("utf-8")

			extracted_data = await self.read_figure_captions(encoded_image)

			page_captions = extracted_data.values()
			page_captions = [" ".join(caption) if isinstance(caption, list) else caption for caption in page_captions]

			captions[page_num+1] = page_captions

		return captions

	@staticmethod
	def match_images_with_captions(image_metadata:list[dict[str, Any]], captions: dict[int, list[str]]) -> list[dict[str, Any]]:
		for meta in image_metadata:
			page_num = meta["page_num"]

			# Convert dict_values to list for indexing
			page_captions = list(captions.get(page_num, []))

			# Assign captions in order if there are captions available
			if page_captions:
				img_index = image_metadata.index(meta) % len(page_captions)
				meta["captions"] = page_captions[img_index]
			else:
				meta["captions"] = "N/A"

		return image_metadata

	async def save_figures_pdf(self, filename: Path, pdf: pymupdf.Document, figures_path: Path, logo_hashes: set[str] = None,
							   verbose:bool = False) -> dict[str, Any]:
		logo_hashes = logo_hashes or {
			"3b4c0ee6601485a77bac913ee230cec8", "cde2017ee1dd0136c9ae78f4cb37ddd3"
			# "a6030f1bba4aa390c453d28c14a58c1d", "4c01d3acab441ccc10381b6a62afa238",
			# "7caa14a242ee374229c8d081852e1b57", "91623e2a4e1255c78ca3c88aae5ff690",
		}

		article = filename.stem
		pdf.article = article
		title = self.extract_title_from_pdf(pdf)
		authors = self.extract_authors_from_pdf(pdf)

		# Extract images from PDF
		image_metadata = self.extract_images_from_pdf(pdf, figures_path, logo_hashes)

		# Extract captions from PDF
		captions = await self.extract_captions_from_pdf(pdf)

		# Match images with captions
		matched_metadata = self.match_images_with_captions(image_metadata, captions)

		article_json = dict()

		for figure_num, figure in enumerate(matched_metadata):
			valid_captions = tuple(filter(lambda caption: caption != "N/A" and caption.strip(), figure["captions"]))

			if not valid_captions:
				continue

			if verbose:
				print(f"Image: {figure['image_filename']}, Page: {figure['page_num']}, Captions: {figure['captions']}")

			figure_name = figure["image_filename"]
			figure_path = figures_path / figure_name

			figure_json = {
				"title": title,
				"authors": authors,
				"article_name": article,
				"image_url": "",
				"figure_name": figure_name,
				"full_caption": figure["captions"],
				"figure_path": str(figure_path),
				"master_images": [],
				"article_url": [],
				"license": [],
				"open": [],
				"unassigned": {
					"master_images": [],
					"dependent_images": [],
					"inset_images": [],
					"subfigure_labels": [],
					"scale_bar_labels": [],
					"scale_bar_lines": [],
					"captions": [],
				},
			}

			# Add all results
			article_json[figure_name] = figure_json

		return article_json

	async def runner(self, exsclaim_json: dict, lock:Lock, pdf_loc: Path):
		t0 = self._start_timer()
		article = pdf_loc.stem
		self.display_info(f">>> Extracting figures from: {article.split('/')[-1]}")

		figures_path = self.results_directory / "figures"
		pdfs_path = self.results_directory / "pdfs"

		for path in (figures_path, pdfs_path):
			path.mkdir(exist_ok=True, parents=True)

		try:
			pdf = pymupdf.open(pdf_loc)

			pdf_text = "\n".join(page.get_text() for page in pdf.pages())

			file_path = pdfs_path / pdf_loc.with_suffix(".txt").name
			file_path.write_text(pdf_text, encoding="utf-8")

			article_dict = await self.save_figures_pdf(pdf_loc, pdf, figures_path)

			async with lock:
				self._update_exsclaim(exsclaim_json, article_dict)
		except Exception as e:
			self.display_exception(e, pdf_loc)

		self._end_timer(t0, f"PDFScraper: {pdf_loc}")

	async def run(self, search_query: dict, exsclaim_json: dict):
		lock = Lock()

		await gather(*[
			self.runner(exsclaim_json, lock, pdf_loc) for pdf_loc in self.pdf_path.glob("*.pdf", case_sensitive=False)
		])

		return exsclaim_json
