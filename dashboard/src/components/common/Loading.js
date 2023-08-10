import React from 'react';
import { Box, Typography, CircularProgress, Stack } from '@mui/material';

// The loading page that appears when UI is getting and posting information from the API

// box container containing the loading components
const loadingDefault = {
  width: '95%',
  height: 450,
  padding: 2,
  justifyContent: "center",
  alignItems: "center",
  alignContent: "center",
  m: 2
}

const Loading = () => {
    
  return (
    <Box sx={loadingDefault} display="flex">
      <Stack alignItems="center"> 
        <CircularProgress size={60} />
        <Typography variant="h5" color="#4285F4">Loading Menu and Subfigures...</Typography>
      </Stack>
     </Box>
  )
}
        
export default Loading;