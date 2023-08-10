import React from 'react';
import { useEffect, useRef } from 'react';

// Returns the cropped image from the given data

const CropImage = (props) => {
  const imgSize = 290;

  const myCanvas = useRef();
  
  // get the dimensions of the crop
  function cropImageAPI(data) {
    var topLeft_x = data["x1"]; // top left corner x-coordinate of the subfigure
    var topLeft_y = data["y1"]; // top left corner y-coordinate of the subfigure
    var sub_width = data["width"]; // width of the subfigure
    var sub_height = data["height"]; // height of the subfigure

    var crop_dimensions = []

    crop_dimensions.push(topLeft_x, topLeft_y, sub_width, sub_height)

    return crop_dimensions;
  }

  useEffect(() => {
    const context = myCanvas.current.getContext("2d");

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
  });

  return (
      <div>
        <canvas ref={myCanvas} width={imgSize} height={imgSize} ></canvas>
      </div>
  )
}

export default CropImage;