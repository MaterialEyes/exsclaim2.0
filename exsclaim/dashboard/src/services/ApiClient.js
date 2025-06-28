// some functions to get data from the API

export const fetchStatus = async (baseUrl, id) => {
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
export const fetchArticles = async (baseUrl, id) => {
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

export const fetchArticle = async (baseUrl, id) => {
	return fetch(`${baseUrl}/results/v1/articles/${id}`, {
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
 * @param num The page number (DEPRECATED).
 * @returns {Promise<any>}
 */
export const fetchFigures = async (baseUrl, id, num) => {
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
 * @param num The page number (DEPRECATED).
 * @returns {Promise<any>}
 */
export const fetchSubFigures = async (baseUrl, id, num) => {
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
