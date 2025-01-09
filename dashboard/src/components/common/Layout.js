import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import ImagesPage from '../results/ImagesPage';
import SearchPage from '../search/SearchPage';
import { Box, Grid, Paper, styled } from '@mui/material';
import { fetchArticles, fetchSubFigures, fetchFigures } from '../../services/ApiClient';
import Loading from './Loading';
import PropTypes from 'prop-types';

// a blue-colored header box
const HeaderBox = styled(Paper)(({ theme }) => ({
	backgroundColor: '#0cb1f7',
	...theme.typography.b1,
	padding: theme.spacing(1),
	textAlign: 'center',
	color: '#fff',
}));

// box container containing the menu and results
const boxDefault = {
	width: '95%',
	padding: 2,
	justifyContent: "center",
	alignItems: "center",
	display: 'flex',
	m: 2
}

/**
 * One big container containing the UI results page. It is divided into two parts: left side menu, right side figures.
 */
const Layout = (props) => {

	const { id } = useParams();
	const [ resultsID, setResultsID ] = useState(id);
	useEffect(() => {
		let title = `Results ID: ${resultsID}`;
		window.history.replaceState("", title, `/results/${resultsID}`);
		document.title = title;
	}, [resultsID]);

	const [articles, setArticles] = useState([]); // set all articles
	const [figures, setFigures] = useState([]); // set all figures
	const [allSubFigures, setAllSubFigures] = useState([]); // set all subfigures
	const [subFigures, setSubFigures] = useState([]); // set displayed subfigures
	const [license, setLicense] = useState(false); // set license
	const [classes, setClasses] = useState({"MC" : true,
		"DF" : true,
		"GR" : true,
		"PH" : true,
		"IL" : true,
		"UN" : true,
		"PT" : true}); // set classification
	const [scales, setScales] = useState({"threshold" : 0,
		"minWidth" : 0,
		"maxWidth" : 1600,
		"minHeight" : 0,
		"maxHeight" : 1600}); // set scales
	const [keywordType, setKeywordType] = useState('caption'); // set the keyword type
	const [keyword, setKeyword] = useState(''); // set the query keyword

	const [articlesLoaded, setArticlesLoaded] = useState(false); // wait for API article requests to finish
	const [figuresLoaded, setFiguresLoaded] = useState(false); // wait for API figure requests to finish
	const [subFiguresLoaded, setSubFiguresLoaded] = useState(false); // wait for API subfigure requests to finish

	const [figurePage, setFigurePage] = useState(1); // current figure page in the API
	const [subFigurePage, setSubFigurePage] = useState(1); // current subfigure page in the API

	// all props that need to be passed to the search page/ left-hand side menu
	const allProps = {
		subFigures: subFigures,
		setSubFigures: setSubFigures,
		allSubFigures: allSubFigures,
		figures: figures,
		articles: articles,
		license: license,
		setLicense: setLicense,
		classes: classes,
		setClasses: setClasses,
		scales: scales,
		setScales: setScales,
		keywordType: keywordType,
		setKeywordType: setKeywordType,
		keyword: keyword,
		setKeyword: setKeyword,
		setLoadResults: props.setLoadResults,
		resultsID: resultsID,
		setResultsID: setResultsID
	}

	// get articles from API
	const getArticles = async () => {
		const articlesJson = await fetchArticles(props.fast_api_url, resultsID);
		const articlesFromServer = articlesJson["results"];
		setArticles(articlesFromServer);
	}

	// get subfigures from API
	const getSubFigures = async (page) => {
		const subFiguresJson = await fetchSubFigures(props.fast_api_url, resultsID, page);
		const data = subFiguresJson["results"];

		setSubFigures(oldArray => [...oldArray, ...data]);
		setAllSubFigures(oldArray => [...oldArray, ...data]);

		if (subFiguresJson.next) {
			setSubFigurePage(subFigurePage+1);
		} else {
			setSubFiguresLoaded(true);
		}
	}

	// get figures from API
	const getFigures = async (page) => {
		const figuresJson = await fetchFigures(props.fast_api_url, resultsID, page);
		const data = figuresJson["results"];
		setFigures(oldArray => [...oldArray, ...data]);

		if (figuresJson.next) {
			setFigurePage(figurePage+1);
		} else {
			setFiguresLoaded(true);
		}
	}

	// loading in info from API
	useEffect(() => {
		getArticles();
		setArticlesLoaded(true);
	}, [resultsID]);

	useEffect(() => {
		getSubFigures(subFigurePage);
	}, [resultsID, subFigurePage]);

	useEffect(() => {
		getFigures(figurePage);
	}, [resultsID, figurePage]);

	// return a loading screen if API is still running, return menu and subfigures once loading is done
	return (
		<div id={props.id}>
			{(!articlesLoaded || !figuresLoaded || !subFiguresLoaded) ? (
				<Loading />
			) : (
				<Box sx={boxDefault}>
					<Grid container spacing={4}>
						<Grid item xs={4}>
							<HeaderBox>Menu</HeaderBox>
						</Grid>
						<Grid item xs={8}>
							<HeaderBox>Figure Results</HeaderBox>
						</Grid>
						<Grid item xs={4}>
							{/* left-hand side menu */}
							<SearchPage
								{...allProps}
							/>
						</Grid>
						<Grid item xs={8}>
							{/* right-hand side subfigure results */}
							<ImagesPage
								subFigures={subFigures}
								figures={figures}
								articles={articles}
							/>
						</Grid>
					</Grid>
				</Box>
			)}
		</ div>
	)
}

Layout.propTypes = {
	/**
	 * The id of the layout.
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
	 * The setter for the loadResults variable.
	 */
	setLoadResults: PropTypes.func,
}

Layout.defaultProps = {
	id: "layout"
}

export default Layout;