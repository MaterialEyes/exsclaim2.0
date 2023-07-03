import React from 'react';
import { useState, useEffect } from 'react';
import { fetchSubFigures } from '../../services/ApiClient';
//import { ImageList, ImageListItem, ImageListItemBar, IconButton, Tooltip, Link, getAccordionSummaryUtilityClass } from '@mui/material';
//import InfoIcon from '@mui/icons-material/Info';
//import CropImage from '../images/CropImage';

// Displays the subfigures given after user's input
const ImagesPageAPI = () => {
    // get the articles
    // const keys = Object.keys(myData);

    const [articles, setArticles] = useState([])
    const [subFigures, setSubFigures] = useState([])

    useEffect(() => {
      const getSubFigures = async (page) => {
        const subFiguresJson = await fetchSubFigures(page);
        const data = subFiguresJson["results"];
        setSubFigures(oldArray => [...oldArray, ...data]);

        if (subFiguresJson.next) {
            getSubFigures(page+1);
        }
      }
      getSubFigures(1);
    }, [])

    /*

    React.useEffect(() => {
        const getAllGames = async(page: number|null): void => {
          if (Number.isInteger(page)){
            const result = await fetch(apiURL + "/games?page="+page)
            const data = await result.json()
            const { results: games } = data;
            if (data.next) { 
              setTimeout(
                getAllGames(
                  parseInt(data.next.charAt(data.next.length-1))), 10000)
            }
            setGames(previousGames => [...games, ...previousGames]);
          }
        }
        getAllGames(1)
      }, []);

      */

    return (
      <div>
          { /*
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
          */}

            {subFigures.length > 0 ? (
                <div>
                    {subFigures.map((subfigure) =>(
                        <li>{subfigure.subfigure_id}</li>
                    ))}
                </div>
            ) : (
                'No subfigures available'
            )}
          
      </div>

   )
}

export default ImagesPageAPI;