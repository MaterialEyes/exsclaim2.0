from exsclaim.version import Version


async def test_version_with_beta():
	version = Version("2.5.3b14")

	assert version.major == 2, f"Major version should be 2, not {version.major}."
	assert version.minor == 5, f"Minor version should be 5, not {version.minor}."
	assert version.patch == 3, f"Patch version should be 3, not {version.patch}."
	assert version.beta == 14, f"Beta version should be 14, not {version.beta}."

	assert version.is_beta, "Version should be in beta."


async def test_version_without_beta():
	version = Version("3.5.4")

	assert version.major == 3, f"Major version should be 3, not {version.major}."
	assert version.minor == 5, f"Minor version should be 5, not {version.minor}."
	assert version.patch == 4, f"Patch version should be 4, not {version.patch}."

	assert version.beta is None, "This version should not be in beta."
	assert not version.is_beta, "This version should not be in beta."


async def test_version_comparison():
	v0 = Version("2.5.3b1")
	v1 = Version("2.5.3b14")
	v2 = Version("2.5.3")
	v3 = Version("2.5.4b1")

	assert v0 < v1, "Beta versions should be comparable, and b1 should be less than b14."
	assert v1 < v2, "Beta versions should be less than the release version of the same patch."
	assert v2 < v3, "Beta versions of the next patch should be higher than the previous release."

	assert v3 > v2, "Beta versions of the next patch should be higher than the previous release."
	assert v2 > v1, "The release version of a given patch should be higher than the beta version of the same patch."
	assert v1 > v0, "A higher beta version of the same patch should be higher than a lower beta version of the same patch."

	for v in (v0, v1, v2, v3):
		assert v == v, "Versions should be equal if all aspects are the same."

	assert v0 <= v1
	assert v1 >= v0
