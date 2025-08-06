function updateBannerNumber(number=undefined){
	const banner = document.getElementById("figure-results-header");

	if(number === undefined){
		banner.innerText = "Figure Results";
	} else {
		banner.innerText = `Figure Results: ${number}`;
	}

	return banner.innerText;
}