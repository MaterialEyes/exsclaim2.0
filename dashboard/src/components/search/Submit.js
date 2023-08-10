import React from 'react'
import { Button } from '@mui/material';

// Submit user's query for filtered subfigures

const Submit = (props) => {

  // find article data of a subfigure given the figure's id
  function subFigureFindArticle(id) {
    let figure = props.figures?.find(item => item.figure_id === id);
    let article_id = figure?.article;
    let article = props.articles?.find(item => item.doi === article_id);
    return article;
  }

  // return new subfigure list from user's query
  function getNewSubFigures() {
    let newSubFigures = [...props.allSubFigures];

    // filter for subfigures containing a certain keyword
    if (props.keyword) {
      if (props.keywordType === 'caption') {
        newSubFigures = newSubFigures.filter((val) => val.keywords.indexOf(props.keyword) !== -1);
      } else if (props.keywordType === 'general') {
        newSubFigures = newSubFigures.filter((val) => val.general.indexOf(props.keyword) !== -1);
      } else if (props.keywordType === 'title') {
        newSubFigures = newSubFigures.filter((val) => subFigureFindArticle(val?.figure)?.title === props.keyword);
      }
    }

    // filter for subfigures of certain class(es)
    let subFigureClasses = Object.keys(props.classes).filter(function (k) {return props.classes[k];});
    newSubFigures = newSubFigures.filter((val) => subFigureClasses.indexOf(val.classification) !== -1);

    // filter for open-access subfigures
    if (props.license === true) {
      newSubFigures = newSubFigures.filter((val) => subFigureFindArticle(val?.figure)?.open === true);
    }

    // filter for subfigures of certain scale
    newSubFigures = newSubFigures.filter((val) => 
      (val.width <= props.scales["maxWidth"] && val.width >= props.scales["minWidth"] &&
      val.height <= props.scales["maxHeight"] && val.height >= props.scales["minHeight"]));
    
    // scales doesn't really work yet since example data doesn't have confidence threshold yet
    console.log(props.scales);

    props.setSubFigures(newSubFigures);
  }
  
  return (
    <div>
      <Button sx={{ width: 200}} variant="contained" onClick={getNewSubFigures}>Submit</Button>
      <Button sx={{ width: 200}} onClick={() => {
        // goes back to the query page
        props.setLoadResults(false);
      }
      }>Back to Query</Button>
    </div>
  )
}


export default Submit;