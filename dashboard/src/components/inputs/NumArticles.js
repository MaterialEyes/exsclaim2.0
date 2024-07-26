import React from 'react';
import { Box, Stack, Typography, TextField } from '@mui/material';
import PropTypes from "prop-types";

// Gets the number of articles EXSCLAIM will parse through

const NumArticles = (props) => {

  // sets the number of articles EXSCLAIM will run through
  const numArticlesChange = (event) => {
    var value = parseInt(event.target.value, 10);

    if (value < 1) {value = 1;} // set user's query of a minimum of 1
    if (!value) {value = 0;} // if user leaves value text box blank, set value to 0 (in the API, if value is 0, then assume user wants all articles)

    props.setNumArticles(value);
  }
    
  return (
    <Box sx={{ padding: 1 }}>
      <Stack direction="row" spacing={2}>
        <Typography>Max Articles:</Typography>
        <TextField
          id="max-number-articles"
          label="Max Articles"
          type="number"
          margin="dense"
          InputProps={{
            inputProps: { type: 'number', min: 1 }
          }}
          sx={{ width: 300, minHeight: 50 }}
          onChange={(e) => numArticlesChange(e)}
        />
      </Stack>
    </Box>
  )
}

NumArticles.propTypes = {
  props: PropTypes.number
}

export default NumArticles;