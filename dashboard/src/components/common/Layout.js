import React from 'react';
import { Outlet, Link } from "react-router-dom";
import NavigationBar from "./NavigationBar"
import Footer from "./Footer"
import { Box, Grid, Paper, styled } from '@mui/material';

/*
 * Layout should be:
 * NavigationBar / Header
 * One big container divded into two: left side menu, right side figures
 * Footer 
 */

const Item = styled(Paper)(({ theme }) => ({
    backgroundColor: theme.palette.mode === 'dark' ? '#1A2027' : '#fff',
    ...theme.typography.body2,
    padding: theme.spacing(1),
    textAlign: 'center',
    color: theme.palette.text.secondary,
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
                    <Item>menu</Item>
                    </Grid>
                    <Grid item xs={8}>
                    <Item>images</Item>
                    </Grid>
                </Grid>
            </Box>
        </ div>
    )
}

export default Layout;