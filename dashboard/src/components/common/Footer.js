import React from 'react'
import { Box, Grid, Typography, Stack, Link } from '@mui/material';
import logo from './../images/Argonnelablogo.PNG';

// The footer of the app, contains more information about Argonne and EXSCLAIM

const Footer = () => {
  return (
    <Box sx={{
      width: "100%",
      height: 120,
      boxShadow: 10,
      bottom: 0,
      alignContent: "top"
    }}>
      <Grid container spacing={1} alignItems="center" justifyContent="center" >
        <Grid item xs={4}>
          {/* image and link to Argonne website */}
          <a href="https://www.anl.gov/">
            <img src={logo} alt="Argonne Logo" height={60} />
          </a>
        </Grid>
        <Grid item xs={8}>
          <Stack>
            {/* some links pertaining to EXSCLAIM */}
            <Typography variant="h6" sx={{ fontWeight: "bold" }}>More Info</Typography>
            <Link href="https://github.com/MaterialEyes/exsclaim" underline="hover"> EXSCLAIM GitHub Page</Link>
            <Link href="https://github.com/MaterialEyes/exsclaim-ui" underline="hover"> EXSCLAIM UI GitHub Page</Link>
            <Link href="https://arxiv.org/abs/2103.10631" underline="hover">EXSCLAIM Paper</Link>
          </Stack>
        </Grid>
      </Grid>
    </Box>
  )
}

export default Footer;