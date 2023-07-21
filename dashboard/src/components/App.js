import './App.css';
//import {
//  BrowserRouter, Routes, Route
//} from 'react-router-dom'
import Header from './common/Header'
import Layout from './common/Layout';
import Query from './common/Query';
import Footer from './common/Footer';

/*
 * Layout of app should be:
 * NavigationBar / Header
 * Menu and Results
 * Footer 
 */

function App() {
  return (
    <div className="App">
      <Header />
      <Query></Query>
      <Footer />
    </div>
  );
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
