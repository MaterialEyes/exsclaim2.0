from typing import Literal

__all__ = ["JournalFamily", "JournalFamilyStatic", "JournalFamilyDynamic", "JournalHtml", "StaticHtml", "DynamicHtml",
		   "JournalMeta", "ACS", "Nature", "RSC", "Wiley", "COMPATIBLE_JOURNALS"]

from .base import JournalFamily, JournalFamilyStatic, JournalFamilyDynamic, JournalHtml, StaticHtml, DynamicHtml, \
	JournalMeta
from .acs import ACS
from .nature import Nature
from .rsc import RSC
from .wiley import Wiley

COMPATIBLE_JOURNALS = Literal["ACS", "Nature", "RSC", "Wiley"]
