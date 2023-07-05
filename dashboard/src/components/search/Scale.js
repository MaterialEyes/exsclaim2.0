import React from 'react'
import { TextField, Slider, Grid, Typography } from '@mui/material';

// Focuses on the scale and size of the subfigures

const Scale = () => {
    return (
        <div>
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
                        sx={{ width: 200, minHeight: 50 }}
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
                        sx={{ width: 200, minHeight: 50 }}
                    />
                </Grid>
            </Grid>
            <Typography id="Confidence Threshold" gutterBottom sx={{ height: 10}}>
                Specify confidence threshold:
            </Typography>
            <Slider
                aria-label="Confidence Threshold"
                defaultValue={0}
                valueLabelDisplay="auto"
                step={0.1}
                marks
                min={0}
                max={1.0}
            />
        </div>
    )
}

export default Scale;