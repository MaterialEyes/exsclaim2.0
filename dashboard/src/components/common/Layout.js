import React from 'react';
import { useState, useEffect } from 'react';
import ImagesPage from '../results/ImagesPage';
import SearchPage from '../search/SearchPage';
import { Box, Grid, Paper, styled } from '@mui/material';
import { fetchArticles, fetchSubFigures, fetchFigures } from '../../services/ApiClient';
//import TestImage from '../results/TestingImage';

// One big container divded into two: left side menu, right side figures

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
  m: 2
}
  
const Layout = () => {

  
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

  // all props that need to be passed to other components                                        
  const allProps = {
    setSubFigures: setSubFigures,
    subFigures: subFigures,
    allSubFigures: allSubFigures,
    figures: figures,
    articles: articles,
    license: license,
    setLicense: setLicense,
    classes: classes,
    setClasses: setClasses,
    scales: scales,
    setScales: setScales
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

    if (subFiguresJson.next && page < 10) {
      getSubFigures(page+1);
    }
  }

  // get figures from API
  const getFigures = async (page) => {
    const figuresJson = await fetchFigures(page);
    const data = figuresJson["results"];
    setFigures(oldArray => [...oldArray, ...data]);  

    if (figuresJson.next) {
      getFigures(page+1);
    }
  }

  useEffect(() => {
    getArticles();
    getSubFigures(1);
    getFigures(1);
  
  }, [])

  return (
    <div>
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
    </ div>
  )
}

export default Layout;