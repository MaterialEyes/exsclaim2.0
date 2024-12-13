import React from 'react';
import { Box, Stack, Typography, FormControlLabel, FormGroup, Radio, RadioGroup } from '@mui/material';
import PropTypes from 'prop-types';

// Gets the journal family where EXSCLAIM will parse through

const JournalFamily = (props) => {

	return (
		<Box sx={{ padding: 1 }}>
			<Stack direction="row" spacing={2}>
				<Typography>Journal Family:</Typography>
				<FormGroup>
					<RadioGroup
						aria-labelledby="journal family label"
						defaultValue="nature"
						name="journal family buttons"
						onChange={(event, value) => {
							props.setJournalFamily(value);
						}}
					>
						<FormControlLabel sx={{ height: 30 }} value="nature" control={<Radio />} label="Nature" />
						<FormControlLabel sx={{ height: 30 }} value="rcs" control={<Radio />} label="RCS" />
					</RadioGroup>
				</FormGroup>
			</Stack>
		</Box>
	)
}

JournalFamily.propTypes = {
	journalFamily: PropTypes.string
}

export default JournalFamily;