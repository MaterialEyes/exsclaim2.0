import './App.css';
//import {
//  BrowserRouter, Routes, Route
//} from 'react-router-dom'
import Header from './common/Header'
import Layout from './common/Layout';
import Footer from './common/Footer';


function App() {
  return (
    <div className="App">
      <Header />
      <Layout></Layout>
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
