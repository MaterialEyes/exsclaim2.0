from .figures import CRNN, ctc, non_max_suppression_malisiewicz, create_scale_bar_objects, ScalebarInfo, resize_transform
from .config import settings
from .exceptions import ExsclaimToolException
from .tool import ExsclaimTool
from .utilities import boxes, load_model_from_checkpoint, download_model_checkpoint

import cv2
import numpy as np
import torch
if settings.DISPLAY_TQDM:
	import tqdm
	# from .utilities.tqdm import set_stream_handlers_to_tqdm, remove_tqdm_from_set_stream_handlers

from pathlib import Path
from PIL import Image
from typing import Any, Generator, Optional


__all__ = ["FigureSeparator"]


def get_optional_path(path: Optional[str]) -> Optional[Path]:
	if path is None:
		return None
	return Path(path).resolve()


class FigureSeparator(ExsclaimTool):
	"""
	FigureSeparator object.
	Separate subfigure images from full figure image
	using CNN trained on crowdsourced labeled figures
	Parameters:
	None
	"""

	def __init__(self, search_query:dict, **kwargs):
		kwargs.setdefault("logger_name", __name__ + ".FigureSeparator")
		super().__init__(search_query, **kwargs)
		self.exsclaim_json = dict()
		self._get_unrecognized_image_folders()

	def _get_unrecognized_image_folders(self):
		self.undetected_path = settings.UNDETECTED_SUBFIGURES_PATH
		self.unclassified_path = settings.UNCLASSIFIED_SUBFIGURES_PATH

		for path in (self.undetected_path, self.unclassified_path):
			if path is not None:
				path.mkdir(parents=True, exist_ok=True)

	async def load(self, yolov11_subfigure_bbox: Optional[Path] = None, yolov11_subfigure_label: Optional[Path] = None,
				   yolov11_classifier: Optional[Path] = None):
		"""Load relevant models for the object detection tasks"""
		from ultralytics import YOLO
		from torchvision.models.detection import fasterrcnn_resnet50_fpn
		from torchvision.models.detection.faster_rcnn import FastRCNNPredictor, FasterRCNN_ResNet50_FPN_Weights

		# Set configuration variables
		figures_path = Path(__file__).parent.resolve() / "figures"
		checkpoint_path = settings.CHECKPOINTS_PATH
		self.cuda = torch.cuda.is_available()

		self.dtype = torch.cuda.FloatTensor if self.cuda else torch.FloatTensor
		if self.cuda:
			self.logger.info("Using CUDA.")

		self.device = torch.device("cuda" if self.cuda else "cpu")

		yolov11_subfigure_bbox = yolov11_subfigure_bbox or checkpoint_path / "yolov11_finetuned_augmentation_best.pt"
		yolov11_subfigure_label = yolov11_subfigure_label or checkpoint_path / "yolov11_label.pt"
		yolov11_classifier = yolov11_classifier or checkpoint_path / "yolov11_classification.pt"

		for model_file in (yolov11_subfigure_bbox, yolov11_subfigure_label, yolov11_classifier):
			if not model_file.is_file():
				await download_model_checkpoint(model_file)

		try:
			self.subfigure_bbox = YOLO(yolov11_subfigure_bbox)
			self.subfigure_bbox.to(self.device)
			self.logger.info("Subfigure bounding box model has been loaded.")

			self.subfigure_label = YOLO(yolov11_subfigure_label)
			self.subfigure_label.to(self.device)
			self.logger.info("Subfigure label bounding box model has been loaded.")

			self.classification_model = YOLO(yolov11_classifier)
			self.classification_model.to(self.device)
			self.logger.info("Subfigure classification model has been loaded.")
		except BaseException as e:
			self.logger.exception("Error loading YOLO models.")
			raise ExsclaimToolException from e

		# Common YOLO settings if needed
		self.confidence_threshold = 0.25  # Default confidence threshold
		self.image_size = 640  # Default YOLO image size

		# Load scale bar detection model
		# load an object detection model pre-trained on COCO
		scale_bar_detection_model = fasterrcnn_resnet50_fpn(weights=FasterRCNN_ResNet50_FPN_Weights.DEFAULT)

		input_features = scale_bar_detection_model.roi_heads.box_predictor.cls_score.in_features

		number_classes = 3  # background, scale bar, scale bar label
		scale_bar_detection_model.roi_heads.box_predictor = FastRCNNPredictor(input_features, number_classes)

		self.scale_bar_detection_model = await load_model_from_checkpoint(
			scale_bar_detection_model, "scale_bar_detection_model.pt", self.device,
		)

		# Load scale label recognition model
		config_path = figures_path / "config" / "scale_label_reader.json"
		with open(config_path, "r") as f:
			from orjson import loads
			configuration_file = loads(f.read())

		configuration = configuration_file["theta"]
		scale_label_recognition_model = CRNN(configuration=configuration)

		self.scale_label_recognition_model = await load_model_from_checkpoint(
			scale_label_recognition_model, "scale_label_recognition_model.pt", self.device
		)

	async def unload(self):
		if self.cuda:
			torch.cuda.empty_cache()
			for model in (self.subfigure_bbox, self.classification_model, self.scale_bar_detection_model, self.scale_label_recognition_model):
				# Remove the model from the GPU
				model.to("cpu")
			del model

	def _update_exsclaim(self, exsclaim_dict: dict, figure: dict):
		figure_name = figure["figure_name"].split("/")[-1]

		exsclaim_dict[figure_name]["master_images"].extend(figure["master_images"])

		return exsclaim_dict

	async def run(self, search_query: dict, exsclaim_dict: dict[str, Any]):
		"""Run the models relevant to manipulating article figures"""
		exsclaim_dict = exsclaim_dict or dict()
		append_file = "_figures"
		path = self.results_directory / "figures"

		self.display_info(f"Running Figure Separator\n")
		self.results_directory.mkdir(exist_ok=True)

		t0 = self._start_timer()
		# List of objects (figures, captions, etc.) that have already been separated
		file = self.results_directory / "_figures"

		if file.is_file():
			with open(file, "r", encoding="utf-8") as f:
				separated = {line.strip() for line in f.readlines()}
		else:
			separated = set()

		with open(file, "w", encoding="utf-8") as f:
			for figure in separated:
				f.write(f"{Path(figure).name}\n")
		# Figure extra goes here
		new_separated = set()

		counter = 1
		figures = tuple(
			path / value["figure_name"]
			for value in exsclaim_dict.values()
			if value["figure_name"] not in separated
		)

		figures_enum = enumerate(figures, start=counter)
		# if settings.DISPLAY_TQDM:
		# 	figures_enum = tqdm.tqdm(figures_enum, total=len(figures), desc="Separating Figures", unit="fig")
			# set_stream_handlers_to_tqdm(self.logger, figures_enum)

		for counter, _path in figures_enum:
			self.display_info(f">>> ({counter:,} of {+len(figures):,}) Extracting images from: {_path}")

			try:
				figure_json = self.extract_image_objects(_path.name)
				new_separated.add(_path.name)
				exsclaim_dict = self._update_exsclaim(exsclaim_dict, figure_json)
			except Exception as e:
				self.display_exception(e, _path)
				raise e

			# Save to file every N iterations (to accommodate restart scenarios)
			if counter % 1_000 == 0:
				self._appendJSON(exsclaim_dict, data=new_separated, filename=append_file)
				new_separated = set()

		# remove_tqdm_from_set_stream_handlers(self.logger)
		self._end_timer(t0, f"{counter:,} figures")
		self._appendJSON(exsclaim_dict, data=new_separated, filename=append_file)
		return exsclaim_dict

	def read_scale_bar(self, cropped_image: Image.Image) -> ctc.Results:
		"""Outputs the text of an image cropped to a scale bar label bbox

		Args:
			cropped_image (Image): An PIL RGB image cropped to the bounding box
				of a scale bar label.
		Returns:
			label_text (string): The text of the scale bar label
		"""
		image, classes = resize_transform(cropped_image)
		# run image on model
		logps = self.scale_label_recognition_model(image.to(self.device))
		probs = torch.exp(logps)
		probs = probs.squeeze(0)
		yield from ctc.run_ctc(probs, classes, self.logger)

	@staticmethod
	def assign_scale_objects_to_subfigures(master_image: dict, scale_objects: list[dict]) -> tuple[dict, list[dict]]:
		"""Assign scale bar objects to master images

		Args:
			master_image (Master Image Json): A Master Image JSON
			scale_objects (list of Scale Object JSON): candidate scale objects
		Returns:
			master_image (Master Image JSON): updated with scale objects
			scale_objects: updated with assigned objects removed
		"""
		geometry = master_image["geometry"]
		x1, y1, x2, y2 = boxes.convert_labelbox_to_coords(geometry)
		unassigned_scale_objects = []
		assigned_scale_objects = []

		for scale_object in scale_objects:
			if boxes.is_contained(scale_object["geometry"], geometry):
				assigned_scale_objects.append(scale_object)
			else:
				unassigned_scale_objects.append(scale_object)
		master_image["scale_bars"] = assigned_scale_objects

		# find if there is one unique scale bar label
		nm_to_pixel = 0
		label = ""
		scale_labels = set()
		for scale_object in master_image["scale_bars"]:
			if scale_object["label"]:
				scale_labels.add(scale_object["label"]["nm"])
				nm_to_pixel = scale_object["label"]["nm"] / float(scale_object["length"])
				label = scale_object["label"]["text"]

		if len(scale_labels) == 1:
			master_image.update(dict(
				nm_height=int(nm_to_pixel * master_image.get("height", y2 - y1) * 10) / 10,
				nm_width=int(nm_to_pixel * master_image.get("width", x2 - x1) * 10) / 10,
				scale_label=label
			))
		return master_image, unassigned_scale_objects

	def detect_scale_objects(self, image: torch.Tensor) -> list[ScalebarInfo]:
		"""Detects bounding boxes of scale bars and scale bar labels

		Args:
			image (torch.Tensor): An image tensor
		Returns:
			scale_bar_info (list): A list of lists with the following
				pattern: [[x1,y1,x2,y2, confidence, label],...] where
				label is 1 for scale bars and 2 for scale bar labels
		"""
		# prediction
		self.scale_bar_detection_model.eval()
		with torch.no_grad():
			outputs = self.scale_bar_detection_model([image.to(self.device)])

		# post-process
		scale_bar_info = []
		for i, box in enumerate(outputs[0]["boxes"]):
			confidence = outputs[0]["scores"][i]
			if confidence > 0.5:
				x1, y1, x2, y2 = box
				label = outputs[0]["labels"][i]
				scale_bar_info.append(ScalebarInfo(
					x1.data.cpu(),
					y1.data.cpu(),
					x2.data.cpu(),
					y2.data.cpu(),
					confidence.data.cpu(),
					label.data.cpu(),
				))
		scale_bar_info = non_max_suppression_malisiewicz(
			np.asarray(scale_bar_info), 0.4
		)
		return scale_bar_info

	def determine_scale(self, figure_path: Path, figure_json: dict[str, Any]) -> dict[str, Any]:
		"""Adds scale information to figure by reading and measuring scale bars

		Args:
			figure_path (str): A path to the image (.png, .jpg, or .gif)
				file containing the article figure
			figure_json (dict): A Figure JSON
		Returns:
			figure_json (dict): A dictionary with classified image_objects
				extracted from figure
		"""
		from torchvision import transforms

		convert_to_nm = {
			"a":              0.1,
			"nm":             1.0,
			"um":         1_000.0,
			"mm":     1_000_000.0,
			"cm":    10_000_000.0,
			"m":  1_000_000_000.0,
		}
		unassigned = figure_json.get("unassigned", dict())
		unassigned_scale_labels = unassigned.get("scale_bar_labels", list())
		master_images = figure_json.get("master_images", list())
		image = Image.open(figure_path).convert("RGB")
		tensor_image = transforms.ToTensor()(image)

		# Detect scale bar objects
		scale_bar_info = self.detect_scale_objects(tensor_image)
		label_names = ["background", "scale bar", "scale label"]
		scale_bars = []
		scale_labels = []

		for scale_object in scale_bar_info:
			x1, y1, x2, y2, confidence, classification = scale_object
			geometry = boxes.convert_coords_to_labelbox(int(x1), int(y1), int(x2), int(y2))
			
			match label_names[int(classification)]:
				case "scale bar":
					scale_bars.append(dict( # Scale bar JSON
						geometry=geometry,
						confidence=float(confidence),
						length=int(x2 - x1),
					))
				case "scale label":
					scale_bar_label_image = image.crop((int(x1), int(y1), int(x2), int(y2)))

					# Read Scale Text
					for (magnitude, unit, label_confidence) in self.read_scale_bar(scale_bar_label_image):
						# 0 is never correct and -1 is the error value
						if magnitude <= 0:
							continue

						length_in_nm = magnitude * convert_to_nm[unit.strip().lower()]
						scale_labels.append(dict(
							geometry=geometry,
							text=f"{magnitude} {unit}",
							label_confidence=float(label_confidence),
							box_confidence=float(confidence),
							nm=int(length_in_nm * 100) / 100,
						))

		# Match scale bars to labels and to subfigures (master images)
		scale_bar_jsons, unassigned_labels = create_scale_bar_objects(scale_bars, scale_labels)
		for master_image in master_images:
			master_image, scale_bar_jsons = self.assign_scale_objects_to_subfigures(master_image, scale_bar_jsons)

		# Save info to JSON
		unassigned["scale_bar_labels"] = unassigned_scale_labels
		unassigned["scale_bar_lines"] = scale_bar_jsons
		figure_json["unassigned"] = unassigned
		figure_json["master_images"] = master_images

		return figure_json

	def get_bounding_boxes(self, figure_path: Path, model):
		# Run YOLO detection with higher confidence threshold
		results = model.predict(
			source=figure_path,
			imgsz=self.image_size,
			conf=0.6,
			iou=0.45,
			max_det=100,
			agnostic_nms=False,
			stream=False,
			verbose=settings.DEBUG
		)
		result = results[0]

		# Process detections
		detections_per_class = dict()

		for box in result.boxes:
			cls_id = int(box.cls[0])
			conf = box.conf[0]
			if cls_id not in detections_per_class or conf > detections_per_class[cls_id].conf[0]:
				detections_per_class[cls_id] = box
		# print(f"{detections_per_class=}")
		return detections_per_class

	def extract_image_objects(self, figure_path: str) -> dict:
		"""Separate and classify subfigures in an article figure

		Args:
			figure_path (str): A path to the image (.png, .jpg, or .gif)
				file containing the article figure
		Returns:
			figure_json (dict): A dictionary with classified image_objects
				extracted from figure
		"""
		from contextlib import suppress

		# Get full path to figure
		figure_path = self.results_directory / "figures" / figure_path

		img: np.ndarray = cv2.imread(figure_path, cv2.IMREAD_COLOR)
		height, width, _ = img.shape
		binary_img = np.zeros((height, width, 1))

		# Get figure name without extension for directory naming
		figure_base_name = figure_path.stem

		detections_per_class = self.get_bounding_boxes(figure_path, self.subfigure_bbox)
		subfigures_per_class = self.get_bounding_boxes(figure_path, self.subfigure_label)

		# Initialize variables
		figure_name = figure_path.name
		figure_json = self.exsclaim_json.get(figure_name, dict())
		figure_json.update(dict(
			figure_name=figure_name,
			master_images=[]
		))

		if len(detections_per_class) == 0:
			self.logger.info(f"{figure_path} could not detect any subfigures.")
			if self.undetected_path is not None:
				cv2.imwrite(self.undetected_path / figure_path.name, img)

		# Process each final detection
		for cls_id, box in detections_per_class.items():
			x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
			label_box = subfigures_per_class.get(cls_id, None)
			if label_box is not None:
				lx1, ly1, lx2, ly2 = label_box.xyxy[0].cpu().numpy()
			else:
				lx1, ly1, lx2, ly2 = None, None, None, None
			conf = float(box.conf[0])

			# Ensure coordinates are within bounds and boxes aren't too small
			x1 = int(min(max(x1, 0), width - 1))
			y1 = int(min(max(y1, 0), height - 1))
			x2 = int(min(max(x2, 0), width))
			y2 = int(min(max(y2, 0), height))

			dx = x2 - x1	# Change in x coordinates (width)
			dy = y2 - y1	# Change in y coordinates (height)

			if dx <= 5 or dy <= 5:
				continue

			# Get the label
			label = self.subfigure_bbox.names[cls_id]		# This will be 'a', 'b', 'c', etc.

			# Add to binary mask for visualization if small enough
			if dx < 64 and dy < 64:
				binary_img[y1:y2, x1:x2] = 255

			# Get the subfigure classification
			classification_results = self.classification_model.predict(
				source=img[y1:y2, x1:x2],
				imgsz=self.image_size,
				conf=0.6,
				iou=0.45,
				max_det=100,
				agnostic_nms=False,
				stream=False,
				verbose=settings.DEBUG
			)

			result = classification_results[0]
			if result.probs is not None:
				classification = result.names[result.probs.top1]
				class_conf = float(result.probs.top1conf)
			else:
				self.logger.exception(f"Could not classify subfigure {figure_path} (label {label}) -- result.probs is None.")
				classification = "unclear"
				class_conf = 0
				if self.unclassified_path is not None:
					cv2.imwrite(self.unclassified_path / f"{figure_path.stem}-{label}{figure_path.suffix}", img)

			# Create master_image_info
			master_image_info = {
				"classification": classification,
				"classification_confidence": float(class_conf),
				"confidence": float(conf),
				"height": dy,
				"width": dx,
				"geometry": dict(
					x0=x1,
					y0=y1,
					x1=x2,
					y1=y2
				),
				"subfigure_label": {
					"text": label,
					"geometry": dict(
						x0=int(lx1),
						y0=int(ly1),
						x1=int(lx2),
						y1=int(ly2)
					)
				}
			}

			# Create output directory structure using figure_base_name (without extension)
			subfigure_directory = self.results_directory / "images" / figure_base_name / label
			subfigure_directory.mkdir(parents=True, exist_ok=True)

			# Crop and save using base name for output filename
			cropped_img = img[y1:y2, x1:x2]
			cv2.imwrite(str(subfigure_directory / f"{figure_base_name}_{label}.png"), cropped_img)
			figure_json["master_images"].append(master_image_info)

		# Sometimes the system will have a problem with PIL and Enums
		with suppress(TypeError):
			figure_json = self.determine_scale(figure_path, figure_json)

		return figure_json
