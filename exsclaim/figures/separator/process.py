from __future__ import division

from typing import NamedTuple
import cv2
import numpy as np
import torch


__all__ = ["label2yolobox", "yolobox2label", "nms", "postprocess", "preprocess_mask", "preprocess", "ImageInfo"]


class ImageInfo(NamedTuple):
	height: int
	width: int
	new_height: int
	new_width: int
	dx: int
	dy: int


def label2yolobox(labels:np.ndarray, info_img:ImageInfo, maxsize:int, lrflip:bool) -> np.ndarray:
	"""
	Transform coco labels to yolo box labels
	Args:
		labels (numpy.ndarray): label data whose shape is :math:`(N, 5)`.
			Each label consists of [class, x1, y1, x2, y2] where \
				class (float): class index.
				x1, y1, x2, y2 (float) : coordinates of \
					left-top and right-bottom points of bounding boxes.
					Values range from 0 to width or height of the image.
		info_img : tuple of height, width, new_height, new_width, dx, dy.
			height, width (int): original shape of the image
			new_height, new_width (int): shape of the resized image without padding
			dx, dy (int): pad size
		maxsize (int): target image size after pre-processing
		lrflip (bool): horizontal flip flag

	Returns:
		labels:label data whose size is :math:`(N, 5)`.
			Each label consists of [class, xc, yc, width, height] where
				class (float): class index.
				xc, yc (float) : center of bbox whose values range from 0 to 1.
				width, height (float) : size of bbox whose values range from 0 to 1.
	"""
	height, width, new_height, new_width, dx, dy = info_img
	x1 = labels[:, 1] / width
	y1 = labels[:, 2] / height
	x2 = (labels[:, 1] + labels[:, 3]) / width
	y2 = (labels[:, 2] + labels[:, 4]) / height

	labels[:, 1] = (((x1 + x2) / 2) * new_width + dx) / maxsize
	labels[:, 2] = (((y1 + y2) / 2) * new_height + dy) / maxsize
	labels[:, 3] *= new_width / width / maxsize
	labels[:, 4] *= new_height / height / maxsize

	if lrflip:
		labels[:, 1] = 1 - labels[:, 1]
	return labels


def yolobox2label(box, info_img:ImageInfo):
	"""
	Transform yolo box labels to yxyx box labels.
	Args:
		box (list): box data with the format of [yc, xc, width, height]
			in the coordinate system after pre-processing.
		info_img : tuple of height, width, new_height, new_width, dx, dy.
			height, width (int): original shape of the image
			new_height, new_width (int): shape of the resized image without padding
			dx, dy (int): pad size
	Returns:
		label (list): box data with the format of [y1, x1, y2, x2]
			in the coordinate system of the input image.
	"""
	height, width, new_height, new_width, dx, dy = info_img
	y1, x1, y2, x2 = box

	box_h = ((y2 - y1) / new_height) * height
	box_w = ((x2 - x1) / new_width) * width
	y1 = ((y1 - dy) / new_height) * height
	x1 = ((x1 - dx) / new_width) * width

	label = [max(x1, 0), max(y1, 0), min(x1 + box_w, width), min(y1 + box_h, height)]
	return label


def nms(bbox:np.ndarray, thresh:float, score:np.ndarray = None, limit:int = None) -> np.ndarray:
	"""Suppress bounding boxes according to their IoUs and confidence scores.
	Args:
		bbox (array): Bounding boxes to be transformed. The shape is
			:math:`(R, 4)`. :math:`R` is the number of bounding boxes.
		thresh (float): Threshold of IoUs.
		score (array): An array of confidences whose shape is :math:`(R,)`.
		limit (int): The upper bound of the number of the output bounding
			boxes. If it is not specified, this method selects as many
			bounding boxes as possible.
	Returns:
		array:
		An array with indices of bounding boxes that are selected. \
		They are sorted by the scores of bounding boxes in descending \
		order. \
		The shape of this array is :math:`(K,)` and its dtype is\
		:obj:`numpy.int32`. Note that :math:`K \\leq R`.

	from: https://github.com/chainer/chainercv
	"""

	if len(bbox) == 0:
		return np.zeros((0,), dtype=np.int32)

	if score is not None:
		order = score.argsort()[::-1]
		bbox = bbox[order]
	bbox_area = np.prod(bbox[:, 2:] - bbox[:, :2], axis=1)

	selec = np.zeros(bbox.shape[0], dtype=bool)
	for i, b in enumerate(bbox):
		top_left = np.maximum(b[:2], bbox[selec, :2])
		bottom_right = np.minimum(b[2:], bbox[selec, 2:])
		area = np.prod(bottom_right - top_left, axis=1) * (top_left < bottom_right).all(axis=1)

		iou = area / (bbox_area[i] + bbox_area[selec] - area)
		if (iou >= thresh).any():
			continue

		selec[i] = True
		if limit is not None and np.count_nonzero(selec) >= limit:
			break

	selec = np.where(selec)[0]
	if score is not None:
		selec = order[selec]
	return selec.astype(np.int32)


def postprocess(prediction:torch.Tensor, dtype, conf_thres:float = 0.7, nms_thres:float = 0.45) -> list[torch.Tensor]:
	"""
	Postprocess for the output of YOLO model
	perform box transformation, specify the class for each detection,
	and perform class-wise non-maximum suppression.
	Args:
		prediction (torch tensor): The shape is :math:`(N, B, 4)`.
			:math:`N` is the number of predictions,
			:math:`B` the number of boxes. The last axis consists of
			:math:`xc, yc, w, h` where `xc` and `yc` represent a center
			of a bounding box.
		num_classes (int):
			number of dataset classes.
		conf_thres (float):
			confidence threshold ranging from 0 to 1,
			which is defined in the config file.
		nms_thres (float):
			IoU threshold of non-max suppression ranging from 0 to 1.

	Returns:
		output (list of torch tensor):

	"""
	box_corner = prediction.new(prediction.shape)
	box_corner[:, :, 0] = prediction[:, :, 0] - prediction[:, :, 2] / 2
	box_corner[:, :, 1] = prediction[:, :, 1] - prediction[:, :, 3] / 2
	box_corner[:, :, 2] = prediction[:, :, 0] + prediction[:, :, 2] / 2
	box_corner[:, :, 3] = prediction[:, :, 1] + prediction[:, :, 3] / 2
	prediction[:, :, :4] = box_corner[:, :, :4]

	output = [None for _ in range(len(prediction))]
	for i, image_pred in enumerate(prediction):
		# Filter out confidence scores below the threshold
		conf_mask = (image_pred[:, 4] >= conf_thres).squeeze()
		image_pred = image_pred[conf_mask]

		# If none are remaining => process next image
		if not image_pred.size(0):
			continue

		# Get score and class with highest confidence
		class_conf = torch.ones(image_pred[:, 4:5].size()).type(dtype)
		class_pred = torch.zeros(image_pred[:, 4:5].size()).type(dtype)

		# Detections ordered as (x1, y1, x2, y2, obj_conf, class_conf, class_pred)
		detections = torch.cat((image_pred[:, :5], class_conf.float(), class_pred.float()), 1)
		# Iterate through all predicted classes
		unique_labels = detections[:, -1].cpu().unique()

		if prediction.is_cuda:
			unique_labels = unique_labels.cuda()

		for _class in unique_labels:
			# Get the detections with the particular class
			detections_class = detections[detections[:, -1] == _class]
			nms_in = detections_class.cpu().numpy()
			nms_out_index = nms(nms_in[:, :4], nms_thres, score=nms_in[:, 4] * nms_in[:, 5])

			detections_class = detections_class[nms_out_index]
			if output[i] is None:
				output[i] = detections_class
			else:
				output[i] = torch.cat((output[i], detections_class))

	return output


def preprocess_mask(mask:np.ndarray, imgsize:int, info_img:ImageInfo):
	h, w, nh, nw, dx, dy = info_img
	sized = np.ones((imgsize, imgsize, 1), dtype=np.uint8) * 127
	mask = cv2.resize(mask, (nw, nh))
	sized[dy:dy + nh, dx:dx + nw, 0] = mask

	return sized


def preprocess(img:np.ndarray, imgsize:int, jitter:float, random_placing:bool = False) -> tuple[np.ndarray, ImageInfo]:
	"""
	Image preprocess for yolo input
	Pad the shorter side of the image and resize to (imgsize, imgsize)
	Args:
		img (numpy.ndarray): input image whose shape is :math:`(H, W, C)`.
			Values range from 0 to 255.
		imgsize (int): target image size after pre-processing
		jitter (float): amplitude of jitter for resizing
		random_placing (bool): if True, place the image at random position

	Returns:
		img (numpy.ndarray): input image whose shape is :math:`(C, imgsize, imgsize)`.
			Values range from 0 to 1.
		info_img : tuple of h, w, nh, nw, dx, dy.
			height, width (int): original shape of the image
			new_height, new_width (int): shape of the resized image without padding
			dx, dy (int): pad size
	"""
	height, width, _ = img.shape
	img = img[:, :, ::-1]
	assert img is not None

	if jitter > 0:
		# add jitter
		dw = jitter * width
		dh = jitter * height
		new_ar = (width + np.random.uniform(low=-dw, high=dw)) / (height + np.random.uniform(low=-dh, high=dh))
	else:
		new_ar = width / height

	if new_ar < 1: # width < height
		new_height = imgsize
		new_width = new_height * new_ar
	else:
		new_width = imgsize
		new_height = new_width / new_ar

	new_width, new_height = int(max(new_width, 1)), int(max(new_height, 1))

	if random_placing:
		dx = int(np.random.uniform(imgsize - new_width))
		dy = int(np.random.uniform(imgsize - new_height))
	else:
		dx = (imgsize - new_width) // 2
		dy = (imgsize - new_height) // 2

	img = cv2.resize(img, (new_width, new_height))
	sized = np.ones((imgsize, imgsize, 3), dtype=np.uint8) * 127
	sized[dy:dy + new_height, dx:dx + new_width, :] = img

	info_img = ImageInfo(height, width, new_height, new_width, dx, dy)
	return sized, info_img
