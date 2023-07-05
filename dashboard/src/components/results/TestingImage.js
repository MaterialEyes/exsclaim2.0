import React from 'react';
import { useState, useEffect } from 'react';
import { fetchArticles, fetchSubFigures, fetchFigures } from '../../services/ApiClient';
import { ImageListItem } from '@mui/material';
import CropImage from '../images/CropImage';

// Displays the subfigures given after user's input
const TestImage = (props) => {

    const [articles, setArticles] = useState([])
    const [subFigures, setSubFigures] = useState([])
    const [figures, setFigures] = useState([])

    function subFigureArticleOpen(id) {
        let figure = figures.find(item => item.figure_id === id);
        let article_id = figure?.article;
        let article = articles.find(item => item.doi === article_id);
        let open = article?.open;
        return open;
      }

    function licensed(data) {
        return !(subFigureArticleOpen(data?.figure) === false && props.license === false);
    }

    useEffect(() => {
      const getArticles = async () => {
        const articlesFromServer = await fetchArticles()
        setArticles(articlesFromServer)
      }

      const getSubFigures = async (page) => {
        const subFiguresJson = await fetchSubFigures(page);
        const data = subFiguresJson["results"];
        setSubFigures(oldArray => [...oldArray, ...data]);
      }

      const getFigures = async (page) => {
        const figuresJson = await fetchFigures(page);
        const data = figuresJson["results"];
        setFigures(oldArray => [...oldArray, ...data]);
      }

      getArticles();
      getSubFigures(1);
      getFigures(1);

    }, [])

    return (
      <div>
          {
              licensed(subFigures[0]) ? (
                <ImageListItem 
                    key={"testImage"}
                >
                <CropImage 
                    url={"https://media.springernature.com/lw685/springer-static/image/art%3A10.1038%2Fs41467-021-26454-x/MediaObjects/41467_2021_26454_Fig1_HTML.png"}
                    data={subFigures[0]}
                />
                
            </ImageListItem>
              ) : (null)
          }
        
      </div>

   )
}

export default TestImage;