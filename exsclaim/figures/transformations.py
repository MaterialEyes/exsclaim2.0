from PIL import Image
from torchvision import transforms


__all__ = ["resize_transform"]


def resize_transform(image:Image):
	transform = transforms.Compose(
		[
			transforms.Resize((128, 512)),
			transforms.Lambda(lambda image: image.convert("RGB")),
			transforms.ToTensor(),
			transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
		]
	)
	classes = "0123456789mMcCuUnN .A"
	image = transform(image)
	return image.unsqueeze(0), classes
