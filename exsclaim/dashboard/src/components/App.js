import './App.css';
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { useState } from 'react';
import Layout from './common/Layout.js';
import Query from './common/Query.js';
import Header from './common/Header.js';
import Footer from './common/Footer.js';
import PropTypes from 'prop-types';

/**
 * Layout of app should be:
 * NavigationBar / Header
 * Menu and Results
 * Footer
 */
const App = (props) => {
	const [loadResults, setLoadResults] = useState(false); // toggles between the query page and the results page
	const [queryResultsId, setQueryResultsId] = useState(""); // The results ID for the API

	const [alert, setAlert] = useState(false);
	const [alertContent, setAlertContent] = useState('');
	const [alertSeverity, setAlertSeverity] = useState('success');

	return (
		<BrowserRouter>
			<Routes>
				<Route path="/" element={
				    <div id="app">
				        <Header alert={alert}
								setAlert={setAlert}
								alertSeverity={alertSeverity}
								alertContent={alertContent}/>
					    <Query setLoadResults={setLoadResults} setQueryResultsId={setQueryResultsId} fast_api_url={props.fast_api_url}
							   available_llms={props.available_llms} setAlert={setAlert} setAlertContent={setAlertContent} setAlertSeverity={setAlertSeverity}
							   journalFamilies={props.journalFamilies}
						/>
					    <Footer />
					</div>
				} />
				<Route path="/results/:id" element={
				    <div id="app">
				        <Header alert={alert}
								setAlert={setAlert}
								alertSeverity={alertSeverity}
								alertContent={alertContent}/>
					    <Layout setLoadResults={setLoadResults} queryResultsId={queryResultsId} fast_api_url={props.fast_api_url} />
					    <Footer />
					</div>
				} />
				<Route path="/healthcheck" element={
				    <div id="app">
				        <p>EXSCLAIM Dashboard is operating normally.</p>
					</div>
				} />
			</Routes>
		</BrowserRouter>
	);
}

App.defaultProps = {
	id: "exsclaim-app",
	fast_api_url: "https://exsclaim.materialeyes.org",
	available_llms: ["llama3.2"],
	alert: false,
	alertSeverity: "success",
	alertContent: "",
	journalFamilies: ["Nature"]
}

App.propTypes = {
	/**
	 * The id of the main app.
	 */
	id: PropTypes.string,

	/**
	 * If the results page should be loaded (true) or the query page (false).
	 */
	loadResults: PropTypes.bool,

	/**
	 * The ID for the results that were submitted from the Query page.
	 */
	queryResultsId: PropTypes.string,

	/**
	 * The API's URL.
	 */
	fast_api_url: PropTypes.string.isRequired,

	/**
	 * The list of available LLMs.
	 * The syntax should match LLM.models()
	 */
	available_llms: PropTypes.arrayOf(PropTypes.object).isRequired,

	/**
	 * If the alert should be shown to the user
	 */
	alert: PropTypes.bool,

	/**
	 * Sets if the alert should be shown to the user
	 */
	setAlert: PropTypes.func,

	/**
	 * The content of the alert that is shown to the user.
	 */
	alertContent: PropTypes.string,

	/**
	 * The setter for the alert content.
	 */
	setAlertContent: PropTypes.func,

	/**
	 * How severe the alert is.
	 */
	alertSeverity: PropTypes.string,

	/**
	 * The severity of the alert.
	 */
	setAlertSeverity: PropTypes.func,

	/**
	 * The list of available journal families to search through.
	 */
	journalFamilies: PropTypes.arrayOf(PropTypes.string).isRequired
}

export default App;
