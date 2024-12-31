import React from 'react';
import { Box, Stack, Typography, FormControlLabel, FormGroup, Radio, RadioGroup } from '@mui/material';
import PropTypes from 'prop-types';

/**
 * Gets the type of sort that EXSCLAIM will use
 */
const SortBy = (props) => {
  return (
    <Box sx={{ padding: 1 }}>
      <Stack direction="row" spacing={2}>
        <Typography>Sort by:</Typography>
        <FormGroup>
          <RadioGroup
            aria-labelledby="sort label"
            defaultValue="relevant"
            name="sort buttons"
            onChange={(event, value) => {
              props.setSort(value);
            }}
          >
            <FormControlLabel sx={{ height: 30 }}  value="relevant" control={<Radio />} label="Relevant" />
            <FormControlLabel sx={{ height: 30 }}  value="recent" control={<Radio />} label="Recent" />
          </RadioGroup>
        </FormGroup>
      </Stack>
    </Box>
  )
}

SortBy.propTypes = {
    /**
     * How the articles should be sorted.
     */
    sort: PropTypes.string
}
        
export default SortBy;