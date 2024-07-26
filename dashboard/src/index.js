import {fetchArticles, fetchArticle, fetchFigures, fetchSubFigures} from './services/ApiClient';
import NumArticles from "./components/inputs/NumArticles";
import InputTerm from "./components/inputs/InputTerm";
import OpenAccess from "./components/inputs/OpenAccess";
import JournalFamily from "./components/inputs/JournalFamily";
import Model from "./components/inputs/Model";
import InputButton from "./components/inputs/InputButton";
import SortBy from "./components/inputs/SortBy";
import OutputName from "./components/inputs/OutputName";
import InputSynonyms from "./components/inputs/InputSynonyms";
import Query from "./components/common/Query";
import Loading from "./components/common/Loading";
import Layout from "./components/common/Layout";
import Footer from "./components/common/Footer";
import NavigationBar from "./components/common/NavigationBar";
import Header from "./components/common/Header";
import License from "./components/search/License";
import Scale from "./components/search/Scale";
import Classification from "./components/search/Classification";
import SearchPage from "./components/search/SearchPage";
import Submit from "./components/search/Submit";
import KeyWords from "./components/search/KeyWords";
import CropImage from "./components/images/CropImage";
import ImagesPage from "./components/results/ImagesPage";
import ResultsPage from "./components/results/ResultsPage";

export {
	fetchArticles,
	fetchArticle,
	fetchFigures,
	fetchSubFigures,
	NumArticles,
	InputTerm,
	OpenAccess,
	JournalFamily,
	Model,
	InputButton,
	SortBy,
	OutputName,
	InputSynonyms,
	Query,
	Loading,
	Layout,
	Footer,
	NavigationBar,
	Header,
	License,
	Scale,
	Classification,
	SearchPage,
	Submit,
	KeyWords,
	CropImage,
	ImagesPage,
	ResultsPage,
}

// import React from 'react';
// import ReactDOM from 'react-dom';
// import './index.css';
// import App from './components/App';
// import reportWebVitals from './reportWebVitals';
//
// ReactDOM.render(
// 	<React.StrictMode>
// 		<App />
// 	</React.StrictMode>,
// 	document.getElementById('root')
// );
//
// // If you want to start measuring performance in your app, pass a function
// // to log results (for example: reportWebVitals(console.log))
// // or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
// reportWebVitals();
