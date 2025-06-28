import React from 'react'
import { useState, useEffect } from 'react';
import { Autocomplete, FormControlLabel, FormGroup, TextField, FormLabel, Radio, RadioGroup } from '@mui/material';
import PropTypes from 'prop-types';

/**
 * Gets what keywords should be contained in/related to the subfigures.
 */
const KeyWords = (props) => {

	const [keywords, setKeywords] = useState([]); // set the displayed keywords

	// flatten a nested array to a normal array
	function flatten(arr) {
		return arr.reduce(function (flat, toFlatten) {
			return flat.concat(Array.isArray(toFlatten) ? flatten(toFlatten) : toFlatten);
		}, []);
	}

	// set user's query of where to look for keywords
	const changeKeywords = (event) => {
		let value = event.target.value;

		props.setKeywordType(value);

		if (value === 'caption') {
			let subFigureKeywords = props.allSubFigures.map((val) => val.keywords);
			setKeywords(Array.from(new Set(flatten(subFigureKeywords))));
		} else if (value === 'general') {
			let generalKeywords = props.allSubFigures.map((val) => val.general);
			setKeywords(Array.from(new Set(flatten(generalKeywords))));
		} else if (value === 'title') {
			let titleKeywords = props.articles.map((val) => val.title);
			setKeywords(Array.from(new Set(flatten(titleKeywords))));
		}
	}

	// set default keywords to be from the captions
	useEffect(() => {
		let subFigureKeywords = props.allSubFigures.map((val) => val.keywords);
		setKeywords(Array.from(new Set(flatten(subFigureKeywords))));

	}, [props.allSubFigures])

	return (
		<div>
			<FormGroup>
				<FormLabel id="keywords label">Subfigures containing keywords in:</FormLabel>
				<RadioGroup
					aria-labelledby="keywords buttons label"
					defaultValue="caption"
					name="keywords buttons"
					onChange={changeKeywords}
				>
					<FormControlLabel sx={{ height: 20 }}  value="caption" control={<Radio size="small" />} label="Subfigure Caption" />
					<FormControlLabel sx={{ height: 20 }}  value="general" control={<Radio size="small" />} label="General Article" />
					<FormControlLabel sx={{ height: 20 }}  value="title" control={<Radio size="small" />} label="Article's Title" />
				</RadioGroup>
			</FormGroup>

			<Autocomplete
				disablePortal
				id="combo-box-demo"
				options={keywords}
				sx={{ width: '65%', minHeight: 40, margin: 1 }}
				renderInput={(params) => <TextField {...params} label="Keywords" />}
				size="small"
				onChange={(event, value) => {
					props.setKeyword(value);
				}}
			/>
		</div>
	)
}

KeyWords.propTypes = {
	/**
	 *
	 */
	keywordType: PropTypes.string,
	/**
	 *
	 */
	allSubFigures: PropTypes.array,
	/**
	 *
	 */
	articles: PropTypes.array,
}

export default KeyWords;