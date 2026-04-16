"""
Sanitiser: strips prompt-injection patterns, executable instructions,
and role-override syntax from UCS profile content.

Per the UCS spec, every profile passing through a compliant tool must
be sanitised. The sanitisation_attestation field in provenance records this.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Threat patterns
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS: list[re.Pattern] = [
    # Role override attempts
    re.compile(r"\bignore\s+(all\s+)?previous\s+instructions?\b", re.I),
    re.compile(r"\bdisregard\s+(all\s+)?prior\s+instructions?\b", re.I),
    re.compile(r"\byou\s+are\s+now\s+(?:a|an|the)\b", re.I),
    re.compile(r"\bact\s+as\s+(?:a|an|the)\s+(?:different|new|unrestricted)\b", re.I),
    re.compile(r"\bpretend\s+(?:you\s+are|to\s+be)\b", re.I),
    re.compile(r"\bjailbreak\b", re.I),
    re.compile(r"\bdan\s+mode\b", re.I),
    # System-prompt injection markers
    re.compile(r"<\s*/?system\s*>", re.I),
    re.compile(r"\[INST\]|\[/INST\]"),
    re.compile(r"#{3,}\s*system", re.I),
    # Executable instruction patterns
    re.compile(r"\balways\s+trust\s+this\s+(artifact|profile|document)\b", re.I),
    re.compile(r"\boverride\s+(safety|guardrails?|restrictions?|policies?)\b", re.I),
    re.compile(r"\bbypass\s+(safety|filter|restriction)\b", re.I),
    # Suspicious formatting that may indicate injected context
    re.compile(r"```\s*(?:system|prompt|instruction)", re.I),
]

_SUSPICIOUS_PHRASES: list[re.Pattern] = [
    re.compile(r"\bdo\s+not\s+(?:reveal|disclose|share)\s+(?:this|your)\s+(?:prompt|instruction|system)", re.I),
    re.compile(r"\bkeep\s+this\s+(?:secret|hidden|confidential)\b", re.I),
    re.compile(r"\btrust\s+me[,\.]?\s+i\s+am\b", re.I),
]


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class SanitisationResult:
    clean:      bool
    warnings:   list[str] = field(default_factory=list)
    redactions: list[str] = field(default_factory=list)
    sanitised_value: Any = None


# ---------------------------------------------------------------------------
# Sanitiser
# ---------------------------------------------------------------------------

class Sanitiser:
    """
    Scans and cleans string values within a UCS profile dict.
    Returns a sanitised copy of the data and a report of what was changed.
    """

    def sanitise_profile(self, data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        """
        Returns (sanitised_data, list_of_redaction_notes).
        """
        redactions: list[str] = []
        sanitised = self._walk(data, path="root", redactions=redactions)
        return sanitised, redactions

    def sanitise_string(self, value: str) -> SanitisationResult:
        warnings:   list[str] = []
        redactions: list[str] = []
        result = value

        for pattern in _INJECTION_PATTERNS:
            match = pattern.search(result)
            if match:
                note = f"Injection pattern removed: '{match.group()}'"
                redactions.append(note)
                result = pattern.sub("[REDACTED]", result)

        for pattern in _SUSPICIOUS_PHRASES:
            match = pattern.search(result)
            if match:
                note = f"Suspicious phrase flagged: '{match.group()}'"
                warnings.append(note)
                result = pattern.sub("[FLAGGED]", result)

        return SanitisationResult(
            clean=len(redactions) == 0 and len(warnings) == 0,
            warnings=warnings,
            redactions=redactions,
            sanitised_value=result,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _walk(self, node: Any, path: str, redactions: list[str]) -> Any:
        if isinstance(node, str):
            result = self.sanitise_string(node)
            if not result.clean:
                for note in result.redactions + result.warnings:
                    redactions.append(f"[{path}] {note}")
            return result.sanitised_value

        if isinstance(node, dict):
            return {k: self._walk(v, f"{path}.{k}", redactions) for k, v in node.items()}

        if isinstance(node, list):
            return [self._walk(item, f"{path}[{i}]", redactions) for i, item in enumerate(node)]

        return node
