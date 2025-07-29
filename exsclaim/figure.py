from .figures import CRNN, ctc, non_max_suppression_malisiewicz, create_scale_bar_objects, ScalebarInfo, resize_transform
from .exceptions import ExsclaimToolException
from .tool import ExsclaimTool
from .utilities import boxes, load_model_from_checkpoint, download_model_checkpoint

import cv2
import numpy as np
import torch

from contextlib import suppress
from json import load
from pathlib import Path
from PIL import Image
from torchvision import transforms
from torchvision.models.detection import fasterrcnn_resnet50_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor, FasterRCNN_ResNet50_FPN_Weights
from typing import Any
from ultralytics import YOLO


__all__ = ["FigureSeparator"]


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
		self.exsclaim_json = {}

	async def load(self):
		"""Load relevant models for the object detection tasks"""
		# Set configuration variables
		figures_path = Path(__file__).resolve().parent / "figures"
		self.cuda = torch.cuda.is_available()

		self.dtype = torch.cuda.FloatTensor if self.cuda else torch.FloatTensor
		if self.cuda:
			self.logger.info("Using CUDA.")

		self.device = torch.device("cuda" if self.cuda else "cpu")

		yolov11_load = figures_path / "checkpoints" / "yolov11_finetuned_augmentation_best.pt"

		if not yolov11_load.is_file():
			await download_model_checkpoint(yolov11_load)

		try:
			self.yolo_model = YOLO(yolov11_load)
			self.yolo_model.to(self.device)
		except BaseException as e:
			self.logger.exception("Error loading YOLO model.")
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
			scale_bar_detection_model, "scale_bar_detection_model.pt", self.cuda, self.device,
		)

		# Load scale label recognition model
		config_path = figures_path / "config" / "scale_label_reader.json"
		with open(config_path, "r") as f:
			configuration_file = load(f)

		configuration = configuration_file["theta"]
		scale_label_recognition_model = CRNN(configuration=configuration)

		self.scale_label_recognition_model = await load_model_from_checkpoint(
			scale_label_recognition_model, "scale_label_recognition_model.pt", self.cuda, self.device
		)

	async def unload(self):
		torch.cuda.empty_cache()
		for model in (self.yolo_model, self.scale_bar_detection_model, self.scale_label_recognition_model):
			# Remove the model from the GPU
			if self.cuda:
				model.to("cpu")
			del model

	def _update_exsclaim(self, exsclaim_dict:dict, figure:dict):
		figure_name = figure["figure_name"].split("/")[-1]

		exsclaim_dict[figure_name]["master_images"].extend(figure["master_images"])

		# for key, value in figure["unassigned"].items():
		# 	exsclaim_dict[figure_name]["unassigned"][key].extend(value)

		return exsclaim_dict

	async def run(self, search_query:dict, exsclaim_dict: dict[str, Any]):
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

		for counter, _path in enumerate(figures, start=counter):
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

		self._end_timer(t0, f"{counter:,} figures")
		self._appendJSON(exsclaim_dict, data=new_separated, filename=append_file)
		return exsclaim_dict

	def read_scale_bar(self, cropped_image:Image) -> tuple[float, str, float]:
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
		magnitude, unit, confidence = ctc.run_ctc(probs, classes)
		return magnitude, unit, float(confidence)

	@staticmethod
	def assign_scale_objects_to_subfigures(master_image:dict, scale_objects:list[dict]) -> tuple[dict, list[dict]]:
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

	def detect_scale_objects(self, image:Image) -> list[ScalebarInfo]:
		"""Detects bounding boxes of scale bars and scale bar labels

		Args:
			image (PIL Image): A PIL image object
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

	def determine_scale(self, figure_path:Path, figure_json:dict[str, Any]) -> dict[str, Any]:
		"""Adds scale information to figure by reading and measuring scale bars

		Args:
			figure_path (str): A path to the image (.png, .jpg, or .gif)
				file containing the article figure
			figure_json (dict): A Figure JSON
		Returns:
			figure_json (dict): A dictionary with classified image_objects
				extracted from figure
		"""
		convert_to_nm = {
			"a":              0.1,
			"nm":             1.0,
			"um":         1_000.0,
			"mm":     1_000_000.0,
			"cm":    10_000_000.0,
			"m":  1_000_000_000.0,
		}
		unassigned = figure_json.get("unassigned", {})
		unassigned_scale_labels = unassigned.get("scale_bar_labels", [])
		master_images = figure_json.get("master_images", [])
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
					magnitude, unit, label_confidence = self.read_scale_bar(scale_bar_label_image)

					# 0 is never correct and -1 is the error value
					if magnitude > 0:
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

	def extract_image_objects(self, figure_path:str) -> dict:
		"""Separate and classify subfigures in an article figure

		Args:
			figure_path (str): A path to the image (.png, .jpg, or .gif)
				file containing the article figure
		Returns:
			figure_json (dict): A dictionary with classified image_objects
				extracted from figure
		"""
		# Get full path to figure
		figure_path = self.results_directory / "figures" / figure_path

		img = cv2.imread(str(figure_path), cv2.IMREAD_COLOR)
		height, width, _ = img.shape
		binary_img = np.zeros((height, width, 1))

		# Get figure name without extension for directory naming
		figure_base_name = figure_path.stem

		# Run YOLO detection with higher confidence threshold
		results = self.yolo_model.predict(
			source=figure_path,
			imgsz=self.image_size,
			conf=0.6,
			iou=0.45,
			max_det=100,
			agnostic_nms=False
		)

		# Initialize variables
		figure_name = figure_path.name
		figure_json = self.exsclaim_json.get(figure_name, {})
		figure_json.update(dict(
			figure_name=figure_name,
			master_images=[]
		))

		# Process detections
		detections_per_class = {}

		if results[0].boxes.shape[0] == 0:
			self.logger.info(f"{figure_path} could not detect any subfigures.")

		for result in results:
			for box in result.boxes:
				cls_id = int(box.cls[0])
				conf = box.conf[0]
				if cls_id not in detections_per_class or conf > detections_per_class[cls_id].conf[0]:
					detections_per_class[cls_id] = box

		# Process each final detection
		for cls_id, box in detections_per_class.items():
			x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
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
			label = self.yolo_model.names[cls_id]		# This will be 'a', 'b', 'c', etc.

			# Add to binary mask for visualization if small enough
			if dx < 64 and dy < 64:
				binary_img[y1:y2, x1:x2] = 255

			# TODO: Reimplement classify_subfigures with this update method

			# Create master_image_info
			master_image_info = {
				"classification": "subfigure",
				"confidence": float(conf),
				"height": dy,
				"width": dx,
				"geometry": [
					{"x": x1, "y": y1},
					{"x": x2, "y": y1},
					{"x": x1, "y": y2},
					{"x": x2, "y": y2}
				],
				"subfigure_label": {
					"text": label,
					"geometry": [
						{"x": x1, "y": y1},
						{"x": x2, "y": y1},
						{"x": x1, "y": y2},
						{"x": x2, "y": y2}
					]
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
