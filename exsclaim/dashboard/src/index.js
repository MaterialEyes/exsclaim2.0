import {fetchArticles, fetchArticle, fetchFigures, fetchSubFigures} from './services/ApiClient.js';
import NumArticles from "./components/inputs/NumArticles.js";
import InputTerm from "./components/inputs/InputTerm.js";
import OpenAccess from "./components/inputs/OpenAccess.js";
import JournalFamily from "./components/inputs/JournalFamily.js";
import Model from "./components/inputs/Model.js";
import InputButton from "./components/inputs/InputButton.js";
import SortBy from "./components/inputs/SortBy.js";
import OutputName from "./components/inputs/OutputName.js";
import InputSynonyms from "./components/inputs/InputSynonyms.js";
import Query from "./components/common/Query.js";
import Loading from "./components/common/Loading.js";
import Layout from "./components/common/Layout.js";
import Footer from "./components/common/Footer.js";
import Header from "./components/common/Header.js";
import Notification from "./components/common/Notification.js";
import License from "./components/search/License.js";
import ResultID from "./components/search/ResultID.js";
import Scale from "./components/search/Scale.js";
import Classification from "./components/search/Classification.js";
import SearchPage from "./components/search/SearchPage.js";
import Submit from "./components/search/Submit.js";
import KeyWords from "./components/search/KeyWords.js";
import CropImage from "./components/images/CropImage.js";
import ImagesPage from "./components/results/ImagesPage.js";
import App from "./components/App.js";
// import React from "react";
// import ReactDOM from "react-dom/client";

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
	Header,
	Notification,
	License,
	ResultID,
	Scale,
	Classification,
	SearchPage,
	Submit,
	KeyWords,
	CropImage,
	ImagesPage,
	App,
}

// import './index.css';
// import App from './components/App';
// import reportWebVitals from './reportWebVitals';
//
// const root = ReactDOM.createRoot(document.getElementById("root"));
// root.render(
// 	<React.StrictMode>
// 		<App fast_api_url="http://localhost:8000"
// 			 available_llms={[{model_name: "llama3.2", needs_api_key: false, display_name: "LLama 3.2"}]}
// 			 journalFamilies={["Nature"]}
// 		/>
// 	</React.StrictMode>
// );
//
// // If you want to start measuring performance in your app, pass a function
// // to log results (for example: reportWebVitals(console.log))
// // or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
// reportWebVitals();
