import React from 'react';
import { useState, useEffect } from 'react';
import ImagesPage from '../results/ImagesPage';
import SearchPage from '../search/SearchPage';
import { Box, Grid, Paper, styled } from '@mui/material';
import { fetchArticles, fetchSubFigures, fetchFigures } from '../../services/ApiClient';
//import TestImage from '../results/TestingImage';

/*
 * Layout of app should be:
 * NavigationBar / Header
 * One big container divded into two: left side menu, right side figures (this js file)
 * Footer 
 */

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

  const [articles, setArticles] = useState([]);
  const [figures, setFigures] = useState([]);
  const [allSubFigures, setAllSubFigures] = useState([]);  
  const [subFigures, setSubFigures] = useState([]);
  const [license, setLicense] = useState(false);
  const [classes, setClasses] = useState({"MC" : true,
                                          "DF" : true,
                                          "GR" : true,
                                          "PH" : true,
                                          "IL" : true,
                                          "UN" : true,
                                          "PT" : true});

  //const allClasses = ["IL", "GR", "PT", "PH", "MC", "DF", "UN"];

  const allProps = {
    setSubFigures: setSubFigures,
    subFigures: subFigures,
    allSubFigures: allSubFigures,
    figures: figures,
    articles: articles,
    license: license,
    setLicense: setLicense,
    classes: classes,
    setClasses: setClasses
  }

  const getArticles = async () => {
    const articlesFromServer = await fetchArticles()
    setArticles(articlesFromServer)
  }

  const getSubFigures = async (page) => {
    const subFiguresJson = await fetchSubFigures(page);
    const data = subFiguresJson["results"];
    setSubFigures(oldArray => [...oldArray, ...data]);
    setAllSubFigures(oldArray => [...oldArray, ...data]);  

    if (subFiguresJson.next && page < 10) {
      getSubFigures(page+1);
    }
  }
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

/* 
setSubFigures={setSubFigures}
              subfigurelist={subFigures}
              allsubfigurelist={allSubFigures}
              figurelist={figures}
              articlelist={articles}
              license={license}
              toggleLicense={toggleLicense}
*/