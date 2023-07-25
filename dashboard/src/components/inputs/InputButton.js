import React from 'react';
//import { useState, useEffect } from 'react';
import { Box, Button } from '@mui/material';

const InputButton = (props) => {

  function submitQuery() {
    console.log(props.outputName);
    console.log(props.numArticles);
    console.log(props.term);
    console.log(props.synonyms);
    console.log(props.journalFamily);
    console.log(props.sort);
    console.log(props.access);

    props.setLoadResults(true);
  }
  
  return (
    <Box sx={{ padding: 1 }}>
      <Button sx={{ width: 200}} variant="contained" onClick={submitQuery}>Submit</Button>
    </Box>
  )
}
      
export default InputButton;