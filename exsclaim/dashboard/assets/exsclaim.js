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
		case 202:
		case 209:
		case 210:
			return data;
		case 404:
			console.error("An unknown ID was given to the server.");
			return false;
		case 422:
			console.error("An improperly formatted ID was inputted to the server.");
			return false;
		case 500:
			console.error("An unknown server-side error has occurred. Please try again later.");
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
	const response = await fetch(`${baseUrl}/results/v1/${id}/figures?page=${num}`, {
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
	const response = await fetch(`${baseUrl}/results/v1/${id}/subfigures?page=${num}`, {
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
 * Loads the classification codes.
 * @param baseUrl The URL that points toward the EXSCLAIM API.
 * @returns {Promise<any>}
 */
const fetch_classification_codes = async (baseUrl) => {
	const response = await fetch(`${baseUrl}/classification_codes`, {
		method: "GET",
		headers: {
			"Access-Control-Allow-Origin": "*",
			"Content-Type": "application/json"
		},
		credentials: "include"
	})

	const codes = await response.json();
	if(response.ok){
		return Object.fromEntries(codes.map((code) => [code.code, code.name]));
	}
	console.error(codes);
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

const dagFuncs = window.dashAgGridFunctions = window.dashAgGridFunctions || {};
dagFuncs.colorByLabel = function(params){
	const default_color = { backgroundColor: "#ffffff00", color: "#000000" };
	const colors = [
		"#636EFA",
		"#EF553B",
		"#00CC96",
		"#AB63FA",
		"#FFA15A",
		"#19D3F3",
		"#FF6692",
		"#B6E880",
		"#FF97FF",
		"#FECB52",
	];

	if(!params.value){
		return default_color;
	}
	const result = params.value.match(/([a-z])/i);
	const label = result[0].toUpperCase();

	if(label.length === 0){
		return default_color;
	}

	const position = label.charCodeAt(0) - 65; //"A".charCodeAt(0);
	const color = colors[position % colors.length];

	return { backgroundColor: color || "var(--text)" };
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

		update_info_banner: async function(store, data) {
			let url = `${data.public_fastapi_url}/banner`;
			if(store.last_seen_banner !== undefined && store.last_seen_banner !== null){
				url += `?last_seen_banner=${store.last_seen_banner}`;
			}
			const response = await fetch(url, {
				method: "GET",
				headers: {
					"Access-Control-Allow-Origin": "*",
					"Content-Type": "application/json"
				},
				credentials: "omit"
			});

			switch (response.status) {
				case 204: // Nothing to show
					return [false, "", window.dash_clientside.no_update];
				case 200:
					const json = await response.json();
					store.last_seen_banner = json.id;
					return [true, json.content, store];
				default:
					const text = await response.text();
					console.error(`Could not receive banner text: ${text}`);
					return [false, text, window.dash_clientside.no_update];
			}
		},

		update_layout_state: async function(n_intervals, current_data, data){
			if(!current_data){
				throw window.dash_clientside.PreventUpdate;
			}

			const result_id = current_data.results_id;
			const fast_api_url = data.public_fastapi_url;
			let updated_data = { ...current_data };

			const status = await fetch_status(fast_api_url, result_id);
			switch(status.status){
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

		filterImages: function (n_clicks, keywords, keyword_type, classifications, license_only, data, min_width, max_width, min_height, max_height, confidence) {
			let filtered_subfigures = data.all_subfigures;
			classifications = new Set(classifications);

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
					subfigure => classifications.has(subfigure.classification_code)
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
			return filtered_subfigures;
		},

		update_ids_and_banner: function(visible_ids, ids) {
			const show = {display: "block"};
			const hide = {display: "none"};

			if(visible_ids === null || visible_ids === undefined){
				return [ids.map(() => show), `Figure Results: ${ids.length}`,
				ids.length === 0 ? show : hide];
			}

			visible_ids = new Set(visible_ids.map(subfigure => subfigure.id));
			let visible_figures = 0;
			const new_ids = ids.map((id) => {
				if(visible_ids.has(id.id)){
					visible_figures++;
					return show;
				}
				return hide;
			});
			return [new_ids, `Figure Results: ${visible_figures}`, visible_figures === 0 ? show : hide];
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

		previous_runs: async function(n_clicks, data){
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
				table_data += `<tr><td data-id="${run.id}"><a href="/results/${run.id}">${run.id}</a></td>`;
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
			return [table_header, false, false];
		},

		update_data_table: async function(n_clicks, exsclaim_data){
			let all_rows_finished = true;
			const unfinished_cells = document.querySelectorAll("[data-start]");
			const api_url = exsclaim_data.public_fastapi_url;
			const locale = getLocale();

			for(const cell of unfinished_cells){
				const row = cell.parentNode;
				const cells = row.querySelectorAll("td");
				const id = cells[0].dataset.id;

				fetch_status(api_url, id).then(status => {
					if(status === false || status.status === "Running."){
						all_rows_finished = false;
						return;
					}
					delete cells[8].dataset.start;
					cells[3].innerText = status.status;
					cells[7].innerText = new Date(Date.parse(status.end_time)).toLocaleString(locale);
					cells[8].innerText = formatTimespan(status.run_time);
				});
			}

			return !all_rows_finished;
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

			if(ntfy_link !== null && ntfy_link !== undefined){
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
			if(/Running.?/.test(status.status)){ // Not ready, still running
				throw window.dash_clientside.PreventUpdate;
			}

			return [`/results/${query_id}`, true];
		},
	},

	train: {
		load_previous_runs: async function(n_clicks, data){
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
			let output = [];

			for(const run of runs){
				let status;
				if(run.status !== "Finished"){
					continue;
				} else {
					status = run.status;
				}

				output.push({
					label: `${run.id} [${run.name}]`,
					value: run.id,
				});
			}

			return [output, output[0].value, false];
		},

		add_new_row: async function(n_clicks){
			if(n_clicks === undefined) { throw window.dash_clientside.PreventUpdate; }

			return {
				add: [{
					label: null,
					classification: "Unclear",
					x0: null,
					y0: null,
					x1: null,
					y1: null,
					label_x0: null,
					label_y0: null,
					label_x1: null,
					label_y1: null,
					subcaption: ""
				}]
			}
		},

		/**
		 * Acts as a cache so everytime a user removes then re-adds a run, another query isn't sent to the server to get the info again
		 */
		figures_per_run: [],

		/**
		 * The list of objects ...
		 */
		training_data: {},

		populate_figures: async function(selected_runs, data){
			const api_url = data.public_fastapi_url;
			if(typeof(selected_runs) === "string"){
				selected_runs = [selected_runs];
			}

			const init = {
				method: "GET",
				headers: {
					"Access-Control-Allow-Origin": "*",
					"Content-Type": "application/json"
				},
				credentials: "include"
			};

			const options = [];
			for(const selected_run of selected_runs){
				if(!this.figures_per_run.includes(selected_run.id)) { // TODO: Have a set just of run ids to check against
					let articles = await fetch_articles(api_url, selected_run);

					let figures = await fetch_figures(api_url, selected_run);

					let subfigures = await fetch_subfigures(api_url, selected_run);

					let response = await fetch(`${api_url}/results/v1/${selected_run}/subfigure_labels`, init);
					let labels = await response.json();

					let class_codes = await fetch_classification_codes(api_url);

					articles = Object.fromEntries(articles.map((article) => [article.id, article.url]));

					figures = Object.fromEntries(figures.map((fig) => [fig.id, {
						id: fig.id,
						url: fig.url,
						caption: fig.caption,
						run_id: fig.run_id,
						article_url: articles[fig.article_id],
						subfigures: []
					}]));

					labels = Object.fromEntries(labels.map((label) => [label.subfigure_id, {
						label: label.text,
						x0: label.x1,
						y0: label.y1,
						x1: label.x2,
						y1: label.y2
					}]));

					for(const subfigure of subfigures){
						const label = labels[subfigure.id];
						figures[subfigure.figure_id].subfigures.push({
							label: label?.label,
							classification: class_codes[subfigure.classification_code] ?? "Unclear",
							id: subfigure.id,
							x0: subfigure.x1,
							y0: subfigure.y1,
							x1: subfigure.x2,
							y1: subfigure.y2,
							label_x0: label?.x0,
							label_y0: label?.y0,
							label_x1: label?.x1,
							label_y1: label?.y1,
							subcaption: subfigure.caption,
						});
						// console.log(label);
					}

					this.figures_per_run.push(...Object.values(figures));
				}

				options.push(...this.figures_per_run.filter((obj) => obj.run_id === selected_run).map((obj) => Object.fromEntries([["label", obj.id], ["value", obj.id]])));
			}

			return [options];
		},

		update_available_figures: async function(options, current_figure){
			if(options.length === 0){
				return [options, null];
			}

			if(current_figure === undefined || current_figure === null){
				current_figure = options[0];
			} else if(!options.includes(current_figure)) {
				current_figure = null;
			}

			return [options, current_figure];
		},

		draw_annotation: function(x0, y0, x1, y1, color, height, label=true) {
			return {
				editable: true,
				line: {
					color: color,
					dash: label ? "dash" : "solid"
				},
				"x0": x0,
				"y0": -y0,
				"x1": x1,
				"y1": -y1
			}
		},

		/**
		 * A global object to keep track of the current annotations
		 */
		img_layout: null,

		update_current_figure: async function(image, training_data){
			const NULL_IMAGE = [[], training_data, {"data": [], "layout": []}, "", "", true];
			if(!image){
				return NULL_IMAGE;
			}

			let figure = training_data[image];
			let data;

			if(!figure) {
				figure = this.figures_per_run.filter((obj) => obj.id === image);

				if(figure.length === 0){
					console.error(`Could not find info for: ${image}.`);
					return NULL_IMAGE;
				}

				figure = figure[0];
				training_data[figure.id] = figure;
			}

			data = figure.subfigures.sort((a, b) => a.label.toUpperCase().localeCompare(b.label.toUpperCase()));

			const shapes = [];

			const img = new Image();
			img.onload = () => {
				const width = img.naturalWidth;
				const height = img.naturalHeight;

				for (const [_, subfigure] of figure.subfigures.entries()) {
					const color = dagFuncs.colorByLabel({value: subfigure.label}).backgroundColor;
					shapes.push(this.draw_annotation(subfigure.x0, subfigure.y0, subfigure.x1, subfigure.y1, color, height, false));
					shapes.push(this.draw_annotation(subfigure.label_x0, subfigure.label_y0, subfigure.label_x1, subfigure.label_y1, color, height, true));
				}

				// TODO: Add the draw annotation tool
				this.img_layout = {
					shapes: shapes,
					dragmode: "drawrect",
					autosize: true,
					xaxis: {
						// dtick: 100,
						// nticks: 20,
						range: [0, width],
						scaleanchor: "y",
						showticklabels: true,
						tickformat: "d",
						ticks: "outside",
						type: "linear",
						visible: true,
					},
					yaxis: {
						anchor: "x",
						// autorange: "reversed",
						// dtick: 100,
						// nticks: 20,
						range: [-height, 0],
						showticklabels: true,
						tickformat: "-d",
						ticks: "outside",
						type: "linear",
						visible: true,
					},
					images: [{
						source: figure.url,
						xref: "x",
						yref: "y",
						x: 0,
						y: 0,
						sizex: width,
						sizey: height,
						xanchor: "left",
						yanchor: "top",
						layer: "below"
					}],
					margin: {
						l: 50,
						r: 10,
						t: 10,
						b: 50
					},
					mode: "markers"
				};

				Plotly.newPlot("figure", [], this.img_layout);
				// TODO: Check if which function I want to us (https://plotly.com/javascript/plotlyjs-function-reference/#plotlynewplot)
				// TODO: Somewhat related, figure out how to have the edits connect back to the table's data when moving them (https://dash.plotly.com/annotations#modifying-shapes-and-parsing-relayoutdata)
			};

			img.src = figure.url;
			return [data, training_data, window.dash_clientside.no_update, figure.caption, figure.article_url, false];
		},

		update_coordinates: async function(coords, training_data, figure_id){
			const new_data = coords[0].data;
			// console.log(`Coords = ${coords[0]}`);

			const replacementRow = coords[0].rowIndex * 2;
			const color = dagFuncs.colorByLabel({ value: new_data.label }).backgroundColor;
			const height = this.img_layout.images[0].sizey;
			const column = coords[0].colId;

			if(column.includes("label")){
				const null_check = new Set([new_data.label_x0, new_data.label_y0, new_data.label_x1, new_data.label_y1]);
				if(!null_check.has(null) && !null_check.has(undefined)){
					this.img_layout.shapes[replacementRow+1] = this.draw_annotation(new_data.label_x0, new_data.label_y0, new_data.label_x1, new_data.label_y1, color, height, true);
				}
			} else if (column !== "subcaption"){
				const null_check = new Set([new_data.x0, new_data.y0, new_data.x1, new_data.y1]);
				if(!null_check.has(null) && !null_check.has(undefined)){
					this.img_layout.shapes[replacementRow] = this.draw_annotation(new_data.x0, new_data.y0, new_data.x1, new_data.y1, color, height, false);
				}
			}

			const get_label_index = training_data[figure_id]["subfigures"].map((element, index) => [index, element.label]).filter((element) => element[1] === new_data.label)[0];
			if(get_label_index === undefined){
				if(column === "label"){
					new_data["id"] = `${figure_id}-${coords[0].value}`;
				}
				training_data[figure_id]["subfigures"].push(new_data);
			} else{
				training_data[figure_id]["subfigures"][get_label_index[0]][column] = coords[0].value;
				if(column === "label"){
					training_data[figure_id]["subfigures"][get_label_index[0]]["id"] = `${figure_id}-${coords[0].value}`;
				}
			}

			return [Plotly.newPlot("figure", [], this.img_layout), training_data];
		},

		update_full_caption: function(caption, training_data, figure_id){
			if(!caption || typeof caption !== "string"){
				return window.dash_clientside.no_update;
			}

			training_data[figure_id]["caption"] = caption;

			return training_data;
		},

		download: function(n_clicks, training_data){
			if(!n_clicks){
				return window.dash_clientside.no_update;
			}

			const content = JSON.stringify(training_data, null, 2);

			const obj = {
				filename: "exsclaim_training_data.json",
				content: content,
				base64string: false
			};
			// console.log(content.length);

			return obj;
		},

		upload: function(contents) {
			const split_contents = contents.split(",");

			try{
				const decoded = atob(split_contents[1]);
				return JSON.parse(decoded);
			}
			catch(error){
				return window.dash_clientside.no_update;
			}
		}
	}
})