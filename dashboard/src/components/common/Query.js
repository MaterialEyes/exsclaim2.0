import React from 'react';
//import { useState, useEffect } from 'react';
import { Box, Grid, Paper, styled, Stack, Typography, Autocomplete, TextField, FormControlLabel, FormGroup, FormLabel, Radio, RadioGroup, Checkbox } from '@mui/material';

// One big container containing the input query menu for the user to run EXSCLAIM

const Query = () => {

  const HeaderBox = styled(Paper)(({ theme }) => ({
    backgroundColor: '#0cb1f7',
    ...theme.typography.b1,
    padding: theme.spacing(1),
    textAlign: 'center',
    color: '#fff',
    width: '100%'
  }));
    
  const boxDefault = {
    width: '95%',
    height: 350,
    padding: 2,
    justifyContent: "center",
    alignItems: "center",
    display: 'flex',
    m: 2,
  }
  
  return (
    <div>
      <Box sx={boxDefault}>
        <Box sx={{ width: "70%" }}>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <HeaderBox>Input Query</HeaderBox>
            </Grid>

            <Grid item xs={6}>
              <HeaderBox>First half</HeaderBox>
            </Grid>

            <Grid item xs={6}>
              <HeaderBox>Second half</HeaderBox>
            </Grid>
          </Grid>
        </Box>
      </Box> 
    </div>
  )
}
  
export default Query;

/* 
<Stack>
          <HeaderBox>Input Query</HeaderBox>
          <Grid 
            container 
            spacing={2}
            justify="center"
          >
            <Grid item xs={6}>
              <Grid 
                container 
                spacing={2}
                justify="center"
              >
                <Grid item xs={4}>
                  <Typography>Output Name:</Typography>
                </Grid>
                <Grid item xs={8}>
                  <TextField sx={{ width: 300, minHeight: 50 }}></TextField>
                </Grid>
                
                <Grid item xs={4}>
                  <Typography>Journal Family:</Typography>
                </Grid>
                <Grid item xs={8}>
                  <FormGroup>
                    <RadioGroup
                      aria-labelledby="journal family label"
                      defaultValue="nature"
                      name="journal family buttons"
                    >
                      <FormControlLabel sx={{ height: 30 }} value="nature" control={<Radio />} label="Nature" />
                      <FormControlLabel sx={{ height: 30 }} value="rcs" control={<Radio />} label="RCS" />
                    </RadioGroup>
                  </FormGroup>
                </Grid>

                <Grid item xs={4}>
                  <Typography>Max Number of Articles:</Typography>
                </Grid>
                <Grid item xs={8}>
                  <TextField
                    id="max-number-articles"
                    label="Max Articles"
                    type="number"
                    InputLabelProps={{
                        shrink: true,
                    }}
                    size="small"
                    margin="dense"
                    sx={{ width: 300, minHeight: 50 }}
                  />
                </Grid>

                <Grid item xs={4}>
                  <Typography>Sort by:</Typography>
                </Grid>
                <Grid item xs={8}>
                  <FormGroup>
                    <RadioGroup
                      aria-labelledby="sort label"
                      defaultValue="revelant"
                      name="sort buttons"
                    >
                      <FormControlLabel sx={{ height: 30 }}  value="revelant" control={<Radio />} label="Revelant" />
                      <FormControlLabel sx={{ height: 30 }}  value="recent" control={<Radio />} label="Recent" />
                    </RadioGroup>
                  </FormGroup>
                </Grid>
              </Grid>
            </Grid>

            <Grid item xs={6}>
              <Grid 
                container 
                spacing={2}
                justify="center"
              >
                <Grid item xs={4}>
                  <Typography>Open Access:</Typography>
                </Grid>
                <Grid item xs={8}>
                  <FormGroup>
                    <FormControlLabel
                      sx={{ height: 20}} 
                      control={
                        <Checkbox
                          id="access"
                          size="small" 
                        />
                      }
                    />
                  </FormGroup>
                </Grid>

                <Grid item xs={4}>
                  <Typography>Term:</Typography>
                </Grid>
                <Grid item xs={8}>
                  <TextField></TextField>
                </Grid>

                <Grid item xs={4}>
                  <Typography>Synonyms:</Typography>
                </Grid>
                <Grid item xs={8}>
                  <Autocomplete
                    multiple
                    freeSolo
                    id="synonyms"
                    options={[]}
                    getOptionLabel={(option) => option}
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        variant="standard"
                        label="Synonyms"
                      />
                    )}
                  />
                </Grid>
              </Grid>
            </Grid>
          </Grid>  
        </Stack>
*/