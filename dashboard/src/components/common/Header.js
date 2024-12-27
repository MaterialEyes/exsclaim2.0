import React from 'react';
import { Typography, Stack } from '@mui/material';
import PropTypes from "prop-types";

/**
 * The header of the app, introduces the user to the EXSCLAIM UI and how to use it
 */
const Header = (props) => {
	return (
		<Stack id={props.id} justifyContent="center">
			<div style={{ textAlign: "center" }}>
				<img src="/assets/ExsclaimLogo.png" alt="EXSCLAIM Logo" style={{ maxWidth: 350, height: "auto" }}></img>
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
	id: "header"
}

Header.propTypes = {
	/**
	 * The id of the header.
	 */
	id: PropTypes.string
}

export default Header;