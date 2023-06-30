import React from 'react'
import { Box, Grid, Typography, Stack, Link } from '@mui/material';
import logo from '../images/Argonnelablogo.PNG';

const Footer = () => {
    return (
        <Box sx={{
            width: "100%",
            height: 120,
            // backgroundColor: '#07004D',
            boxShadow: 10,
            bottom: 0,
            alignContent: "top"
        }}>
            <Grid container spacing={1} >
                <Grid item xs={4}>
                    <img src={logo} alt="Argonne Logo" height={60}></img>
                </Grid>
                <Grid item xs={8}>
                    <Stack>
                        <Typography variant="h6" sx={{ fontWeight: "bold" }}>More Info</Typography>
                        <Link href="https://github.com/MaterialEyes/exsclaim" underline="hover">GitHub Page</Link>
                        <Link href="https://www.anl.gov/" underline="hover">Argonne Website</Link>
                        <Link href="https://arxiv.org/abs/2103.10631" underline="hover">EXSCLAIM Paper</Link>
                    </Stack>
                </Grid>
            </Grid>
        </Box>
    )
}

export default Footer;