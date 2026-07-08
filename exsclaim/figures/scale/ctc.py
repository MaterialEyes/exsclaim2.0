# Source:
#  https://github.com/githubharald/CTCDecoder/blob/master/src/BeamSearch.py
from __future__ import division, print_function

from .lm import LanguageModel

from pathlib import Path
from typing import Optional

import logging
import torch


__all__ = ["BeamEntry", "BeamState", "applyLM", "addBeam", "ctcBeamSearch", "postprocess_ctc", "run_ctc"]


class BeamEntry:
    """Information about one single beam at a specific time-step"""
    def __init__(self):
        self._prNonBlank = 0
        self._prBlank = 0
        self.prText = 1  # LM score
        self.lmApplied = False  # flag if LM was already applied to this beam
        self.labeling = ()

    @property
    def prTotal(self):
        """blank and non-blank"""
        return self._prNonBlank + self._prBlank

    @property
    def prNonBlank(self) -> int:
        """non-blank"""
        return self._prNonBlank

    @prNonBlank.setter
    def prNonBlank(self, prNonBlank: int):
        self._prNonBlank = prNonBlank

    @property
    def prBlank(self) -> int:
        """blank"""
        return self._prBlank

    @prBlank.setter
    def prBlank(self, prBlank: int):
        self._prBlank = prBlank

    @property
    def labeling(self) -> tuple:
        """Beam-labeling"""
        return self._labeling

    @labeling.setter
    def labeling(self, labeling: tuple):
        self._labeling = labeling


class BeamState:
    """Information about the beams at specific time-step."""
    def __init__(self):
        self.entries = {}

    def norm(self):
        """length-normalize LM score"""
        for k, _ in self.entries.items():
            labelingLen = len(self.entries[k].labeling)
            self.entries[k].prText = self.entries[k].prText ** (
                1.0 / (labelingLen if labelingLen else 1.0)
            )

    def sort(self):
        """return beam-labelings, sorted by probability"""
        beams = list(self.entries.values())
        sortedBeams = sorted(beams, reverse=True, key=lambda x: x.prTotal * x.prText)
        return [(x.labeling, x.prTotal * x.prText) for x in sortedBeams]


def applyLM(parentBeam, childBeam, classes, lm):
    """Get LM score of child beam"""
    if not (lm and not childBeam.lmApplied):
        return

    # first char
    c1 = classes[parentBeam.labeling[-1] if parentBeam.labeling else classes.index(" ")]
    # second char
    c2 = classes[childBeam.labeling[-1]]
    # influence of the language model
    lmFactor = 0.01
    # probability of seeing first and second char next to each other
    bigramProb = lm.getCharBigram(c1, c2) ** lmFactor
    # probability of the character sequence
    childBeam.prText = parentBeam.prText * bigramProb
    # only apply LM once per beam entry
    childBeam.lmApplied = True


def addBeam(beamState: BeamState, labeling):
    """add beam if it does not yet exist"""
    if labeling not in beamState.entries:
        beamState.entries[labeling] = BeamEntry()


def ctcBeamSearch(mat: torch.Tensor, classes: str, lm: LanguageModel, beamWidth=25):
    """beam search as described by Hwang et al. and Graves et al."""

    blankIdx = len(classes)
    maxT, maxC = mat.shape

    # initialize beam state
    last = BeamState()
    labeling = ()
    last.entries[labeling] = BeamEntry()
    last.entries[labeling].prBlank = 1

    # go over all time-steps
    for t in range(maxT):
        curr = BeamState()

        # get beam-labelings of best beams
        bestLabelings = last.sort()[0:beamWidth]

        # go over best beams
        for labeling, conf in bestLabelings:

            # probability of paths ending with a non-blank
            prNonBlank = 0
            # in case of non-empty beam
            if labeling:
                # probability of paths with repeated last char at the end
                prNonBlank = last.entries[labeling].prNonBlank * mat[t, labeling[-1]]

            # probability of paths ending with a blank
            prBlank = (last.entries[labeling].prTotal) * mat[t, blankIdx]

            # add beam at current time-step if needed
            addBeam(curr, labeling)

            # fill in data
            curr.entries[labeling].labeling = labeling
            curr.entries[labeling].prNonBlank += prNonBlank
            curr.entries[labeling].prBlank += prBlank
            # beam-labeling not changed, therefore also LM score unchanged
            curr.entries[labeling].prText = last.entries[labeling].prText
            # LM already applied at previous time-step for this beam-labeling
            curr.entries[labeling].lmApplied = True

            # extend current beam-labeling
            for c in range(maxC - 1):
                # add new char to current beam-labeling
                newLabeling = labeling + (c,)

                # if new labeling contains duplicate char at the end,
                # only consider paths ending with a blank
                if labeling and labeling[-1] == c:
                    prNonBlank = mat[t, c] * last.entries[labeling].prBlank
                else:
                    prNonBlank = mat[t, c] * last.entries[labeling].prTotal

                # add beam at current time-step if needed
                addBeam(curr, newLabeling)

                # fill in data
                curr.entries[newLabeling].labeling = newLabeling
                curr.entries[newLabeling].prNonBlank += prNonBlank

                # apply LM
                applyLM(curr.entries[labeling], curr.entries[newLabeling], classes, lm)

        # set new beam state
        last = curr

    # normalize LM scores according to beam-labeling-length
    last.norm()

    #  # sort by probability
    # bestLabeling = last.sort()[0] # get most probable labeling

    # # map labels to chars
    # res = ''
    # for l in bestLabeling[0]:
    #     res += classes[l]

    return last.sort()[:10]


# Added by MaterialEyes


def postprocess_ctc(results: torch.Tensor, logger: Optional[logging.Logger] = None) -> tuple[float, str, float]:
    classes = "0123456789mMcCuUnN .A"
    idx_to_class = classes + "-"
    for result, confidence in results:
        confidence = confidence.detach().item()

        word = "".join(map(lambda step: idx_to_class[step], result)).strip().replace('-', '')
        try:
            number, unit = word.split()
            number = float(number)
            lower_unit = unit.lower()
        except ValueError as e:
            if logger is not None:
                logger.exception(f"An error occurred while trying to split \"{word}\"", exc_info=e)
            continue

        if lower_unit in {"n", "c", "u"}:
            unit = f"{lower_unit}m"

        if lower_unit in {"nm", "mm", "cm", "um", "a"}:
            return number, unit, confidence
    return -1, "m", 0


def run_ctc(probs: torch.Tensor, classes: str, logger: Optional[logging.Logger] = None) -> tuple[float, str, float]:
    current_file = Path(__file__).resolve(strict=True)
    language_model_file = "corpus.txt"
    language_model = LanguageModel(current_file.parent / language_model_file, classes)
    top_results = ctcBeamSearch(probs, classes, lm=language_model, beamWidth=15)
    return postprocess_ctc(top_results, logger)
