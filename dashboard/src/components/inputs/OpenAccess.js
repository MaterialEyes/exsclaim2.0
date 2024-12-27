import React from 'react';
import {Box, Stack, Typography, FormControlLabel, FormGroup, Checkbox, Radio} from '@mui/material';
import PropTypes from "prop-types";

/**
 * Toggles if EXSCLAIM should only have open access results
 */
const OpenAccess = ({props}) => {
	return (
		<Box sx={{ padding: 1 }}>
			<Stack direction="row" spacing={2}>
				{/*<FormControlLabel sx={{ height: 30 }} value="vicuna" control={<Radio />} label="Vicuna" />*/}
				{/*<Typography>Open Access:</Typography>*/}
				<FormGroup>
					<FormControlLabel
						sx={{ height: 20}}
						label={"Open Access:"}
						control={
							<Checkbox
								defaultChecked={true}
								onChange={
									()=> {
										props.setAccess(!props.access)
									}
								}
							/>
						}
					/>
				</FormGroup>
			</Stack>
		</Box>
	)
}

OpenAccess.defaultProps = {
	id: "open-access"
}

OpenAccess.propTypes = {
	/**
	 * The id of the open access box.
	 */
	id: PropTypes.string,
	/**
	 * If the articles should be open access or not.
	 */
	access: PropTypes.bool,
	/**
	 * To access the new value in Dash.
	 */
	setAccess: PropTypes.func
}

export default OpenAccess;