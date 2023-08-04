import React from 'react';
import { Box, Stack, Typography, FormControlLabel, FormGroup, Radio, RadioGroup } from '@mui/material';

// Handles the sort query inputted by the user

const SortBy = (props) => {
    
  return (
    <Box sx={{ padding: 1 }}>
      <Stack direction="row" spacing={2}>
        <Typography>Sort by:</Typography>
        <FormGroup>
          <RadioGroup
            aria-labelledby="sort label"
            defaultValue="revelant"
            name="sort buttons"
            onChange={(event, value) => {
              props.setSort(value);
            }}
          >
            <FormControlLabel sx={{ height: 30 }}  value="revelant" control={<Radio />} label="Revelant" />
            <FormControlLabel sx={{ height: 30 }}  value="recent" control={<Radio />} label="Recent" />
          </RadioGroup>
        </FormGroup>
      </Stack>
    </Box>
  )
}
        
export default SortBy;