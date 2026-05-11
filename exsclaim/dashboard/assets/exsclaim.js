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
		},
		credentials: "include"
	});

	const data = await response.json();
	switch (response.status) {
		case 200:
			return data["status"];
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
	const response = await fetch(`${baseUrl}/results/v1/${id}/articles`, {
		method: "GET",
		headers: {
			"Access-Control-Allow-Origin": "*",
			"Content-Type": "application/json"
		},
		credentials: "include"
	})

	const json = await response.json();
	if(response.ok){
		return json;
	}
	console.error(json.detail);
	return [];
}

/**
 * Loads the full figures found during a run.
 * @param baseUrl The URL that points toward the EXSCLAIM API.
 * @param id The UUID of the run that you're interested in.
 * @param num The page number.
 * @returns {Promise<any>}
 */
const fetch_figures = async (baseUrl, id, num=-1) => {
	const response = await fetch(`${baseUrl}/results/v1/${id}/figures/?page=${num}`, {
		method: "GET",
		headers: {
			"Access-Control-Allow-Origin": "*",
			"Content-Type": "application/json"
		},
		credentials: "include"
	})

	const json = await response.json();
	if(response.ok){
		return json;
	}
	console.error(json.detail);
	return [];
}

/**
 * Loads the subfigures found during a run.
 * @param baseUrl The URL that points toward the EXSCLAIM API.
 * @param id The UUID of the run that you're interested in.
 * @param num The page number.
 * @returns {Promise<any>}
 */
const fetch_subfigures = async (baseUrl, id, num=-1) => {
	const response = await fetch(`${baseUrl}/results/v1/${id}/subfigures/?page=${num}`, {
		method: "GET",
		headers: {
			"Access-Control-Allow-Origin": "*",
			"Content-Type": "application/json"
		},
		credentials: "include"
	})

	const json = await response.json();
	if(response.ok){
		return json;
	}
	console.error(json.detail);
	return [];
}

const getDefault = function (value, default_value){
	if(value === undefined || value === null) { return default_value; }
	return value;
}

const getLocale = function() {
	return navigator.languages && navigator.languages.length ? navigator.languages[0] : navigator.language;
}

const formatTimespan = function(seconds, locale) {
	const time = {
		days: Math.floor(seconds / 86400),
		hours: Math.floor((seconds % 86400) / 3600),
		minutes: Math.floor((seconds % 3600) / 60),
		seconds: Math.floor(seconds % 60),
		milliseconds: Math.floor((seconds * 1000) % 1000),
		// nanoseconds: Math.floor((seconds * 1000000) % 1000)
	};
	return new Intl.DurationFormat(locale, { style: "digital" }).format(time);
}

window.dash_clientside = Object.assign({}, window.dash_clientside, {
	clientside: {
		setTheme: function(theme="dark", data) {
			if(data.first_visit === undefined){
				data.first_visit = false;
				if(window.matchMedia){
					if(window.matchMedia("(prefers-color-scheme: dark)")){
						theme = "dark";
					}
				}
			} else if (theme){
				theme = "light";
			} else {
				theme = "dark";
			}

			document.body.setAttribute("data-theme", theme);
			data.theme = theme;
			return data;
		},

		update_layout_state: async function(n_intervals, current_data, data){
			if(!current_data){
				throw window.dash_clientside.PreventUpdate;
			}

			const result_id = current_data.results_id;
			const fast_api_url = data.public_fastapi_url;
			let updated_data = { ...current_data };

			const status = await fetch_status(fast_api_url, result_id);
			switch(status){
				case "Running.":
					throw window.dash_clientside.PreventUpdate;
				case "Finished.":
					break;
				case "Closed due to an error.":
				case "Killed.":
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
			let filtered_subfigures = data.all_subfigures;

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
			const image_container = document.querySelector("#images-container");
			style = style !== undefined ? style : {};
			style.overflowX = "auto"; //hidden
			style.overflowY = "auto"; //visible

			// const children = images.props.children;
			// let count = Array.from(children.length).slice(1).filter(e => !window.getComputedStyle(e).hidden).length;
			// let count = children.length;

			if(image_container.clientHeight >= filter_components.clientHeight){
				style.maxHeight = filter_components.clientHeight;
				style.clientHeight = filter_components.clientHeight;
			} else {
				delete style.maxHeight;
			}

			return style;
		},

		updateScalePadding: function (value){
			document.querySelector("#scale-threshold")?.removeAttribute("style");
			return window.dash_clientside.no_update;
		},
	},

	user: {
		check_password: function(password){
			// Check if this is in login or signup mode
			const username = document.getElementById("username");
			if(username === null || username === undefined) { return [true, false]; }

			const checks = [
				["password_length", /^.{8,}$/i],
				["password_upper", /^.*[A-Z]+.*$/],
				["password_lower", /^.*[a-z]+.*$/],
				["password_number", /^.*\d+.*$/],
				["password_special", /^.*[!#$&?@^_(){}<>\[\]\/|=+,-.:;]+.*$/],
			];
			let valid = true;

			if(password === undefined){
				password = "";
			}

			for (const [id, regex] of checks) {
				const match = regex.test(password);
				if(!match){
					valid = false;
				}

				const li = document.getElementById(id);
				if(li === undefined || li === null) { continue; }

				li.className = `li-password ${match ? 'password-passed' : 'password-failed'}`;
			}

			return [valid, !valid];
		},

		check_email: function(email){
			let email_component = document.getElementById("email");
			const valid = email_component.validity.valid;

			return [valid, !valid];
		},

		send_form_data: async function(n_clicks, username, email, password, data, current_url) {
			if(n_clicks === undefined) { throw window.dash_clientside.PreventUpdate; }
			const formData = new FormData();
			let target_link;

			if(username === undefined || username === null){
				target_link = `${data.public_fastapi_url}/user/login`;
			}
			else{
				target_link = `${data.public_fastapi_url}/user/create_user`;
				formData.append("username", username);
			}

			formData.append("email", email);
			formData.append("password", password);

			try{
				const response = await fetch(target_link, {
					method: "POST",
					body: formData,
					credentials: "include"
				});

				if(!response.ok){
					return [true, [await response.text()], "danger", current_url, false];
					// Redirect back to where ever they came from
				}

				const cookieHeader = response.headers.get("Set-Cookie");
				if(cookieHeader){
					document.cookie = cookieHeader;
				}

				return [false, [], "success", document.referrer, true];
			} catch(e){
				return [true, [e], "danger", current_url, false];
			}
		},

		logout: async function(n_clicks, data, current_url) {
			if(n_clicks === undefined) { throw window.dash_clientside.PreventUpdate; }
			try{
				const response = await fetch(`${data.public_fastapi_url}/user/logout`, {
					method: "GET",
					credentials: "include"
				});

				if(!response.ok){
					return [true, [await response.text()], "danger", current_url, false];
				}

				const cookieHeader = response.headers.get("Set-Cookie");
				if(cookieHeader){
					document.cookie = cookieHeader;
				}

				return [false, [], "success", document.referrer, true];
			} catch(e){
				return [true, [e], "danger", current_url, false];
			}
		},

		previous_runs_regular_table: async function(n_clicks, data){
			if(n_clicks === undefined) { throw window.dash_clientside.PreventUpdate; }

			const api_url = data.public_fastapi_url;
			const response = await fetch(`${api_url}/user/previous_runs`, {
				method: "GET",
				headers: {
					"Access-Control-Allow-Origin": "*",
					"Content-Type": "application/json"
				},
				credentials: "include"
			});

			const runs = await response.json();
			const table = document.getElementById("previous-runs-table");

			const headers = ["ID", "Name", "Query", "Status", "# Articles", "# Figures", "Start Time", "End Time", "Run Time"];

			const table_header = `<tr><td>${headers.join("</td><td>")}</td></tr>`;
			let table_data = "";

			for(const run of runs){
				table_data += `<tr><td><a href="/results/${run.id}">${run.id}</a></td>`;
				for(const value of [run.name, run.term, run.status]){
					table_data += `<td>${value}</td>`;
				}

				for(const value of [run.num_articles, run.num_figures]){
					table_data += `<td>${value !== null ? value : ""}</td>`;
				}

				const start_time = Date.parse(run.start_time);
				table_data += `<td>${new Date(start_time).toLocaleString()}</td>`;

				let end_time, run_time;

				if(run.end_time !== null){
					end_time = new Date(Date.parse(run.end_time));
					run_time = run.run_time;

					table_data += `<td>${end_time.toLocaleString()}</td><td>${formatTimespan(run_time)}</td>`;
				} else{
					run_time = (Date.now() - start_time) / 1000;
					table_data += `<td></td><td data-start="${start_time}">${formatTimespan(run_time)}</td>`;
				}
			}

			table.innerHTML = table_header + table_data;

			setInterval(() => document.querySelectorAll("[data-start]").forEach((td) => {
				td.innerText = formatTimespan((Date.now() - td.dataset.start) / 1000);
			}), 1000);
			return [table_header, "hidden"];
		},

		previous_runs: async function(n_clicks, data, current_data){
			if(n_clicks === undefined) { throw window.dash_clientside.PreventUpdate; }
			else if(current_data !== undefined) { return dash_clientside.user.update_data_table(n_clicks, data, current_data); }

			const api_url = data.public_fastapi_url;
			const response = await fetch(`${api_url}/user/previous_runs`, {
				method: "GET",
				headers: {
					"Access-Control-Allow-Origin": "*",
					"Content-Type": "application/json"
				},
				credentials: "include"
			});

			const locale = getLocale();
			const runs = await response.json();
			let table_data = [];

			for(const run of runs){
				let status;
				if(run.status === "Finished"){
					status = `[${run.status}](${api_url}/results/${run.id})`
				} else {
					status = run.status;
				}

				table_data.push({
					id: `[${run.id}](/results/${run.id})`,
					name: run.name,
					status: status,
					num_articles: run.num_articles ?? '',
					num_figures: run.num_figures,
					query: run.term,
					start_time: Date.parse(run.start_time),
					end_time: Date.parse(run.end_time),
					run_time: Date.parse(run.run_time),
					run_id: run.id,
					// start_time_timestamp: start_time
				});
			}

			return [table_data, "hide", 1000, false];
		},

		previous_runs_backup: async function(n_clicks, data, current_data){
			if(n_clicks === undefined) { throw window.dash_clientside.PreventUpdate; }
			else if(current_data !== undefined) { return dash_clientside.user.update_data_table(n_clicks, data, current_data); }

			const api_url = data.public_fastapi_url;
			const response = await fetch(`${api_url}/user/previous_runs`, {
				method: "GET",
				headers: {
					"Access-Control-Allow-Origin": "*",
					"Content-Type": "application/json"
				},
				credentials: "include"
			});

			const locale = getLocale();
			const runs = await response.json();
			let table_data = [];

			for(const run of runs){
				const start_time = Date.parse(run.start_time);
				let end_time, run_time;

				if(run.end_time !== null){
					end_time = new Date(Date.parse(run.end_time)).toLocaleString(locale);
					run_time = formatTimespan(run.run_time, locale);
				} else{
					end_time = "";
					run_time = formatTimespan((Date.now() - start_time) / 1000, locale);
				}

				let status;
				if(run.status === "Finished"){
					status = `[${run.status}](${api_url}/results/${run.id})`
				} else {
					status = run.status;
				}

				table_data.push({
					id: `[${run.id}](/results/${run.id})`,
					name: run.name,
					status: status,
					num_articles: run.num_articles ?? '',
					num_figures: run.num_figures,
					query: run.term,
					start_time: new Date(start_time).toLocaleString(locale),
					end_time: end_time,
					run_time: run_time,
					run_id: run.id,
					start_time_timestamp: start_time
				});
			}

			return [table_data, "hide", 1000, false];
		},

		update_data_table: async function(n_clicks, exsclaim_data, current_data){
			let all_rows_finished = true;
			const locale = getLocale();
			const check_status = n_clicks % 60 === 0;
			const check_ids = [];
			const now = Date.now();

			for(let i = 0; i < current_data.length; i++){
				const row = current_data[i];
				if(row.end_time !== undefined && row.end_time.length > 0){
					continue;
				}

				all_rows_finished = false;
				row.run_time = formatTimespan((now - row.start_time_timestamp) / 1000, locale);

				if(check_status) {
					check_ids.push(i);
				}
				current_data[i] = row;
			}

			if(check_status){
				const api_url = exsclaim_data.public_fastapi_url;
				check_ids.forEach(i => {
					fetch_status(api_url, current_data[i].run_id).then(status => {
							if(status === false || status === "Running."){ return; }
							const run = current_data[i];
							current_data[i].status = status === "Finished." ? `[${run.status}](${api_url}/results/${run.id})` : status;
							current_data[i].end_time = new Date(now).toLocaleString(locale);
						}
					);
				});
			}

			return [current_data, "hide", 1000, all_rows_finished];
		}
	},

	query: {
		submit_query: async function(n_clicks, stored_data, output_name, journal_family, num_articles,
									 sort_by, term, synonyms, open_access, model, model_key, save_formats, ntfy_link,
									 ntfy_priority) {
			if(n_clicks === undefined) { throw window.dash_clientside.PreventUpdate; }

			// Validated required fields
			if(term === undefined || term === null || term.trim().length === 0){
				return [true, true, "A search term is required.", "danger", stored_data];
			}

			// Process synonyms
			let synonyms_list = [];
			if(synonyms !== null && synonyms !== undefined && synonyms.length > 0){
				synonyms_list = synonyms.split("\n").map((s) => s.trim());
			}

			const input_data = {
				name: getDefault(output_name, ""),
				journal_family: getDefault(journal_family, "Nature"),
				maximum_scraped: getDefault(num_articles, 0),
				sortby: getDefault(sort_by, "relevant"),
				term: term.trim(),
				synonyms: synonyms_list,
				save_format: save_formats,
				open_access: getDefault(open_access, false),
				llm: getDefault(model, "llama3.2"),
				model_key: getDefault(model_key, ""),
				ntfy: [],
			};

			if(ntfy_link !== null){
				input_data.ntfy.push({
					url: ntfy_link,
					priority: ntfy_priority !== null && ntfy_priority >= 1 && ntfy_priority <= 5 ? ntfy_priority : 3
				});
			}

			const api_url = stored_data.public_fastapi_url;

			try{
				const response = await fetch(`${api_url}/query`, {
					method: "POST",
					body: JSON.stringify(input_data),
					credentials: "include",
					headers: {
						"Accept": "application/json",
						"Access-Control-Allow-Origin": "*",
						"Access-Control-Allow-Headers": "Accept, Content-Type, mode",
						"Content-Type": "application/json",
					}
				});

				if(!response.ok){
					return [true, true, await response.text(), "danger", stored_data];
				}

				const json = await response.json();
				const result_id = json.result_id;
				stored_data.query_id = result_id;

				const status_link = `${api_url}/status/${result_id}`;
				const status_element = `<p>Query: <a href="/results/${result_id}">${result_id}</a> was submitted to the server. This page will automatically update when the results are available. You can also check the run's status at <a href=${status_link} target="_blank">${status_link}</a>.</p>`

				return [false, true, status_element, "success", stored_data];
			} catch(e){
				return [true, true, e, "danger", stored_data];
			}
		},

		check_results_status: async function(n_clicks, data) {
			if(n_clicks === undefined) { throw window.dash_clientside.PreventUpdate; }

			const query_id = data.query_id;
			const api_url = data.public_fastapi_url;

			const status = await fetch_status(api_url, query_id);
			if(/Running.?/.test(status)){ // Not ready, still running
				throw window.dash_clientside.PreventUpdate;
			}

			return [`/results/${query_id}`, true];
		},
	}
})