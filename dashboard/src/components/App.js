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

/*
 * Layout of app should be:
 * NavigationBar / Header
 * Menu and Results
 * Footer 
 */

function App() {

  const [loadResults, setLoadResults] = useState(false); // toggles between the query page and the results page

  return (
    <div className="App">
      <Header />
      {(loadResults) ? (
        <Layout setLoadResults={setLoadResults}></Layout>
      ) : (
        <Query setLoadResults={setLoadResults}></Query>
      )}
      <Footer />
    </div>
  );
}

App.propTypes = {
    loadResults: PropTypes.bool
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
