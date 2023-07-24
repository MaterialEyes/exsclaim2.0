import React from 'react';
import { Typography, Stack } from '@mui/material';
import logo from '../images/ExsclaimLogo.png';

// The header of the app, introduces the user to the EXSCLAIM UI and how to use it

const Header = () => {
  return (
    <Stack justifyContent="center">
      <div style={{ textAlign: "center" }}>
        <img src={logo} alt="EXSCLAIM Logo" style={{ maxWidth: 350, height: "auto" }}></img>
      </div>
      <Typography variant="h5" sx={{ fontWeight: "bold" }}>Welcome to the EXSCLAIM UI!</Typography>
      <Typography>
        On this website, you can submit a query for EXSCLAIM to run through. <br/>
        Once you submit, a list of subfigures will appear on the right and a menu on the left. Then, you can query through the subfigures with the 
        left-hand-side menu. <br/>
        Have fun querying!
      </Typography>
    </Stack>
  )
}

export default Header;