import React from 'react';
import { Box, Stack, Typography, Autocomplete, TextField } from '@mui/material';

// Gets the alternative search terms (synonyms) to be used in EXSCLAIM

const InputSynonyms = (props) => {
    
  return (
    <Box sx={{ padding: 1 }}>
      <Stack direction="row" spacing={2}>
        <Typography>Synonyms:</Typography>
        <Autocomplete
          multiple
          freeSolo
          id="synonyms"
          options={[]}
          getOptionLabel={(option) => option}
          renderInput={(params) => (
            <TextField
              {...params}
              margin="dense"
              label="Synonyms"
            />
          )}
          sx={{ width: 300, minHeight: 50 }}
          onChange={(event, values) => {
            props.setSynonyms(values);
          }}
        />
      </Stack>
    </Box>
  )
}
      
export default InputSynonyms;