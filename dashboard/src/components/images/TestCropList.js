import React from 'react';
import { ImageList, ImageListItem, ImageListItemBar, IconButton, Tooltip } from '@mui/material';
import InfoIcon from '@mui/icons-material/Info';
import myData from '../../example-files/exsclaim.json';
import CropImage from './CropImage';

// Testing if <canvas> can be used with ImageList
const TestCropList = () => {
    // get the articles
    const keys = Object.keys(myData);

    return (
       <div>
           {keys.length > 0 ? (
             // width: 500, height: 450
               <ImageList sx={{ height: 550 }} cols={3} gap={8}>
                {keys.map((val) => (
                  Array.from(Array(myData[val]["master_images"].length).keys()).map((x) => (
                    <ImageListItem key={myData[val]["image_url"]}>
                        <CropImage figure_name={val} num={x}></CropImage>
                        <ImageListItemBar
                          title={myData[val]["figure_name"] + " (" 
                            + myData[val]["master_images"][x]["subfigure_label"]["text"] + ")"}
                          subtitle={myData[val]["title"]}
                          actionIcon={
                            <Tooltip title={myData[val]["full_caption"]}>
                              <IconButton
                                sx={{ color: 'rgba(255, 255, 255, 0.54)' }}
                                aria-label={`info about ${myData[val]["figure_name"]}`}
                              >
                                <InfoIcon />
                              </IconButton>
                            </Tooltip>
                          }
                        />
                    </ImageListItem>
                  ))
                ))}
                </ImageList>
           ) : (
               'No articles/figures available'
           )}
       </div>

    )
}

export default TestCropList;