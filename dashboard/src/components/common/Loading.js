import React from 'react';
import { Box, Typography, CircularProgress, Stack } from '@mui/material';

const loadingDefault = {
  width: '95%',
  height: 400,
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