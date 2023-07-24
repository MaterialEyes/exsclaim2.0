import React from 'react';
import { Box, Stack, Typography, TextField } from '@mui/material';

const InputTerm = (props) => {
    
  return (
    <Box sx={{ padding: 1 }}>
      <Stack direction="row" spacing={2}>
        <Typography>Term:</Typography>
        <TextField
          id="term-input"
          label="Term"
          margin="dense"
          sx={{ width: 300, minHeight: 50 }}
          onChange={(e) => {
            props.setTerm(e.target.value);
          }}
        />
      </Stack>
    </Box>
  )
}
    
export default InputTerm;