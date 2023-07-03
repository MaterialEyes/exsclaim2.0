import React from 'react';
//import { useState, useEffect } from 'react';
//import { fetchArticles } from '../../services/ApiClient';
import { ImageList, ImageListItem, ImageListItemBar, IconButton, Tooltip, Link } from '@mui/material';
import InfoIcon from '@mui/icons-material/Info';
import myData from '../../example-files/exsclaim.json';
import CropImage from '../images/CropImage';

// Displays the subfigures given after user's input
const ImagesPage = () => {
    // get the articles
    const keys = Object.keys(myData);

    /*
    const [articles, setArticles] = useState([])

    useEffect(() => {
      const getArticles = async () => {
        const articlesFromServer = await fetchArticles()
        setArticles(articlesFromServer)
      }
      getArticles()
    }, [])
    */

    // In the real app, we'll want to show subfigures, not articles. You 
    // can retrieve them from their figure urls, and then you'll have to crop
    // them. The old ui had an image only results page that I liked, and one
    // with the resolved metadata (caption, scale, label, etc.). This is where
    // something like https://mui.com/components/data-grid/ and/or
    // https://mui.com/components/image-list/#masonry-image-list will come in
    // handy (masonry is good because it will allow images with different sizes
    // to fit together well)
    //
    // try combining the masonry image list with this:
    // https://colab.research.google.com/drive/1WB5EQxSn8lVwx7vDw0TT8ZpDn7jxYzh9#scrollTo=660oaoioWGek
    return (
      <div>
          {keys.length > 0 ? (
              <ImageList sx={{ height: 550 }} cols={3}>
               {keys.map((val) => (
                 Array.from(Array(myData[val]["master_images"].length).keys()).map((x) => (
                    <ImageListItem 
                      key={myData[val]["figure_name"] + " (" 
                        + myData[val]["master_images"][x]["subfigure_label"]["text"] + ")"}
                    >
                       <CropImage 
                        figure_name={val} 
                        num={x} >
                      </CropImage>
                       <ImageListItemBar
                         title={myData[val]["figure_name"] + " (" 
                           + myData[val]["master_images"][x]["subfigure_label"]["text"] + ")"}
                         subtitle={
                          <Link href={myData[val]["article_url"]} underline="hover" color="white">{myData[val]["title"]}</Link>
                          }
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

export default ImagesPage;