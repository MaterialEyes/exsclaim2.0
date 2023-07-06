import React from 'react'
import { FormGroup, FormControlLabel, Checkbox, Grid } from '@mui/material';

// Focuses on what type the subfigure is

const Classification = () => {
  return (
    <div>
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
    </div>
  )
}

export default Classification;