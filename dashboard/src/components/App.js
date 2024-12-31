import './App.css';
//import {
//  BrowserRouter, Routes, Route
//} from 'react-router-dom'
import { useState } from 'react';
import Header from './common/Header'
import Layout from './common/Layout';
import Query from './common/Query';
import Footer from './common/Footer';
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

	return (
		<div id={props.id} className="App">
			<Header />
			{(loadResults) ? (
				<Layout setLoadResults={setLoadResults} queryResultsId={queryResultsId} fast_api_url={props.fast_api_url} />
			) : (
				<Query setLoadResults={setLoadResults} setQueryResultsId={setQueryResultsId} fast_api_url={props.fast_api_url} />
			)}
			<Footer />
		</div>
	);
}

App.defaultProps = {
	fast_api_url: "https://exsclaim.materialeyes.org"
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
	fast_api_url: PropTypes.string.isRequired
}

export default App;

/*

<BrowserRouter>
          <Routes>
              <Route path="/" element={<Layout />}>
                  <Route index element={<ResultsPage />} />
                  <Route path="search" element={<SearchPage />} />
              </Route>
          </Routes>
      </BrowserRouter>

*/
