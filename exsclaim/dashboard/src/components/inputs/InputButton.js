import { Box, Button } from '@mui/material';
import PropTypes from 'prop-types';
import { useNavigate } from "react-router-dom";
import { fetchStatus } from '../../services/ApiClient.js';

/**
 * Submits the user query to the API, which then runs EXSCLAIM.
 * After the subfigure results are loaded, the user is taken to the results page (Layout.js)
 */
const InputButton = (props) => {
	const navigate = useNavigate();

	function checkResultsStatus(deadline){
		fetchStatus(props.fast_api_url, props.queryId).then((resultsReady) => {
			if(!resultsReady){
				setTimeout(() => requestIdleCallback(checkResultsStatus, {timeout: 60_000}), 60_000);
			} else {
				props.setLoadResults(true);
				navigate(`/results/${props.queryId}`);
			}
		});
	}

	/**
	 * the function that will send a post request with the user's input query to the API
	 * @returns {Promise<void>}
	 */
	async function submitQuery() {
		// data that will be posted to the API
		let inputData = {
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
			console.error("A search term is required.");
			props.setAlertContent("A search term is required.");
			props.setAlertSeverity("error");
			props.setAlert(true);
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
			const json = await response.json();
			const result_id = json["result_id"];
			props.queryId = result_id;

			props.setAlertContent(`Query: <a href="/status/${result_id}">${result_id}</a> was submitted to the server. This page will automatically update when the results are available.`);
			props.setAlertSeverity("success");
			props.setAlert(true);
		} else{
			props.setAlertContent(await response.text());
			props.setAlertSeverity("error");
			props.setAlert(true);
		}
		switch (response.status){
			case 422:
				props.setAlertContent(await response.text());
				props.setAlertSeverity("error");
				props.setAlert(true);

				break;
			default:
				props.setAlertContent(await response.text());
				props.setAlertSeverity("warning");
				props.setAlert(true);
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

	/**
	 * If the alert should be shown to the user
	 */
	setAlert: PropTypes.func,

	/**
	 * The content that will be shown in the alert.
	 */
	setAlertContent: PropTypes.func,

	/**
	 * The severity of the alert.
	 */
	setAlertSeverity: PropTypes.func,
}

InputButton.defaultProps = {
	id: "submit-query"
}

export default InputButton;