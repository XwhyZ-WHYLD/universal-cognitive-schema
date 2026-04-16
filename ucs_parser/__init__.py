"""
ucs-parser: Reference implementation for the Universal Cognitive Schema (v0.1.0)

Parses AI platform exports into UCS-compliant profiles.
"""

from .models import UCSProfile
from .parser import Parser
from .validator import Validator
from .fidelity import FidelityScorer
from .sanitiser import Sanitiser

__version__ = "0.1.0"
__all__ = ["Parser", "Validator", "FidelityScorer", "Sanitiser", "UCSProfile"]
