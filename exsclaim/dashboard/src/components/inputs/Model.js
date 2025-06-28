import React, { useState } from 'react';
import {Box, Stack, Typography, FormGroup, Select, MenuItem, TextField} from '@mui/material';
import PropTypes from 'prop-types';

/**
 * Gets what kind of LLM (Large Langauge Model) EXSCLAIM! will use.
 */
const Model = (props) => {

	const [showKey, setShowKey] = useState(false);
	// A dictionary of the model names and if they need APIs for a quick loop up
	const needsApi = Object.fromEntries(props.available_llms.map((llm, index) => (
		[llm["model_name"], llm["needs_api_key"]]
	)))

	// handles whether or not to show the model key text box depending on what model the user chooses to use
	function handleModelChange(value)  {
		props.setModel(value);

		if (needsApi[value]) {
			setShowKey(true);
		}
		else {
			setShowKey(false);
			props.setModelKey("");
		}
	}

	return (
		<Box sx={{ padding: 1 }}>
			<Stack direction="row" spacing={2}>
				<Typography>Large Language Model:</Typography>
				<FormGroup>
					<Select
						labelId="model-selection-label"
						id="model-selection"
						onChange={(event, value) => {
							handleModelChange(value.props.value);
						}}
						label="LLM:"
					>
						{
							props.available_llms.map((llm, index) => (
								<MenuItem value={llm["model_name"]}>{llm["display_name"]}</MenuItem>
							))
						}
					</Select>
				</FormGroup>
				{ /* show model key text box depending on if the user wants to use GPT or not */ }
				{
					showKey &&
					<TextField
						id="key-input"
						label="Model Key"
						margin="dense"
						sx={{ width: 300, minHeight: 50 }}
						onChange={(e) => {
							props.setModelKey(e.target.value);
						}}
					/>
				}
			</Stack>
		</Box>
	)
}

Model.propTypes = {
	/**
	 * The name of the LLM model.
	 */
	model: PropTypes.string.isRequired,
	/**
	 * The API Key needed to run the given LLM.
	 */
	modelKey: PropTypes.string,

	/**
	 * A dictionary of available models, and if they need an API key or not.
	 */
	available_llms: PropTypes.arrayOf(PropTypes.object),
}

export default Model;