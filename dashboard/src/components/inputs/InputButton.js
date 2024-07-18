import React from 'react';
import { Box, Button } from '@mui/material';

// Submits the user query to the API, which then runs EXSCLAIM. After the subfigure results are loaded, 
// the user is taken to the results page (Layout.js)

const InputButton = (props) => {

  // the function that will send a post request with the user's input query to the API
  function submitQuery() {

    // data that will be posted to the API
    var inputData = {
      "name" : props.outputName,
      "journal_family" : props.journalFamily,
      "maximum_scraped" : props.numArticles,
      "sortby" : props.sort,
      "term" : props.term,
      "synonyms" : props.synonyms,
      "save_format" : "postgres",
      "access" : props.access,
      "llm" : props.model,
      "model_key" : props.modelKey
    };

    // POST user input to API
    fetch(process.env.FAST_API_URL, {
      method: 'POST', 
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(inputData)
    });

    props.setLoadResults(true);
  }
  
  return (
    <Box sx={{ padding: 1 }}>
      <Button sx={{ width: 200}} variant="contained" onClick={submitQuery}>Submit</Button>
    </Box>
  )
}
      
export default InputButton;