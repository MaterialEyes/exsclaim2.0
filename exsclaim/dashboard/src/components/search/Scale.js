import React from 'react'
import { TextField, Slider, Grid, InputAdornment, FormLabel } from '@mui/material';
import PropTypes from 'prop-types';

/**
 * Gets the scale and size of the subfigure results should be.
 */
const Scale = (props) => {

	const min = 0; // the minimum width/height of a subfigure
	const max = 1600; // the maximum width/height of a subfigure

	// set user's query of a minimum width/height
	const minTextChange = (event, key) => {
		let value = parseInt(event.target.value, 10);

		if (value > max) {value = max};
		if (value < min || !value) {value = min};

		let newScales = { ...props.scales};
		newScales[key] = value;
		props.setScales(newScales);
	}

	// set user's query of a maximum width/height
	const maxTextChange = (event, key) => {
		let value = parseInt(event.target.value, 10);

		if (value > max || !value) {value = max};
		if (value < min) {value = min};

		let newScales = { ...props.scales};
		newScales[key] = value;
		props.setScales(newScales);
	}

	// set user's query of confidence threshold
	// CURRENT DATA IN UI DOESN'T HAVE CONFIDENCE THRESHOLD VALUES
	const sliderChange = (event, newValue) => {
		/*
		let newScales = { ...props.scales};
		newScales["threshold"] = newValue;
		props.setScales(newScales);
		*/
		console.log(newValue);
	};

	return (
		<div>
			<Grid container id={props.id} spacing={1}>
				<Grid item xs={6}>
					<TextField
						id="min-number-width"
						label="Min Width"
						type="number"
						InputLabelProps={{
							shrink: true,
						}}
						InputProps={{
							endAdornment: <InputAdornment position="end">px</InputAdornment>,
							inputProps: { type: 'number', min: min, max: max }
						}}
						size="small"
						margin="dense"
						sx={{ width: "90%", minHeight: 50 }}
						onChange={(e) => minTextChange(e, "minWidth")}
					/>
				</Grid>
				<Grid item xs={6}>
					<TextField
						id="max-number-width"
						label="Max Width"
						type="number"
						InputLabelProps={{
							shrink: true,
						}}
						InputProps={{
							endAdornment: <InputAdornment position="end">px</InputAdornment>,
							inputProps: { type: 'number', min: min, max: max }
						}}
						size="small"
						margin="dense"
						sx={{ width: "90%", minHeight: 50 }}
						onChange={(e) => maxTextChange(e, "maxWidth")}
					/>
				</Grid>

				<Grid item xs={6}>
					<TextField
						id="min-number-height"
						label="Min Height"
						type="number"
						InputLabelProps={{
							shrink: true,
						}}
						InputProps={{
							endAdornment: <InputAdornment position="end">px</InputAdornment>,
							inputProps: { type: 'number', min: min, max: max }
						}}
						size="small"
						margin="none"
						sx={{ width: "90%", minHeight: 50 }}
						onChange={(e) => minTextChange(e, "minHeight")}
					/>
				</Grid>
				<Grid item xs={6}>
					<TextField
						id="max-number-height"
						label="Max Height"
						type="number"
						InputLabelProps={{
							shrink: true,
						}}
						InputProps={{
							endAdornment: <InputAdornment position="end">px</InputAdornment>,
							inputProps: { type: 'number', min: min, max: max }
						}}
						size="small"
						margin="none"
						sx={{ width: "90%", minHeight: 50 }}
						onChange={(e) => maxTextChange(e, "maxHeight")}
					/>
				</Grid>
			</Grid>

			<FormLabel id="keywords label">Specify confidence threshold:</FormLabel>
			<Slider
				aria-label="Confidence Threshold"
				defaultValue={0}
				valueLabelDisplay="auto"
				step={0.1}
				marks
				min={0}
				max={1.0}
				onChangeCommitted={sliderChange}
			/>
		</div>
	)
}

Scale.propTypes = {
	/**
	 *
	 */
	scales: PropTypes.array,

	id: PropTypes.string
}

Scale.defaultProps = {
	id: "scale-grid"
}

export default Scale;