import React from 'react';
//import { useState, useEffect } from 'react';
//import { fetchArticles } from '../../services/ApiClient';
import myData from '../../example-files/exsclaim.json';
//import './CropImage.css';

// Testing cropping images
// https://code.tutsplus.com/tutorials/how-to-crop-or-resize-an-image-with-javascript--cms-40446
// https://stackoverflow.com/questions/58063673/how-to-display-specific-part-of-image-in-square
// https://stackoverflow.com/questions/47362222/how-to-show-the-only-part-of-the-image
// https://www.w3schools.com/cssref/pr_pos_clip.php
// https://stackoverflow.com/questions/30629230/centering-svg-clipping-path-with-css

const example_figure = myData["d0na00203h_fig1.jpg"];

var top_ex = example_figure["master_images"][0]["geometry"][0]["y"];
var left_ex = example_figure["master_images"][0]["geometry"][0]["x"];
var bottom_ex = example_figure["master_images"][0]["geometry"][1]["y"];
var right_ex = example_figure["master_images"][0]["geometry"][2]["x"];

var arr_x = [...example_figure["master_images"]];
var arr_y = [...example_figure["master_images"]];
arr_x.forEach(getXMax);
var max_x = Math.max(...arr_x);
arr_y.forEach(getYMax);
var max_y = Math.max(...arr_y);

function getXMax(item, index, arr) {
    arr[index] = item["geometry"][2]["x"];
}

function getYMax(item, index, arr) {
    arr[index] = item["geometry"][1]["y"];
}

function cropImage(top, right, bottom, left) {
    var img = document.getElementById("test-image");
    var originalWidth = img.naturalWidth;
    var originalHeight = img.naturalHeight;
    img.onLoad = function(event) {
        originalWidth = img.naturalWidth;
        originalHeight = img.naturalHeight;
    }
    img.src = example_figure["image_url"];

    var widthRatio = originalWidth / max_x;
    var heightRatio = originalHeight / max_y;
    
    return "inset" + "(" + (top * heightRatio) + "px " 
        + (right * widthRatio) + "px " + (bottom * heightRatio) + "px " + (left * widthRatio) + "px)";
}

const CropImage = () => {
    return (
       <div>
            <img
                id="test-image"
                src={`${example_figure["image_url"]}?fit=crop&auto=format`}
                srcSet={`${example_figure["image_url"]}?fit=crop&auto=format&dpr=2 2x`}
                alt={example_figure["figure_name"]}
                loading="lazy"
                style={{ clipPath: cropImage(top_ex, 
                    (max_x - right_ex),
                    (max_y - bottom_ex), 
                    left_ex) }}
            />
            
       </div>

    )
}

/* <img
                id="test-image"
                src={`${example_figure["image_url"]}?w=248&fit=crop&auto=format`}
                srcSet={`${example_figure["image_url"]}?w=248&fit=crop&auto=format&dpr=2 2x`}
                alt={example_figure["figure_name"]}
                loading="lazy"
                style={{ clipPath: cropImage(270, 
                    0,
                    0, 
                    0) }}
            /> */

export default CropImage;