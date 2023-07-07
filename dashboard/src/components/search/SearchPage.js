import React from 'react'
import { Box, Paper, Stack, styled } from '@mui/material';
import KeyWords from './KeyWords';
import Classification from './Classification';
import License from './License';
import Scale from './Scale';
import Submit from './Submit';

// This page comes second in importance. The main idea is
// to create an html form to mimic an exsclaim query json
// to send a post request to the api that will initiate
// a run of the pipeline

const SubHeaderBox = styled(Paper)(({ theme }) => ({
  width: "98%",
  backgroundColor: '#00CAF5',
  ...theme.typography.b1,
  padding: theme.spacing(0.5),
  textAlign: 'center',
  color: '#fff',
}));

const SearchPage = (props) => {
  return (
    <Box sx={{ width: '100%' }}>
      <Stack spacing={1} >
        <SubHeaderBox>Keywords</SubHeaderBox>
        <KeyWords
          {...props}
        />
        <SubHeaderBox>Classification</SubHeaderBox>
        <Classification
          {...props}
        />
        <SubHeaderBox>License</SubHeaderBox>
        <License 
          {...props}
        />
        <SubHeaderBox>Scale</SubHeaderBox>
        <Scale
          {...props}
        />
        
        <Submit
          {...props}
        />
      
      </Stack>
    </Box>
  )
}

export default SearchPage;