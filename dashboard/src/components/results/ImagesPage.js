import React from 'react';
import {IconButton, ImageList, ImageListItem, ImageListItemBar, Link, Tooltip} from '@mui/material';
import InfoIcon from '@mui/icons-material/Info';
import CropImage from '../images/CropImage';
import PropTypes from 'prop-types';

/**
 * Displays the subfigure results of the user's input in the subfigure results menu and the query menu.
 */
const ImagesPage = (props) => {

	/**
	 * find figure data of a subfigure given the figure's id
	 */
	function subFigureFindFigure(id) {
		return props.figures.find(item => item.figure_id === id);
	}

	/**
	 * find article data of a subfigure given the figure's id
\	 */
	function subFigureFindArticle(id) {
		let figure = subFigureFindFigure(id);
		let article_id = figure?.article;
		return props.articles.find(item => item.doi === article_id);
	}

	// if there are subfigures that match the inputted queries, return those. If not, return no images found
	return (
		<div>
			{props.subFigures.length > 0 ? (
				<ImageList sx={{ maxHeight: 590 }} cols={3}>
					{props.subFigures.map((subfigure) => (
							<ImageListItem key={subfigure["id"]}>
								{/* the cropped image */}
								<CropImage
									url={subFigureFindFigure(subfigure?.figure)?.url}
									data={subfigure}
								/>
								{/* display the subfigure's caption, original article (link to original article if user links on the article name), and subfigure name */}
								<ImageListItemBar
									title={subfigure["id"]}
									subtitle={
										<Link href={subFigureFindArticle(subfigure?.figure)?.url}
											  target="_blank" underline="hover" color="white">
											{subFigureFindArticle(subfigure?.figure)?.title}
										</Link>
									}
									actionIcon={
										// display the subfigure captions when user hovers over info icon if there are captions. If not, return no captions available
										<Tooltip title={(subfigure?.caption !== null) ? (subfigure?.caption) : ("No captions available")}>
											<IconButton
												sx={{ color: 'rgba(255, 255, 255, 0.54)' }}
												aria-label={`info about ${subFigureFindArticle(subfigure?.figure)?.title}`}>
												<InfoIcon />
											</IconButton>
										</Tooltip>
									}
								/>
							</ImageListItem>
						)
					)}
				</ImageList>
			) : (
				'No articles/figures available'
			)}
		</div>
	)
}

ImagesPage.propTypes = {
	/**
	 * The list of articles scraped by EXSCLAIM!
	 */
	articles: PropTypes.array,

	/**
	 * The list of figures scraped by EXSCLAIM!
	 */
	figures: PropTypes.array,

	/**
	 * The list of subfigures discovered by EXSCLAIM!
	 */
	subFigures: PropTypes.array
}

export default ImagesPage;