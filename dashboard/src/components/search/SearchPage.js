import React from 'react'
import { Box, Paper, Stack, styled, Autocomplete, FormLabel, FormControl, FormGroup, FormControlLabel, FormHelperText, Checkbox, Textfield, Slider, Button } from '@mui/material';
// This page comes second in importance. The main idea is
// to create an html form to mimic an exsclaim query json
// to send a post request to the api that will initiate
// a run of the pipeline

// make a side menu and you can change to change the results displayed by ImagesPage
// https://www.youtube.com/watch?v=WV6u_6ZNWkQ&ab_channel=AnthonySistilli
// https://mui.com/material-ui/react-popover/ at the anchor playground section

const SubHeaderBox = styled(Paper)(({ theme }) => ({
    backgroundColor: '#00CAF5',
    ...theme.typography.body2,
    padding: theme.spacing(1),
    textAlign: 'center',
    color: '#fff',
  }));

const SearchPage = () => {
    return (
        <Box sx={{ width: '100%' }}>
            <Stack spacing={2}>
                <SubHeaderBox>Keywords</SubHeaderBox>
                {/* checkbox and autocomplete */}
                <SubHeaderBox>Classification</SubHeaderBox>
                {/* checkbox */}
                <SubHeaderBox>License</SubHeaderBox>
                {/* checkbox */}
                <SubHeaderBox>Scale</SubHeaderBox>
                {/* textfield (number), textfield (number), and slider */}
                <SubHeaderBox>Submission</SubHeaderBox>
                <Button variant="contained">Submit</Button>
            </Stack>
        </Box>
    )
}

export default SearchPage;