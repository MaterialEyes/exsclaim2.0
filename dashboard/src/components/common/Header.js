import React from 'react';
import { Typography, Stack } from '@mui/material';
import logo from '../images/ExsclaimLogo.png';

const Header = () => {
  return (
    <Stack>
      <div style={{ textAlign: "center" }}>
        <img src={logo} alt="EXSCLAIM Logo" style={{ maxWidth: 350, height: "auto" }}></img>
      </div>
      <Typography variant="h5" sx={{ fontWeight: "bold" }}>Welcome to the EXSCLAIM UI!</Typography>
      <Typography>
        On this website, you can query the subfigures on the right to whatever you specified on the menu on the left.
        Have fun querying!
      </Typography>
    </Stack>
  )
}

export default Header;