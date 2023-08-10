import React from 'react';
import { ImageList, ImageListItem, ImageListItemBar, IconButton, Tooltip, Link } from '@mui/material';
import InfoIcon from '@mui/icons-material/Info';
import CropImage from '../images/CropImage';

// Displays the subfigure results of the user's input in the subfigure results menu and the query menu

const ImagesPage = (props) => {

  // find figure data of a subfigure given the figure's id
  function subFigureFindFigure(id) {
    let figure = props.figures.find(item => item.figure_id === id);
    return figure;
  }

  // find article data of a subfigure given the figure's id
  function subFigureFindArticle(id) {
    let figure = props.figures.find(item => item.figure_id === id);
    let article_id = figure?.article;
    let article = props.articles.find(item => item.doi === article_id);
    return article;
  }

  // if there are subfigures that match the inputted queries, return those. If not, return no images found
  return (
    <div>
        {props.subFigures.length > 0 ? (
          <ImageList sx={{ maxHeight: 590 }} cols={3}>
            {props.subFigures.map((val) => (
              <ImageListItem 
                key={val.subfigure_id}
              >
                {/* the cropped image */}
                <CropImage 
                  url={subFigureFindFigure(val?.figure)?.url}
                  data={val}
                />
                {/* display the subfigure's caption, original article (link to original article if user links on the article name), and subfigure name */}
                <ImageListItemBar
                  title={val.subfigure_id}
                  subtitle={
                  <Link href={subFigureFindArticle(val?.figure)?.url} underline="hover" color="white">{subFigureFindArticle(val?.figure)?.title}</Link>
                  }
                  actionIcon={
                    // display the subfigure captions when user hovers over info icon if there are captions. If not, return no captions available
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