import React from 'react'
import { FormGroup, FormControlLabel, Checkbox } from '@mui/material';
import PropTypes from 'prop-types';

/**
 * Gets whether the subfigure should come from an open-source project or not.
 */
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
                  props.setLicense(!props.license) // set status of license after user input
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

License.propTypes = {
    /**
     *
     */
    license: PropTypes.bool
}

export default License;