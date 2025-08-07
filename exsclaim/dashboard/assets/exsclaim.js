function updateBannerNumber(number=undefined){
	const banner = document.getElementById("figure-results-header");

	if(number === undefined){
		banner.innerText = "Figure Results";
	} else {
		banner.innerText = `Figure Results: ${number}`;
	}

	return banner.innerText;
}

// some functions to get data from the API

const fetch_status = async (baseUrl, id) => {
	const response = await fetch(`${baseUrl}/status/${id}`, {
		method: "GET",
		headers: {
			"Access-Control-Allow-Origin": "*",
			"Content-Type": "application/json"
		}
	});

	const data = await response.json();
	switch (response.status) {
		case 200:
			return data["status"] === "Finished.";
		case 404:
			console.error("An unknown ID was given to the server.");
			return false;
		case 422:
			console.error("An improperly formatted ID was inputted to the server.");
			return false;
		case 500:
			console.error("An unknown server-side error has occurred. Please try again later.");
			return false;
		case 503:
			console.error("An internal database error has occurred within the server. Please try again later.");
			return false;
		default:
			console.error("Unknown status code received from API.");
			return false;
	}
}

/**
 * Loads the articles found during a run.
 * @param baseUrl The URL that points toward the EXSCLAIM API.
 * @param id The UUID of the run that you're interested in.
 * @returns {Promise<any>}
 */
const fetch_articles = async (baseUrl, id) => {
	return fetch(`${baseUrl}/results/v1/${id}/articles`, {
			method: "GET",
			headers: {
				"Access-Control-Allow-Origin": "*",
				"Content-Type": "application/json"
			}
		}
	).then(response => {
		return response.json();
	});
}

/**
 * Loads the full figures found during a run.
 * @param baseUrl The URL that points toward the EXSCLAIM API.
 * @param id The UUID of the run that you're interested in.
 * @param num The page number.
 * @returns {Promise<any>}
 */
const fetch_figures = async (baseUrl, id, num=-1) => {
	return fetch(`${baseUrl}/results/v1/${id}/figures/?page=${num}`, {
			method: "GET",
			headers: {
				"Access-Control-Allow-Origin": "*",
				"Content-Type": "application/json"
			}
		}
	).then(response => {
		return response.json();
	});
}

/**
 * Loads the subfigures found during a run.
 * @param baseUrl The URL that points toward the EXSCLAIM API.
 * @param id The UUID of the run that you're interested in.
 * @param num The page number.
 * @returns {Promise<any>}
 */
const fetch_subfigures = async (baseUrl, id, num=-1) => {
	return fetch(`${baseUrl}/results/v1/${id}/subfigures/?page=${num}`, {
			method: "GET",
			headers: {
				"Access-Control-Allow-Origin": "*",
				"Content-Type": "application/json"
			}
		}
	).then(response => {
		return response.json();
	});
}

window.dash_clientside = Object.assign({}, window.dash_clientside, {
	clientside: {
		update_layout_state: async function(n_intervals, current_data, data){
			if(!current_data){
				throw window.dash_clientside.PreventUpdate;
			}

			const result_id = current_data.results_id;
			const fast_api_url = data.fast_api_url;
			let updated_data = { ...current_data };

			const status = await fetch_status(fast_api_url, result_id);
			switch(status){
				case "Running":
					throw window.dash_clientside.PreventUpdate;
				case "Finished":
					break;
				case "Closed due to an error":
				case "Killed":
					updated_data = Object.assign(updated_data, {
						status: status,
						results_available: false,
						articles_loaded: true,
						figures_loaded: true,
						subfigures_loaded: true,
					});
					return [updated_data, true, {"display": "none"}, {"display": "block"}];
			}

			// Results are ready, fetch all data
			const articles = await fetch_articles(fast_api_url, result_id);
			const figures = await fetch_figures(fast_api_url, result_id);
			const subfigures = await fetch_subfigures(fast_api_url, result_id);

			subfigures.forEach(subfigure => {
				const figure = figures.filter(figure => subfigure.figure_id === figure.id)[0] ?? null;
				let article = null;
				if (figure !== undefined) {
					article = articles.filter(article => article.id === figure.article_id)[0] ?? null;
				}
				subfigure.article = article;
				subfigure.figure = figure;
			});

			// Update the state
			const all_subfigures = updated_data.all_subfigures ?? [];
			all_subfigures.push(...subfigures);

			updated_data = Object.assign(updated_data, {
				results_available: true,
				articles: articles,
				figures: figures,
				all_subfigures: all_subfigures,
				subfigures: subfigures,
				articles_loaded: true,
				figures_loaded: true,
				subfigures_loaded: true
			});

			const articles_loaded = updated_data.articles_loaded ?? false;
			const figures_loaded = updated_data.figures_loaded ?? false;
			const subfigures_loaded = updated_data.subfigures_loaded ?? false;

			if (articles_loaded && figures_loaded && subfigures_loaded) {
				return [updated_data, true, {"display": "none"}, {"display": "block"}];
			} else {
				return [updated_data, false, window.dash_clientside.no_update, window.dash_clientside.no_update];
			}
		},

		filterImages: function (n_clicks, children, keywords, keyword_type, classifications, license_only, data, min_width, max_width, min_height, max_height, confidence) {
			const subfigures = data.all_subfigures;
			let filtered_subfigures = subfigures;

			// Remove message from previous filter if needed
			document.getElementById("filter-error")?.remove();

			// Filter by keywords:
			if (keywords !== undefined) {
				switch (keyword_type) {
					case "caption":
						filtered_subfigures = filtered_subfigures.filter((subfigure) => {
							const caption = subfigure.caption.toLowerCase();
							let includes_keyword = false;
							keywords.forEach((kw) => {
								if(caption.includes(kw.toLowerCase())){
									includes_keyword = true;
									return true;
								}
							});
							return includes_keyword;
						});
						break;
					case "title":
						filtered_subfigures = filtered_subfigures.filter((subfigure) => {
							const caption = subfigure.article?.title.toLowerCase();
							if(caption === undefined){
								return false;
							}
							let includes_keyword = false;
							keywords.forEach((kw) => {
								if(caption.includes(kw.toLowerCase())){
									includes_keyword = true;
									return true;
								}
							});
							return includes_keyword;
						});
						break;
				}
			}

			// Filter by classification
			if (classifications) {
				filtered_subfigures = filtered_subfigures.filter(
					subfigure => classifications.includes(subfigure.classification_code)
				);
			}

			// Filter by license
			if (license_only) {
				filtered_subfigures = filtered_subfigures.filter(
					subfigure => subfigure.article?.open
				);
			}

			// Filter by Image Shape
			if (min_width !== undefined){
				filtered_subfigures = filtered_subfigures.filter(subfigure => subfigure.width >= min_width);
			}

			if (max_width !== undefined){
				filtered_subfigures = filtered_subfigures.filter(subfigure => subfigure.width <= max_width);
			}

			if (min_height !== undefined){
				filtered_subfigures = filtered_subfigures.filter(subfigure => subfigure.height >= min_height);
			}

			if (max_height !== undefined){
				filtered_subfigures = filtered_subfigures.filter(subfigure => subfigure.height <= max_height);
			}

			// Filter by Confidence
			if (confidence !== undefined && confidence !== 0) {
				filtered_subfigures = filtered_subfigures.filter(
					subfigure => subfigure.confidence !== undefined && subfigure.confidence >= confidence
				);
			}

			data.subfigures = filtered_subfigures;

			filtered_subfigures = new Set(filtered_subfigures.map(subfigure => subfigure.id));

			let visibleFigures = 0;
			children.props.children.forEach((subfigure) => {
				const subfigure_id = subfigure.props.children.props.id;
				const subfigure_html = document.getElementById(subfigure_id).parentElement;
				if(filtered_subfigures.has(subfigure_id)){
					subfigure_html.hidden = false;
					visibleFigures++;
				}
				else {
					subfigure_html.hidden = true;
				}
			});

			if(visibleFigures === 0) {
				const child = document.createElement("div");
				child.id = "filter-error";
				child.className = "text-center";
				child.innerText = "No results match the selected filters";
				const container = document.getElementById("images-container");
				container.appendChild(child);
			}
			return children;
		},

		update_banner: function (children){
			try{
				children = document.getElementById("images-container").children[0].children;
				let count = Array.from(children).filter(e => !e.hidden).length;
				return updateBannerNumber(count);
			} catch (e) {
				return updateBannerNumber();
			}
		},

		update_title: function (result_id){
			document.querySelector("title").innerText = `EXSCLAIM Results: ${result_id}`;
			return window.dash_clientside.no_update;
		},

		updateImagePageHeight: function (images, style){
			const filter_components = document.querySelector("#filter-components");
			style = style !== undefined ? style : {};
			style.overflowX = "auto"; //hidden

			const children = images.props.children;
			let count = Array.from(children.length).slice(1).filter(e => window.getComputedStyle(e).display !== 'none').length;

			if(count > 1){
				style.overflowY = "scroll";
				style.maxHeight = filter_components.clientHeight;
			} else {
				delete style.overflowY;
			}

			return style;
		},

		updateScalePadding: function (value){
			document.querySelector("#scale-threshold")?.removeAttribute("style");
			return window.dash_clientside.no_update;
		}
	}
})