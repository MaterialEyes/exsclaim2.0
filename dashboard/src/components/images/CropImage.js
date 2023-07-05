import React from 'react';
import { useEffect, useRef } from 'react';

const imgSize = 290;

const CropImage = (props) => {

    const myCanvas = useRef();
    
    function cropImageAPI(data) {
      var topLeft_x = data["x1"];
      var topLeft_y = data["y1"];
      var sub_width = data["width"];
      var sub_height = data["height"];

      var crop_dimensions = []

      crop_dimensions.push(topLeft_x, topLeft_y, sub_width, sub_height)

      return crop_dimensions;
    }

    useEffect(() => {
      const context = myCanvas.current.getContext("2d");

      const url = props.url;
      const data = props.data;

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