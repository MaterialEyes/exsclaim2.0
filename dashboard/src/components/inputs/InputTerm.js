import React from 'react';
import { Box, Stack, Typography, TextField } from '@mui/material';
import PropTypes from 'prop-types';

// Gets the main search term to be used in EXSCLAIM

const InputTerm = (props) => {

	return (
		<Box sx={{ padding: 1 }}>
			<Stack direction="row" spacing={2}>
				<Typography>Term:</Typography>
				<TextField
					id="term-input"
					label="Term"
					margin="dense"
					sx={{ width: 300, minHeight: 50 }}
					onChange={(e) => {
						props.setTerm(e.target.value);
					}}
				/>
			</Stack>
		</Box>
	)
}

InputTerm.propTypes = {
	term: PropTypes.string
}

export default InputTerm;