import React from 'react'
import { Box, Paper, Stack, styled, Autocomplete, FormGroup, FormControlLabel, Checkbox, TextField, Slider, Button, Grid, Typography } from '@mui/material';
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

const keywords = ["nano"];

const SearchPage = () => {
    return (
        <Box sx={{ width: '100%' }}>
            <Stack spacing={2}>
                <SubHeaderBox>Keywords</SubHeaderBox>
                <Autocomplete
                    disablePortal
                    id="combo-box-demo"
                    options={keywords}
                    sx={{ width: 300, height: 30 }}
                    renderInput={(params) => <TextField {...params} label="Keywords" />}
                    size="small"
                />
                <FormGroup>
                    <FormControlLabel sx={{ height: 20}} control={<Checkbox defaultChecked size="small" />} label="Subfigure's Distributed Caption" />
                    <FormControlLabel sx={{ height: 20}} control={<Checkbox defaultChecked size="small" />} label="Subfigure's Containing Figure's Caption" />
                    <FormControlLabel sx={{ height: 20}} control={<Checkbox defaultChecked size="small" />} label="Article Title" />
                </FormGroup>

                <SubHeaderBox>Classification</SubHeaderBox>
                <Grid container spacing={1}>
                    <Grid item xs={6}>
                        <FormGroup>
                            <FormControlLabel sx={{ height: 20}} control={<Checkbox defaultChecked size="small" />} label="Microscopy" />
                            <FormControlLabel sx={{ height: 20}} control={<Checkbox defaultChecked size="small" />} label="Diffraction" />
                            <FormControlLabel sx={{ height: 20}} control={<Checkbox defaultChecked size="small" />} label="Graph" />
                            <FormControlLabel sx={{ height: 20}} control={<Checkbox defaultChecked size="small" />} label="Basic Photo" />
                        </FormGroup>
                    </Grid>
                    <Grid item xs={6}>
                    <FormGroup>
                            <FormControlLabel sx={{ height: 20}} control={<Checkbox defaultChecked size="small" />} label="Illustration" />
                            <FormControlLabel sx={{ height: 20}} control={<Checkbox defaultChecked size="small" />} label="Unclear" />
                            <FormControlLabel sx={{ height: 20}} control={<Checkbox defaultChecked size="small" />} label="Parent" />
                        </FormGroup>
                    </Grid>
                </Grid>

                <SubHeaderBox>License</SubHeaderBox>
                <FormGroup>
                    <FormControlLabel sx={{ height: 20}} control={<Checkbox defaultChecked size="small" />} label="Include Only Open Access" />
                </FormGroup>

                <SubHeaderBox>Scale</SubHeaderBox>
                <Grid container spacing={1}>
                    <Grid item xs={6}>
                        <TextField
                            id="outlined-number"
                            label="Min"
                            type="number"
                            InputLabelProps={{
                                shrink: true,
                            }}
                            size="small"
                            sx={{ width: 200}}
                        />
                    </Grid>
                    <Grid item xs={6}>
                        <TextField
                            id="outlined-number"
                            label="Max"
                            type="number"
                            InputLabelProps={{
                                shrink: true,
                            }}
                            size="small"
                            sx={{ width: 200}}
                        />
                    </Grid>
                </Grid>
                <Typography id="Confidence Threshold" gutterBottom sx={{ height: 10}}>
                    Specify confidence threshold:
                </Typography>
                <Slider
                    aria-label="Confidence Threshold"
                    defaultValue={0.3}
                    valueLabelDisplay="auto"
                    step={0.1}
                    marks
                    min={0.1}
                    max={1.0}
                    size="small"
                />

                <SubHeaderBox>Submission</SubHeaderBox>
                <Button sx={{ width: 200}} variant="contained">Submit</Button>
            </Stack>
        </Box>
    )
}

export default SearchPage;