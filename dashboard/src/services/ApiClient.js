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

export const fetchArticles = async (baseUrl) => {
	return fetch(`${baseUrl}/articles`, {
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
	return fetch(`${baseUrl}/articles/${id}`, {
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

export const fetchFigures = async (baseUrl, num) => {
	return fetch(`${baseUrl}/figures/?page=${num}`, {
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

export const fetchSubFigures = async (baseUrl, num) => {
	return fetch(`${baseUrl}/subfigures/?page=${num}`, {
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
