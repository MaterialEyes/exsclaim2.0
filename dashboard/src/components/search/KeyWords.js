import React from 'react'
import { Autocomplete, FormGroup, FormControlLabel, Checkbox, TextField } from '@mui/material';

// Focuses on the keywords contained in the subfigures

const keywords = ["nano"];

const KeyWords = () => {
  return (
    <div>
      <Autocomplete
        disablePortal
        id="combo-box-demo"
        options={keywords}
        sx={{ width: 300, minHeight: 50 }}
        renderInput={(params) => <TextField {...params} label="Keywords" />}
        size="small"
      />

      <FormGroup>
        <FormControlLabel 
          sx={{ height: 20 }} 
          control={<Checkbox defaultChecked size="small" />} 
          label="Subfigure's Distributed Caption" />
        <FormControlLabel 
          sx={{ height: 20 }} 
          control={<Checkbox defaultChecked size="small" />}
          label="Subfigure's Containing Figure's Caption" />
        <FormControlLabel 
          sx={{ height: 20 }} 
          control={<Checkbox defaultChecked size="small" />} 
          label="Article Title" />
      </FormGroup>
    </div>
  )
}

export default KeyWords;