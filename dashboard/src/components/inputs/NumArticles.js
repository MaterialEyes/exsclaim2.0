import React from 'react';
import { Box, Stack, Typography, TextField } from '@mui/material';

// Handles the number of articles EXSCLAIM will parse through

const NumArticles = (props) => {

  // set user's query of a minimum width/height
  const numArticlesChange = (event) => {
    var value = parseInt(event.target.value, 10);

    if (value < 1) {value = 1};
    if (!value) {value = 0};

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
      
export default NumArticles;