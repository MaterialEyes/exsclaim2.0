import React from 'react';
import { Box, Button } from '@mui/material';
import PropTypes from 'prop-types';
import { fetchStatus } from '../../services/ApiClient';

/**
 * Submits the user query to the API, which then runs EXSCLAIM.
 * After the subfigure results are loaded, the user is taken to the results page (Layout.js)
 */
const InputButton = (props) => {
	function checkResultsStatus(deadline){
		fetchStatus(props.fast_api_url, props.queryId).then((resultsReady) => {
			if(!resultsReady){
				setTimeout(() => requestIdleCallback(checkResultsStatus, {timeout: 60_000}), 60_000);
			} else {
				props.setLoadResults(true);
			}
		});
	}

	// the function that will send a post request with the user's input query to the API
	async function submitQuery() {
		// data that will be posted to the API
		var inputData = {
			"name" : props.outputName,
			"journal_family" : props.journalFamily,
			"maximum_scraped" : props.numArticles,
			"sortby" : props.sort,
			"term" : props.term,
			"synonyms" : props.synonyms,
			"save_format" : ["postgres"],
			"open_access" : props.access,
			"llm" : props.model,
			"model_key" : props.modelKey
		};

		if(inputData["term"].length === 0){
			// TODO: Add a way to notify the UI that a term is incorrect.
			console.log("A search term is required.");
			return;
		}

		// POST user input to API
		const link = `${props.fast_api_url}/query`;
		const response = await fetch(link, {
			method: "POST",
			headers: {
				"Accept": "application/json",
				"Access-Control-Allow-Origin": "*",
				"Access-Control-Allow-Headers": "Accept, Content-Type, mode",
				"Content-Type": "application/json",
				"mode": "no-cors"
			},
			body: JSON.stringify(inputData)
		});
		if(response.ok){
			console.log("The query was submitted to the server. The page will automatically update when the results are available.");
			const json = await response.json();
			props.queryId = json["result_id"];
		} else{
			console.error(await response.text());
		}
		switch (response.status){
			case 422:
				console.error(response.text());
				break;
			default:
				console.log(response);
		}

		requestIdleCallback(checkResultsStatus, {timeout: 60_000});
	}

	return (
		<Box sx={{ padding: 1 }}>
			<Button id={props.id} sx={{ width: 200}} variant="contained" onClick={submitQuery}>Submit</Button>
		</Box>
	)
}

InputButton.defaultProps = {
	id: "submit-query",
};

InputButton.propTypes = {
	/**
	 * The id of the button.
	 */
	id: PropTypes.string.isRequired,
	/**
	 *
	 */
	click: PropTypes.bool,
	/**
	 * The name of the output
	 */
	outputName: PropTypes.string,
	/**
	 * The journal family that will be searched through.
	 */
	journalFamily: PropTypes.string,
	/**
	 * The maximum number of articles to search through.
	 */
	numArticles: PropTypes.number,
	/**
	 * How the articles should be sorted.
	 */
	sort: PropTypes.string,
	/**
	 * The input term to search for.
	 */
	term: PropTypes.string,
	/**
	 * Any synonyms that are related to the search term.
	 */
	synonyms: PropTypes.arrayOf(PropTypes.string),
	/**
	 * If the articles should be open access or not.
	 */
	access: PropTypes.bool,
	/**
	 * The name of the LLM model.
	 */
	model: PropTypes.string,
	/**
	 * The API Key needed to run the given LLM.
	 */
	modelKey: PropTypes.string,
	// /**
	//  *
	//  */
	// setLoadResults: PropTypes.func
	/**
	 * The callback for when the button is clicked.
	 */
	setProps: PropTypes.func,
	/**
	 * The API's URL.
	 */
	fast_api_url: PropTypes.string,
	/**
	 * The id for the most recently submitted query.
	 */
	queryId: PropTypes.string,
}

InputButton.defaultProps = {
	id: "submit-query"
}

export default InputButton;