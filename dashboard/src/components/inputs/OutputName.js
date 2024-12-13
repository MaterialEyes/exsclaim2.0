import React from 'react';
import { Box, Stack, Typography, TextField } from '@mui/material';
import PropTypes from 'prop-types';

// Handles and gets the output EXSCLAIM file name inputted by the user

const OutputName = (props) => {
	return (
		<Box sx={{ padding: 1 }}>
			<Stack direction="row" spacing={2}>
				<Typography>Output Name:</Typography>
				<TextField
					id="output-name"
					label="Output Name"
					margin="dense"
					sx={{ width: 300, minHeight: 50 }}
					onChange={(e) => {
						props.setOutputName(e.target.value);
					}}
				/>
			</Stack>
		</Box>
	)
}

OutputName.propTypes = {
	outputName: PropTypes.string
}

export default OutputName;