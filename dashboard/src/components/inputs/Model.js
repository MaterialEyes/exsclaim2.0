import React from 'react';
import { useState } from 'react';
import { Box, Stack, Typography, FormControlLabel, FormGroup, Radio, RadioGroup, TextField } from '@mui/material';

// Gets what kind of llm (large langauge model) EXSCLAIM will use

const Model = (props) => {

  const [showKey, setShowKey] = useState(false);

  // handles whether or not to show the model key text box depending on what model the user chooses to use
  function handleModelChange(value)  {
    props.setModel(value);

    if (value !== 'vicuna') {
      setShowKey(true);
    }
    else {
      setShowKey(false);
      props.setModelKey("");
    }
  }
    
  return (
    <Box sx={{ padding: 1 }}>
      <Stack direction="row" spacing={2}>
        <Typography>Large Language Model:</Typography>
        <FormGroup>
          <RadioGroup
            aria-labelledby="model label"
            defaultValue="vicuna"
            name="models buttons"
            onChange={(event, value) => {
              handleModelChange(value);
            }}
          >
            <FormControlLabel sx={{ height: 30 }} value="vicuna" control={<Radio />} label="Vicuna" />
            <FormControlLabel sx={{ height: 30 }} value="gpt3.5-turbo" control={<Radio />} label="GPT3.5-turbo" />
            <FormControlLabel sx={{ height: 30 }} value="gpt-4" control={<Radio />} label="GPT-4" />
          </RadioGroup>
        </FormGroup>
        { /* show model key text box depending on if the user wants to use GPT or not */ }
        {
          showKey &&
            <TextField
              id="key-input"
              label="GPT Key"
              margin="dense"
              sx={{ width: 300, minHeight: 50 }}
              onChange={(e) => {
                props.setModelKey(e.target.value);
              }}
            />
        }
      </Stack>
    </Box>
  )
}
      
export default Model;