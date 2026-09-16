from exsclaim.api.dependencies.accept import Accept, AcceptDirective


async def test_accept_header_with_include_all():
	accept_string = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
	accept = Accept(accept_string)

	assert "text/html" in accept, "text/html should be an accepted media type"
	assert "text/xml" in accept, "text/xml should be an accepted media type because of */*"

	highest_weight, prime_directives = accept.get_highest_directives()
	assert highest_weight == 1.0, f"The default weight should be 1.0, which should be the highest in this case, not: {highest_weight}."

	prime_directives = set(prime_directives)
	for known_directive in ("text/html", "application/xhtml+xml"):
		assert known_directive in prime_directives, f"{known_directive} should be a prime directive."

	best_option, best_directive, weight = accept.get_best_option(("application/xml", "text/html", "*/*"))

	assert best_option == "text/html", "text/html should be chosen because it has the highest weight."
	assert best_directive == "text/html", "text/html was chosen, but the directive was incorrect."
	assert weight == 1.0, f"The weight should be 1.0, not: {weight}."


async def test_accept_header_without_include_all():
	accept_string = "text/html;q=0.1,application/xhtml+xml;q=0.4,application/xml;q=0.9,text/plain;q=0.95"
	accept = Accept(accept_string)

	assert "text/html" in accept, "text/html should be an accepted media type"
	assert "text/xml" not in accept, "text/xml should not be an accepted media type."

	highest_weight, _ = accept.get_highest_directives()
	assert highest_weight == 0.95, f"The default weight should be 0.95, which should be the highest in this case, not: {highest_weight}."

	best_option, best_directive, weight = accept.get_best_option(("application/xml", "text/html", "text/plain"))

	assert best_option == "text/plain", "text/html should be chosen because it has the highest weight."
	assert best_directive == "text/plain", "text/html was chosen, but the directive was incorrect."
	assert weight == 0.95, f"The weight should be 0.95, not: {weight}."


async def test_accept_header_with_all():
	accept_string = "*/*;q=0.1"
	accept = Accept(accept_string)

	assert "text/html" in accept, "text/html should be an accepted media type"
	assert "text/xml" in accept, "text/xml should be an accepted media type."
	assert "random/type" in accept, "random/type should be an accepted media type."

	options = ("some/type", "application/xml", "text/html", "text/plain")
	best_option, _, weight = accept.get_best_option(options)

	assert best_option == options[0], f"{options[0]} should have been chosen since it was the first seen of equally weighted options."
	assert weight == 0.1, f"The highest weight should be 0.1 because it's the only weight given, not {weight}."


def test_directive_properties():
	directive = AcceptDirective.from_string("*/*")

	for known_directive in ("text/plain", "image/png", "application/json", "application/xml"):
		assert known_directive in directive, f"*/* should accept anything, including {known_directive}."

	text_directive = AcceptDirective.from_string("text/*")

	assert text_directive in directive, "One family of types should be within all types."
	assert directive not in text_directive, "All types should not be contained within a specific family of types."

	for known_directive in ("text/plain", "text/html", "text/xml"):
		assert known_directive in text_directive, f"text/* should accept anything within the text type, including {known_directive}."

	for known_directive in ("application/pdf", "audio/mpeg", "video/mj2"):
		assert known_directive not in text_directive, f"text/* should not accept {known_directive}."

	specific_directive = AcceptDirective.from_string("text/plain")
	assert "text/plain" == specific_directive, "text/plain directive should be equal to 'text/plain' string."
	assert "text/plain" in specific_directive, "'text/plain directive' should be in text/plain directive."

	for known_directive in ("text/html", "text/xml", "application/pdf", "audio/mpeg", "video/mj2"):
		assert known_directive not in specific_directive, f"text/plain should not accept {known_directive}."

	assert text_directive not in specific_directive, "Contains should not say all subtypes are in one specific subtype."
