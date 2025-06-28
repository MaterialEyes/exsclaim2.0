import React from 'react';
import { useState } from 'react';
import { Box, Grid, Paper, styled, Stack } from '@mui/material';
import OutputName from '../inputs/OutputName.js';
import JournalFamily from '../inputs/JournalFamily.js';
import NumArticles from '../inputs/NumArticles.js';
import SortBy from '../inputs/SortBy.js';
import OpenAccess from '../inputs/OpenAccess.js';
import InputTerm from '../inputs/InputTerm.js';
import InputSynonyms from '../inputs/InputSynonyms.js';
import Model from '../inputs/Model.js';
import InputButton from '../inputs/InputButton.js';
import PropTypes from 'prop-types';

// a blue-colored header box
const HeaderBox = styled(Paper)(({ theme }) => ({
	backgroundColor: '#0cb1f7',
	...theme.typography.b1,
	padding: theme.spacing(1),
	textAlign: 'center',
	color: '#fff',
	width: '100%'
}));

// box container containing the query menu
const boxDefault = {
	width: '95%',
	height: 450,
	padding: 2,
	justifyContent: "center",
	display: 'flex',
	m: 2,
}

/**
 * One big container with the input query menu for the user to run EXSCLAIM
 */
const Query = (props) => {

	const [outputName, setOutputName] = useState(""); // set output EXSCLAIM result file name
	const [numArticles, setNumArticles] = useState(0); // set number of articles to parse
	const [term, setTerm] = useState(""); // set term
	const [synonyms, setSynonyms] = useState([]); // set synonyms
	const [journalFamily, setJournalFamily] = useState("Nature"); // set the journal family
	const [sort, setSort] = useState("relevant"); // set sort type
	const [access, setAccess] = useState(false); // set open-access or not
	const [model, setModel] = useState("vicuna"); // set the llm
	const [modelKey, setModelKey] = useState(""); // set the user's personal key to run certain llms

	// all props that need to be passed to the submit button and the API
	const allProps = {
		outputName: outputName,
		numArticles: numArticles,
		term: term,
		synonyms: synonyms,
		journalFamily: journalFamily,
		sort: sort,
		access: access,
		model: model,
		modelKey: modelKey,
		setLoadResults: props.setLoadResults,
		fast_api_url: props.fast_api_url,
		setAlert: props.setAlert,
		setAlertContent: props.setAlertContent,
		setAlertSeverity: props.setAlertSeverity,
	}

	return (
		<div id={props.id}>
			<Box sx={boxDefault}>
				<Box sx={{ width: "70%" }}>
					<Grid container spacing={2}>
						<Grid item xs={12}>
							<HeaderBox>Input Query</HeaderBox>
						</Grid>

						<Grid item xs={6}>
							<Stack spacing={1}>
								<OutputName setOutputName={setOutputName} />
								<NumArticles setNumArticles={setNumArticles} />
								<InputTerm setTerm={setTerm} />
								<InputSynonyms setSynonyms={setSynonyms} />
							</Stack>
						</Grid>

						<Grid item xs={6}>
							<Stack spacing={1}>
								<JournalFamily setJournalFamily={setJournalFamily} journalFamilies={props.journalFamilies} />
								<SortBy setSort={setSort} />
								<OpenAccess access={access} setAccess={setAccess} />
								<Model model={model} setModel={setModel} modelKey={modelKey} setModelKey={setModelKey} available_llms={props.available_llms} />
								<InputButton {...allProps} />
							</Stack>
						</Grid>
					</Grid>
				</Box>
			</Box>
		</div>
	)
}

Query.propTypes = {
	/**
	 * If the query page should be loaded (false) or the results page (true).
	 */
	loadResults: PropTypes.bool,
	/**
	 * The setter for the loadResults variable.
	 */
	setLoadResults: PropTypes.func,
	/**
	 * The id of the query object.
	 */
	id: PropTypes.string,
	/**
	 * The API's URL.
	 */
	fast_api_url: PropTypes.string,

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

	/**
	 * The list of available journal families to search through.
	 */
	journalFamilies: PropTypes.arrayOf(PropTypes.string),
}

Query.defaultProps = {
	id: "query",
}

export default Query;