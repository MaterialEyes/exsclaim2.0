import React from 'react';
import { useState, useEffect } from 'react';
import { fetchArticles, fetchSubFigures, fetchFigures } from '../../services/ApiClient';
import { ImageList, ImageListItem, ImageListItemBar, IconButton, Tooltip, Link } from '@mui/material';
import InfoIcon from '@mui/icons-material/Info';
import CropImage from '../images/CropImage';

// Displays the subfigures given after user's input
const ImagesPageAPI = () => {

    const [articles, setArticles] = useState([])
    const [subFigures, setSubFigures] = useState([])
    const [figures, setFigures] = useState([])

    function subFigureURL(id) {
      let figure = figures.find(item => item.figure_id === id);
      let url = figure?.url;
      return url;
    }

    function subFigureArticle(id) {
      let figure = figures.find(item => item.figure_id === id);
      let article_id = figure?.article;
      let article = articles.find(item => item.doi === article_id);
      let title = article?.title;
      return title;
    }

    function subFigureArticleURL(id) {
      let figure = figures.find(item => item.figure_id === id);
      let article_id = figure?.article;
      let article = articles.find(item => item.doi === article_id);
      let url = article?.url;
      return url;
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

        if (subFiguresJson.next) {
            getSubFigures(page+1);
        }
      }
      const getFigures = async (page) => {
        const figuresJson = await fetchFigures(page);
        const data = figuresJson["results"];
        setFigures(oldArray => [...oldArray, ...data]);

        if (figuresJson.next) {
            getFigures(page+1);
        }
      }

      getArticles();
      getSubFigures(1);
      getFigures(1);

    }, [])

    return (
      <div>
        
          {subFigures.length > 0 ? (
            <ImageList sx={{ height: 550 }} cols={3}>
              {subFigures.map((val) => (
                <ImageListItem 
                  key={val.subfigure_id}
                >
                  <CropImage 
                    url={subFigureURL(val.figure)}
                    data={val}
                  />
                  <ImageListItemBar
                    title={val.subfigure_id}
                    subtitle={
                    <Link href={subFigureArticleURL(val.figure)} underline="hover" color="white">{subFigureArticle(val.figure)}</Link>
                    }
                    actionIcon={
                      <Tooltip title={(val.caption !== null) ? (val.caption) : ("No captions available")}>
                        <IconButton
                          sx={{ color: 'rgba(255, 255, 255, 0.54)' }}
                          aria-label={`info about ${subFigureArticle(val.figure)}`}
                        >
                          <InfoIcon />
                        </IconButton>
                      </Tooltip>
                    }
                  />
                  
                </ImageListItem>
              )
            )}
            </ImageList>
        ) : (
            'No articles/figures available'
        )}

      </div>

   )
}

export default ImagesPageAPI;