from os import getenv
from typing import Literal

import exsclaim.llms as llms
import pytest
import random
import warnings


YieldType = tuple[str, int, list[llms.CaptionEntry]]


@pytest.fixture
def caption_info() -> YieldType:
	# Figure 1 caption from https://www.nature.com/articles/s41467-025-65314-w.html

	caption_pairs: list[YieldType] = [
		(
			"<b>a</b> The on-site oxygen 2<i>p</i> two-hole state is prepared and detected via coincidences of oxygen 1<i>s</i> (K-shell) ionization and the oxygen <i>KVV</i> Auger decay. LHB and UHB denote lower and upper Hubbard band, respectively. <b>b</b> Structure and surface termination of tetragonal La<sub>2</sub>CuO<sub>4</sub>: Octahedral coordination (blue polygons) of Copper atoms (grey) to six lattice oxygen atoms O<sub>latt.</sub> (red). The surface layer (right hand side) contains under-coordinated surface oxygen species O<sub>ad.</sub> (light orange). <b>c</b> Oxygen 1<i>s</i>/ <i>KVV</i> coincidence map of La<sub>2</sub>CuO<sub>4</sub> with distinctly separated lattice oxygen O<sub>latt.</sub> and surface oxygen O<sub>ad.</sub> on-site oxygen 2<i>p</i> two-hole state spectral contributions. Color bar shows counts. <b>d</b> Coincidence Auger electron spectra of O<sub>latt.</sub> (red) and O<sub>ad.</sub> (light orange) obtained by integrating the map in <b>c</b> over the respective photoelectron binding energy ranges marked with vertical bars in the same color. Source data are provided as a Source Data file.",
			4,
			[
				llms.CaptionEntry(label="a", caption="The on-site oxygen 2<i>p</i> two-hole state is prepared and detected via coincidences of oxygen 1<i>s</i> (K-shell) ionization and the oxygen <i>KVV</i> Auger decay. LHB and UHB denote lower and upper Hubbard band, respectively."),
				llms.CaptionEntry(label="b", caption="Structure and surface termination of tetragonal La<sub>2</sub>CuO<sub>4</sub>: Octahedral coordination (blue polygons) of Copper atoms (grey) to six lattice oxygen atoms O<sub>latt.</sub> (red). The surface layer (right hand side) contains under-coordinated surface oxygen species O<sub>ad.</sub> (light orange)."),
				llms.CaptionEntry(label="c", caption="Oxygen 1<i>s</i>/ <i>KVV</i> coincidence map of La<sub>2</sub>CuO<sub>4</sub> with distinctly separated lattice oxygen O<sub>latt.</sub> and surface oxygen O<sub>ad.</sub> on-site oxygen 2<i>p</i> two-hole state spectral contributions. Color bar shows counts."),
				llms.CaptionEntry(label="d", caption="Coincidence Auger electron spectra of O<sub>latt.</sub> (red) and O<sub>ad.</sub> (light orange) obtained by integrating the map in <b>c</b> over the respective photoelectron binding energy ranges marked with vertical bars in the same color."),
			]
		),
	]

	return random.choice(caption_pairs)


def token_usage_is_okay(tokens: int | None) -> bool:
	if tokens is None:
		return True # Some services don't currently record token stats
	return tokens > 0


def check_condition(condition: bool, failure_message: str, on_error: Literal["fail", "warn"] = "warn"):
	if condition:
		return

	if on_error == "fail":
		raise AssertionError(failure_message)
	elif on_error == "warn":
		warnings.warn(failure_message)


async def run_llm_test(llm: llms.LLM, caption_info: YieldType):
	name = llm.__class__.__name__
	raw_caption, num_captions, captions_list = caption_info
	captions, keywords, usage = await llm.parse_captions(raw_caption)

	# Syntax tests to ensure that the LLM can connect to the respective service properly
	assert len(captions) > 0, f"No captions returned for {name}."
	assert 0 < len(keywords) <= 5, f"An improper number of keywords was returned: {len(keywords):,} for {name}."
	assert token_usage_is_okay(usage.input_tokens), f"{name} reported no input tokens were used."
	assert token_usage_is_okay(usage.output_tokens), f"{name} reported no output tokens were given."

	# More rigorous tests about the output from the LLM
	check_condition(len(captions) == num_captions, f"{name} should have returned {num_captions:,} captions, but {len(captions):,} were found.")

	known_labels = {caption.label for caption in captions_list}
	found_labels = set(captions.keys())
	check_condition(known_labels == found_labels, f"{name} did not find the proper labels, the difference was {known_labels.symmetric_difference(found_labels)}.")

	# TODO: Come up with tests for the generated captions, maybe ROUGE-L, and if the value is below a threshold, the test failed


async def test_anthropic(caption_info: YieldType):
	api_key = getenv("ANTHROPIC_API_KEY")
	if api_key is None:
		pytest.skip("ANTHROPIC_API_KEY not set.")

	if not hasattr(llms, "Anthropic"):
		pytest.skip("anthropic library is not installed.")

	llm = llms.Anthropic("claude-sonnet-5", api_key=api_key)
	await run_llm_test(llm, caption_info)


async def test_google(caption_info: YieldType):
	api_key = getenv("GEMINI_API_KEY")
	if api_key is None:
		pytest.skip("GEMINI_API_KEY not set.")

	if not hasattr(llms, "Google"):
		pytest.skip("google-genai library is not installed.")

	llm = llms.Google("gemini-3.1-flash-lite", api_key=api_key)
	await run_llm_test(llm, caption_info)


async def test_openai(caption_info: YieldType):
	api_key = getenv("OPENAI_API_KEY")
	if api_key is None:
		pytest.skip("OPENAI_API_KEY not set.")

	if not hasattr(llms, "OpenAI"):
		pytest.skip("openai library is not installed.")

	llm = llms.OpenAI("gpt-5.2", api_key=api_key)
	await run_llm_test(llm, caption_info)
