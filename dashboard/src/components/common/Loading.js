import React from 'react';
import { Box, Typography, CircularProgress, Stack } from '@mui/material';
import PropTypes from 'prop-types';

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

/**
 * The loading page that appears when UI is getting and posting information from the API
 */
const Loading = (props) => {
  return (
    <Box id={props.id} sx={loadingDefault} display="flex">
      <Stack alignItems="center"> 
        <CircularProgress size={60} />
        <Typography variant="h5" color="#4285F4">Loading Menu and Subfigures...</Typography>
      </Stack>
     </Box>
  )
}

Loading.propTypes = {
    /**
     * The id of the loader.
     */
    id: PropTypes.string
}

export default Loading;