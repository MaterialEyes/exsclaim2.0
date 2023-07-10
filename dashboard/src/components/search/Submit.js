import React from 'react'
//import { useState, useEffect } from 'react';
import { Button } from '@mui/material';

// Submit user's query

const Submit = (props) => {
  /*
  function subFigureFindFigure(id) {
    let figure = props.figurelist.find(item => item.figure_id === id);
    return figure;
  }
  */

  // find article data of a subfigure given the figure's id
  function subFigureFindArticle(id) {
    let figure = props.figurelist?.find(item => item.figure_id === id);
    let article_id = figure?.article;
    let article = props.articlelist?.find(item => item.doi === article_id);
    return article;
  }

  // return new subfigure list from user's query
  function getNewSubFigures() {
    let newSubFigures = [...props.allSubFigures];

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
    
    console.log(props.scales);
    console.log(props.keywords);

    props.setSubFigures(newSubFigures);
  }
  
  return (
    <div>
      <Button sx={{ width: 200}} variant="contained" onClick={getNewSubFigures}>Submit</Button>
    </div>
  )
}


export default Submit;