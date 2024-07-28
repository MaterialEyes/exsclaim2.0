import React from 'react';
import { Typography, Stack } from '@mui/material';
import PropTypes from "prop-types";

// The header of the app, introduces the user to the EXSCLAIM UI and how to use it

const Header = ({EXSCLAIM_LOGO_SRC}) => {
  return (
    <Stack justifyContent="center">
      <div style={{ textAlign: "center" }}>
        <img src={EXSCLAIM_LOGO_SRC} alt="EXSCLAIM Logo" style={{ maxWidth: 350, height: "auto" }}></img>
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

Header.defaultProps = {
    EXSCLAIM_LOGO_SRC: "/assets/ExsclaimLogo.png"
}

Header.propTypes = {
    EXSCLAIM_LOGO_SRC: PropTypes.string
}

export default Header;