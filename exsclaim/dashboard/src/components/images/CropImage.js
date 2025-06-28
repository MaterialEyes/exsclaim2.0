import React, {useEffect, useRef} from 'react';
import PropTypes from 'prop-types';

/**
 * Returns the cropped image from the given data.
 */
const CropImage = (props) => {
	const imgSize = 290;

	const canvas = useRef();

	// get the dimensions of the crop
	function cropImageAPI(data) {
		const topLeft_x = data["x1"]; // top left corner x-coordinate of the subfigure
		const topLeft_y = data["y1"]; // top left corner y-coordinate of the subfigure
		const sub_width = data["width"]; // width of the subfigure
		const sub_height = data["height"]; // height of the subfigure

		return [topLeft_x, topLeft_y, sub_width, sub_height];
	}

	useEffect(() => {
		const context = canvas.current.getContext("2d");

		const url = props.url;
		const data = props.data;

		// load in the cropped image
		const image = new Image();
		image.src = url;
		image.onload = () => {
			const dimensions = cropImageAPI(data);
			context.drawImage(image, dimensions[0], dimensions[1], dimensions[2], dimensions[3],
				0, 0, dimensions[2], dimensions[3]);
		};
	}, [canvas]);

	return (
		<div>
			<canvas ref={canvas} width={imgSize} height={imgSize} />
		</div>
	)
}

CropImage.propTypes = {
	/**
	 * The url to the image.
	 */
	url: PropTypes.string.isRequired,
	/**
	 * The data about this image from EXSCLAIM
	 */
	data: PropTypes.object.isRequired
}

export default CropImage;