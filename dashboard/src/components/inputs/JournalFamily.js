import React from 'react';
import { Box, Stack, Typography, FormControlLabel, FormGroup, Radio, RadioGroup } from '@mui/material';
import PropTypes from 'prop-types';

/**
 * Gets the journal family where EXSCLAIM! will parse through
 */
const JournalFamily = (props) => {

	return (
		<Box id={props.id} sx={{ padding: 1 }}>
			<Stack direction="row" spacing={2}>
				<Typography>Journal Family:</Typography>
				<FormGroup>
					<RadioGroup
						aria-labelledby="journal family label"
						defaultValue="Nature"
						name="journal family buttons"
						onChange={(event, value) => {
							props.setJournalFamily(value);
						}}
					>
						<FormControlLabel sx={{ height: 30 }} value="Nature" control={<Radio />} label="Nature" />
						<FormControlLabel sx={{ height: 30 }} value="RSC" control={<Radio />} label="RSC" />
						<FormControlLabel sx={{ height: 30 }} value="ACS" control={<Radio />} label="ACS" />
					</RadioGroup>
				</FormGroup>
			</Stack>
		</Box>
	)
}

JournalFamily.propTypes = {
	/**
	 * The id of the JournalFamily box.
	 */
	id: PropTypes.string,
	/**
	 * The journal family that will be searched through.
	 */
	journalFamily: PropTypes.string
}

export default JournalFamily;