import cv2
from os import PathLike


__all__ = ["apply_mask"]


def apply_mask(figure_path:PathLike[str]):
	# Load the image
	img = cv2.imread(figure_path, cv2.IMREAD_UNCHANGED)

	# Convert the image to RGBA (just in case the image is in another format)
	img = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)

	# Define a 2D filter that will turn black (also shades close to black) pixels to transparent
	low = np.array([0, 0, 0, 0])
	high = np.array([50, 50, 50, 255])

	# Apply the mask (this will turn 'black' pixels to transparent)
	mask = cv2.inRange(img, low, high)
	img[mask > 0] = [0, 0, 0, 0]

	# Convert the image back to PIL format and save the result
	# img_pil = Image.fromarray(img)
	# img_pil.save(figure_path)
	cv2.imwrite(figure_path, img)
