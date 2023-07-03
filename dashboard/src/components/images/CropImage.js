import React from 'react';
import { useEffect, useRef } from 'react';

// Testing cropping images
// https://code.tutsplus.com/tutorials/how-to-crop-or-resize-an-image-with-javascript--cms-40446
// https://stackoverflow.com/questions/58063673/how-to-display-specific-part-of-image-in-square
// https://stackoverflow.com/questions/47362222/how-to-show-the-only-part-of-the-image
// https://www.w3schools.com/cssref/pr_pos_clip.php
// https://stackoverflow.com/questions/30629230/centering-svg-clipping-path-with-css

const imgSize = 290;

const CropImage = (props) => {

    const myCanvas = useRef();

    // this was used for the example json file
    /*
    function cropImage(figure, num) {
      var topLeft_x = figure["master_images"][num]["geometry"][0]["x"];
      var topLeft_y = figure["master_images"][num]["geometry"][0]["y"];
      var sub_width = figure["master_images"][num]["width"];
      var sub_height = figure["master_images"][num]["height"];

      var crop_dimensions = []

      crop_dimensions.push(topLeft_x, topLeft_y, sub_width, sub_height)

      return crop_dimensions;
    }
    */

    function cropImageAPI(data) {
      var topLeft_x = data["x1"];
      var topLeft_y = data["y1"];
      var sub_width = data["width"];
      var sub_height = data["height"];

      var crop_dimensions = []

      crop_dimensions.push(topLeft_x, topLeft_y, sub_width, sub_height)

      return crop_dimensions;
    }

    /*

    useEffect(() => {
        const context = myCanvas.current.getContext("2d");

        const figure = myData[props.figure_name];
        const sub_num = props.num;

        const image = new Image();
        image.src = figure["image_url"];
        image.onload = () => {
          //const dimensions = cropImage(figure, sub_num);
          const dimensions = cropImageAPI();
          context.drawImage(image, dimensions[0], dimensions[1], dimensions[2], dimensions[3],
            0, 0, dimensions[2], dimensions[3]);
        };
      });

    */

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
        <canvas ref={myCanvas} width={imgSize} height={imgSize} ></canvas>
    )
}

export default CropImage;