import React from 'react'
import { Box, Paper, Stack, styled, Button } from '@mui/material';
import KeyWords from './KeyWords';
import Classification from './Classification';
import License from './License';
import Scale from './Scale';

// This page comes second in importance. The main idea is
// to create an html form to mimic an exsclaim query json
// to send a post request to the api that will initiate
// a run of the pipeline

// make a side menu and you can change to change the results displayed by ImagesPage
// https://www.youtube.com/watch?v=WV6u_6ZNWkQ&ab_channel=AnthonySistilli
// https://mui.com/material-ui/react-popover/ at the anchor playground section

const SubHeaderBox = styled(Paper)(({ theme }) => ({
    backgroundColor: '#00CAF5',
    ...theme.typography.b1,
    padding: theme.spacing(0.5),
    textAlign: 'center',
    color: '#fff',
  }));

const SearchPage = () => {
    return (
        <Box sx={{ width: '100%' }}>
            <Stack spacing={2}>
                <SubHeaderBox>Keywords</SubHeaderBox>
                <KeyWords />

                <SubHeaderBox>Classification</SubHeaderBox>
                <Classification />

                <SubHeaderBox>License</SubHeaderBox>
                <License />

                <SubHeaderBox>Scale</SubHeaderBox>
                <Scale />

                <SubHeaderBox>Submission</SubHeaderBox>
                <Button sx={{ width: 200}} variant="contained">Submit</Button>
            </Stack>
        </Box>
    )
}

export default SearchPage;