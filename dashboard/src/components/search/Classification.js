import React from 'react'
import { FormGroup, FormControlLabel, Checkbox, Grid } from '@mui/material';

// Focuses on what type the subfigure is

const Classification = (props) => {

  // set user's query of classification
  function setClassification(className) {
    let newClasses = { ...props.classes};
    newClasses[className] = (props.classes[className] ? false : true);
    props.setClasses(newClasses);
  }

  return (
    <div>
      <Grid container spacing={1}>
        <Grid item xs={6}>
          <FormGroup>
            <FormControlLabel 
              sx={{ height: 20}} 
              control={
                <Checkbox
                  id="microscopy"
                  defaultChecked 
                  size="small" 
                  onChange={
                    ()=> {
                      setClassification("MC")
                    }
                  }
                />
              } 
              label="Microscopy" 
            />
            <FormControlLabel 
              sx={{ height: 20}} 
              control={
                <Checkbox
                  id="diffraction"
                  defaultChecked 
                  size="small" 
                  onChange={
                    ()=> {
                      setClassification("DF")
                    }
                  }
                />
              }
              label="Diffraction" 
            />
            <FormControlLabel 
              sx={{ height: 20}} 
              control={
                <Checkbox
                  id="graph"
                  defaultChecked 
                  size="small" 
                  onChange={
                    ()=> {
                      setClassification("GR")
                    }
                  }
                />
              }
              label="Graph" 
            />
            <FormControlLabel 
              sx={{ height: 20}} 
              control={
                <Checkbox
                  id="photo"
                  defaultChecked
                  size="small"
                  onChange={
                    ()=> {
                      setClassification("PH")
                    }
                  }
                />
              }
              label="Photo" 
            />
          </FormGroup>
        </Grid>
        <Grid item xs={6}>
          <FormGroup>
            <FormControlLabel 
              sx={{ height: 20}} 
              control={
                <Checkbox
                  id="illustration"
                  defaultChecked 
                  size="small" 
                  onChange={
                    ()=> {
                      setClassification("IL")
                    }
                  }
                />
              }
              label="Illustration" 
            />
            <FormControlLabel 
              sx={{ height: 20}} 
              control={
                <Checkbox
                  id="unclear"
                  defaultChecked 
                  size="small" 
                  onChange={
                    ()=> {
                      setClassification("UN")
                    }
                  }
                />
              }
              label="Unclear" 
            />
            <FormControlLabel 
              sx={{ height: 20}} 
              control={
                <Checkbox
                  id="parent"
                  defaultChecked 
                  size="small" 
                  onChange={
                    ()=> {
                      setClassification("PT")
                    }
                  }
                />
              }
              label="Parent" 
            />
          </FormGroup>
        </Grid>
      </Grid>
    </div>
  )
}

export default Classification;