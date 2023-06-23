import React from 'react';
import { Outlet, Link } from "react-router-dom";
import NavigationBar from "./NavigationBar"
import Footer from "./Footer"
import ImagesPage from '../images/ImagesPage';
import SearchPage from '../search/SearchPage';
import { Box, Grid, Paper, styled } from '@mui/material';

/*
 * Layout should be:
 * NavigationBar / Header
 * One big container divded into two: left side menu, right side figures
 * Footer 
 */

const HeaderBox = styled(Paper)(({ theme }) => ({
    backgroundColor: '#0cb1f7',
    ...theme.typography.body2,
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
                        <SearchPage />
                    </Grid>
                    <Grid item xs={8}>
                        <ImagesPage />
                    </Grid>
                </Grid>
            </Box>
        </ div>
    )
}

export default Layout;