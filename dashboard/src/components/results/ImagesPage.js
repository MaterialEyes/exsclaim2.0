import React from 'react';
import { ImageList, ImageListItem, ImageListItemBar, IconButton, Tooltip, Link } from '@mui/material';
import InfoIcon from '@mui/icons-material/Info';
import CropImage from '../images/CropImage';

// Displays the subfigures given after user's input
const ImagesPage = (props) => {

  function subFigureFindFigure(id) {
    let figure = props.figurelist.find(item => item.figure_id === id);
    return figure;
  }

  function subFigureFindArticle(id) {
    let figure = props.figurelist.find(item => item.figure_id === id);
    let article_id = figure?.article;
    let article = props.articlelist.find(item => item.doi === article_id);
    return article;
  }

  return (
    <div>
        {props.subfigurelist.length > 0 ? (
          <ImageList sx={{ height: 550 }} cols={3}>
            {props.subfigurelist.map((val) => (
              <ImageListItem 
                key={val.subfigure_id}
              >
                <CropImage 
                  url={subFigureFindFigure(val?.figure)?.url}
                  data={val}
                  figureData={subFigureFindFigure(val?.figure)}
                  articleData={subFigureFindArticle(val?.figure)}
                  license={props.license}
                />
                <ImageListItemBar
                  title={val.subfigure_id}
                  subtitle={
                  <Link href={subFigureFindArticle(val?.figure)?.url} underline="hover" color="white">{subFigureFindArticle(val?.figure)?.title}</Link>
                  }
                  actionIcon={
                    <Tooltip title={(val?.caption !== null) ? (val?.caption) : ("No captions available")}>
                      <IconButton
                        sx={{ color: 'rgba(255, 255, 255, 0.54)' }}
                        aria-label={`info about ${subFigureFindArticle(val?.figure)?.title}`}
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

export default ImagesPage;