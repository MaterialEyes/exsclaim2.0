import React from 'react'
import { Autocomplete, FormControlLabel, FormGroup, TextField, FormLabel, Radio, RadioGroup } from '@mui/material';

// Focuses on the keywords contained in the subfigures

const KeyWords = (props) => {

  // flatten a nested array to a normal array
  function flatten(arr) {
    return arr.reduce(function (flat, toFlatten) {
      return flat.concat(Array.isArray(toFlatten) ? flatten(toFlatten) : toFlatten);
    }, []);
  }

  // set user's query of where to look for keywords
  const changeKeyWords = (event) => {
    var value = event.target.value;

    //console.log(value);
    if (value === 'caption') {
      let subFigureKeywords = props.subFigures.map((val) => val.keywords);
      props.setKeywords(Array.from(new Set(flatten(subFigureKeywords))));
    } else if (value === 'general') {
      let generalKeywords = props.subFigures.map((val) => val.general);
      props.setKeywords(Array.from(new Set(flatten(generalKeywords))));
    } else if (value === 'title') {
      let titleKeywords = props.articles.map((val) => val.title);
      props.setKeywords(Array.from(new Set(flatten(titleKeywords))));
    }
  }

  return (
    <div>
      <FormGroup>
        <FormLabel id="keywords label">Subfigures containing keywords in:</FormLabel>
        <RadioGroup
          aria-labelledby="keywords buttons label"
          defaultValue="caption"
          name="keywords buttons"
          onChange={changeKeyWords}
        >
          <FormControlLabel sx={{ height: 20 }}  value="caption" control={<Radio size="small" />} label="Subfigure Caption" />
          <FormControlLabel sx={{ height: 20 }}  value="general" control={<Radio size="small" />} label="General Article" />
          <FormControlLabel sx={{ height: 20 }}  value="title" control={<Radio size="small" />} label="Article's Title" />
        </RadioGroup>
      </FormGroup>

      <Autocomplete
        disablePortal
        id="combo-box-demo"
        options={props.keywords}
        sx={{ width: '65%', minHeight: 40, margin: 1 }}
        renderInput={(params) => <TextField {...params} label="Keywords" />}
        size="small"
      />
    </div>
  )
}

export default KeyWords;

/*
<FormGroup>
        <FormControlLabel 
          sx={{ height: 20 }} 
          control={<Checkbox id="subfigure-caption" defaultChecked size="small" />} 
          label="Caption" />
        <FormControlLabel 
          sx={{ height: 20 }} 
          control={<Checkbox id="figure-caption" defaultChecked size="small" />}
          label="General" />
        <FormControlLabel 
          sx={{ height: 20 }} 
          control={<Checkbox id="article-title" defaultChecked size="small" />} 
          label="Article Title" />
      </FormGroup>
*/