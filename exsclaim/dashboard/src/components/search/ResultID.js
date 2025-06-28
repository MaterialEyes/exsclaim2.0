import PropTypes from 'prop-types';
import {TextField} from "@mui/material";
import React, { useState } from "react";

/**
 * The input box that holds the current run ID.
 * If the value is changed, the results from the new run ID will be added to the screen (alongside the previous values).
 */
const ResultID = (props) => {
	const [value, setValue] = useState(props.resultsID);

	const validateUUID = () => {
		const uuidPattern = /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/;
		if(!uuidPattern.test(value)){
			alert("Invalid UUID entered.");
			return;
		}
		props.setResultsID(value);
	};

	return (
		<TextField
			id="results-id"
			label="Results ID"
			type="text"
			value={value}
			InputLabelProps={{
				shrink: true,
			}}
			size="small"
			margin="none"
			sx={{ width: "90%", minHeight: 50 }}
			onChange={(e) => setValue(e.target.value)}
			onBlur={validateUUID}
		/>
	);
};

ResultID.propTypes = {
	/**
	 * The ID of the run who's results are being looked at.
	 */
	resultsID: PropTypes.string
};

export default ResultID;