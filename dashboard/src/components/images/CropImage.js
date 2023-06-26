import React from 'react';
//import { useState, useEffect } from 'react';
//import { fetchArticles } from '../../services/ApiClient';
import { ImageList, ImageListItem, ImageListItemBar, ListSubheader, IconButton, Tooltip } from '@mui/material';
import InfoIcon from '@mui/icons-material/Info';
import myData from '../../example-files/exsclaim.json';

// Testing cropping images
// https://code.tutsplus.com/tutorials/how-to-crop-or-resize-an-image-with-javascript--cms-40446
// https://stackoverflow.com/questions/58063673/how-to-display-specific-part-of-image-in-square
// https://stackoverflow.com/questions/47362222/how-to-show-the-only-part-of-the-image
// https://www.w3schools.com/cssref/pr_pos_clip.php

function cropImage(imagePath, newX, newY, newWidth, newHeight) {
    const originalImage = new Image();
    originalImage.src = imagePath;
    const canvas = document.getElementById('canvas');
    const ctx = canvas.getContext('2d');
    originalImage.addEventListener('load', function() {
        
        const originalWidth = originalImage.naturalWidth;
        const originalHeight = originalImage.naturalHeight;
        const aspectRatio = originalWidth/originalHeight;
        if(newHeight === undefined) {
            newHeight = newWidth/aspectRatio;
        }
        canvas.width = newWidth;
        canvas.height = newHeight;
        
        ctx.drawImage(originalImage, newX, newY, newWidth, newHeight, 0, 0, newWidth, newHeight);
    });
}

const example_figure = myData["d0na00203h_fig1.jpg"];

const CropImage = () => {
    return (
       <div>
           {/* 
           <View style={{width: 64, height: 64, overflow: 'hidden'}}>
                <Image
                    source={{uri: 'https://picsum.photos/200/300'}}
                    style={{
                    height: 200,
                    width: 200,
                    top: -50,
                    left: -70,
                    }}
                />
            </View> */}
           <img
                src={`${example_figure["image_url"]}?w=248&fit=crop&auto=format`}
                srcSet={`${example_figure["image_url"]}?w=248&fit=crop&auto=format&dpr=2 2x`}
                alt={example_figure["figure_name"]}
                loading="lazy"
            />
       </div>

    )
}

export default CropImage;