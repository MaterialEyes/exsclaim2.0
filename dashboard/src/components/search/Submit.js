import React from 'react'
import { useState, useEffect } from 'react';
import { Button } from '@mui/material';
import { fetchSubFigures } from '../../services/ApiClient';

// Submit user's query

const Submit = (props) => {
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
  function getNewSubFigures() {
    let newSubFigures = [...props.allsubfigurelist];

    if (props.license) {
      newSubFigures.filter((val) => subFigureFindArticle(val.figure)?.open === true);
    }
    props.setSubFigures(newSubFigures);
  }
  
  return (
    <div>
      <Button sx={{ width: 200}} variant="contained" onClick={getNewSubFigures}>Submit</Button>
    </div>
  )
}


export default Submit;