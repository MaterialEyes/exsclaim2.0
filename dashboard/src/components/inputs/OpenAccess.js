import React from 'react';
import {Box, Stack, FormControlLabel, FormGroup, Checkbox } from '@mui/material';
import PropTypes from "prop-types";

/**
 * Toggles if EXSCLAIM should only have open access results
 */
const OpenAccess = ({props}) => {
	return (
		<Box sx={{ padding: 1 }}>
			<Stack direction="row" spacing={2}>
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