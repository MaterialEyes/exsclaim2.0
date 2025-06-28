import {Alert, IconButton, Collapse} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import PropTypes from "prop-types";

/**
 * On-screen notifications to the user using @mui/material's Alert
 */
const Notification = (props) => {

	return (
		<Collapse in={props.alert}>
			<Alert
				id={props.id}
				action={
					<IconButton
						aria-label="close"
						color="inherit"
						size="small"
						onClick={() => props.setAlert(false)}
					>
						<CloseIcon fontSize="inherit" />
					</IconButton>
				}
				severity={props.alertSeverity}>
				{props.alertContent}
			</Alert>
		</Collapse>
	)
}

Notification.defaultProps = {
	id: "notification"
}

Notification.propTypes = {
	/**
	 * The id of the header.
	 */
	id: PropTypes.string,

	/**
	 * If the alert should be shown to the user
	 */
	alert: PropTypes.bool,

	/**
	 * Sets if the alert should be shown to the user
	 */
	setAlert: PropTypes.func,

	/**
	 * The content that will be shown in the alert.
	 */
	setAlertContent: PropTypes.func,

	/**
	 * The severity of the alert.
	 */
	setAlertSeverity: PropTypes.func,
}


export default Notification;