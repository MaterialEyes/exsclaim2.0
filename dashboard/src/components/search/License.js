import React from 'react'
import { FormGroup, FormControlLabel, Checkbox } from '@mui/material';

//Focuses on if the subfigure comes from an open-source project or not

const License = (props) => {

  return (
    <div>
      <FormGroup>
        <FormControlLabel
          sx={{ height: 20}} 
          control={
            <Checkbox
              id="license"
              size="small" 
              onChange={
                ()=> {
                  props.setLicense(props.license ? false : true)
                }
              }
            />
          }
          label="Include Only Open Access" 
        />
      </FormGroup>
    </div>
  )
}

export default License;