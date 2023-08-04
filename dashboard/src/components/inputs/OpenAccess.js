import React from 'react';
import { Box, Stack, Typography, FormControlLabel, FormGroup, Checkbox } from '@mui/material';

// Toggles if EXSCLAIM should only have open access results

const OpenAccess = (props) => {
    
  return (
    <Box sx={{ padding: 1 }}>
      <Stack direction="row" spacing={2}>
        <Typography>Open Access:</Typography>
        <FormGroup>
          <FormControlLabel
            sx={{ height: 20}} 
            control={
              <Checkbox
                id="access"
                onChange={
                  ()=> {
                    props.setAccess(props.access ? false : true)
                  }
                }
              />
            }
          />
        </FormGroup>
      </Stack>
    </Box>
  )
}
        
export default OpenAccess;