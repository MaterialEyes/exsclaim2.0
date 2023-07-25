import React from 'react';
import { useState, useEffect } from 'react';
import ImagesPage from '../results/ImagesPage';
import SearchPage from '../search/SearchPage';
import { Box, Grid, Paper, styled } from '@mui/material';
import { fetchArticles, fetchSubFigures, fetchFigures } from '../../services/ApiClient';
import Loading from './Loading';

// One big container divided into two: left side menu, right side figures

const HeaderBox = styled(Paper)(({ theme }) => ({
  backgroundColor: '#0cb1f7',
  ...theme.typography.b1,
  padding: theme.spacing(1),
  textAlign: 'center',
  color: '#fff',
}));

const boxDefault = {
  width: '95%',
  padding: 2,
  justifyContent: "center",
  alignItems: "center",
  display: 'flex',
  m: 2
}
  
const Layout = (props) => {

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

  const [figurePage, setFigurePage] = useState(1); // figure page
  const [subFigurePage, setSubFigurePage] = useState(1); // subfigure page

  // all props that need to be passed to other components                                        
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
    setLoadResults: props.setLoadResults
  }

  // get articles from API
  const getArticles = async () => {
    const articlesFromServer = await fetchArticles()
    setArticles(articlesFromServer)
  }

  // get subfigures from API
  const getSubFigures = async (page) => {
    const subFiguresJson = await fetchSubFigures(page);
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
    const figuresJson = await fetchFigures(page);
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
  }, [])

  useEffect(() => {
    getSubFigures(subFigurePage);
  }, [subFigurePage])

  useEffect(() => {
    getFigures(figurePage);
  }, [figurePage])

  // return a loading screen if API is still running, return menu and subfigures once loading is done
  return (
    <div>
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
              <SearchPage 
                {...allProps}
              />
            </Grid>
            <Grid item xs={8}>
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

export default Layout;