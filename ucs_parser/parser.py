"""
Parser: transforms AI platform data exports into UCS-compliant profiles.

v0.1.0 supports: ChatGPT (conversations.json export)
Planned (v0.2.0): Claude export, Gemini export
"""

from __future__ import annotations

import json
import re
import uuid
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .fidelity import FidelityReport, FidelityScorer
from .models import (
    CommunicationStyle,
    ExpertiseDomain,
    ExpertiseDepth,
    ExpertiseMap,
    InteractionPatterns,
    LanguagePreferences,
    OutputFormat,
    Persona,
    PreferenceCorpus,
    ProjectGraph,
    ResponseLength,
    TemporalContext,
    TypicalPromptStyle,
    UCSProfile,
    Provenance,
    ExtractionMethod,
)
from .sanitiser import Sanitiser
from .validator import Validator


# ---------------------------------------------------------------------------
# Signals used for heuristic inference
# ---------------------------------------------------------------------------

# Rejected-behaviour signal phrases (user corrections)
_CORRECTION_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"don.t\s+(use|start\s+with)\s+bullet", re.I),    "Avoids bullet-point responses"),
    (re.compile(r"don.t\s+start\s+with.{1,40}(certainly|great\s+question|sure)", re.I),
                                                                    "Dislikes filler opener phrases"),
    (re.compile(r"(?:too\s+long|be\s+(?:more\s+)?concis)", re.I), "Prefers concise responses"),
    (re.compile(r"(?:too\s+short|more\s+detail|expand)", re.I),   "Wants detailed responses"),
    (re.compile(r"lead\s+with\s+the\s+(?:main|key|answer)", re.I),"Prefers answer-first structure"),
    (re.compile(r"don.t\s+hedge|stop\s+hedging", re.I),           "Dislikes excessive hedging"),
    (re.compile(r"just\s+answer\s+directly", re.I),               "Prefers direct answers without preamble"),
    (re.compile(r"prose\s+(?:please|not\s+bullets)", re.I),       "Prefers prose over bullets"),
    (re.compile(r"don.t\s+repeat\s+(?:yourself|the\s+question)", re.I),
                                                                    "Dislikes repetition"),
]

_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "Software engineering":  ["code", "function", "api", "backend", "database", "algorithm", "debug"],
    "Machine learning":      ["model", "training", "dataset", "neural", "classifier", "sklearn", "pytorch", "tensorflow"],
    "Product management":    ["roadmap", "sprint", "stakeholder", "user story", "priorit", "product"],
    "Data engineering":      ["pipeline", "etl", "spark", "dbt", "warehouse", "ingestion"],
    "DevOps":                ["docker", "kubernetes", "ci/cd", "deploy", "terraform", "helm"],
    "TypeScript / JavaScript":["typescript", "javascript", "react", "node", "npm", "webpack"],
    "Python":                ["python", "pip", "pandas", "numpy", "fastapi", "flask", "django"],
    "Go":                    ["golang", "goroutine", "gin", "grpc"],
    "Writing / communication":["draft", "email", "essay", "blog", "proofread", "rewrite"],
    "Strategy / business":   ["strategy", "market", "competitor", "revenue", "growth", "fundrais"],
    "Legal":                 ["contract", "gdpr", "compliance", "liability", "clause", "agreement"],
    "Finance":               ["financial", "valuation", "cash flow", "balance sheet", "p&l", "ipo"],
    "Security":              ["vulnerability", "exploit", "penetration", "owasp", "auth", "token"],
}

_FORMAT_SIGNALS: dict[str, list[str]] = {
    "bullets":    ["bullet", "list it", "bullet point"],
    "structured": ["table", "structured", "section", "header"],
    "prose":      ["prose", "paragraph", "write it out", "no bullets"],
}


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class Parser:
    """
    Transforms AI platform data exports into UCS-compliant profiles.

    Usage:
        parser = Parser(source="chatgpt")
        profile = parser.from_file("chatgpt_export.zip")  # or .json
        profile.to_json("my_profile.ucs.json")
        profile.validate()
        print(profile.fidelity_report())
    """

    SUPPORTED_SOURCES = ("chatgpt",)

    def __init__(self, source: str = "chatgpt") -> None:
        if source not in self.SUPPORTED_SOURCES:
            raise ValueError(
                f"Unsupported source '{source}'. "
                f"Supported: {self.SUPPORTED_SOURCES}. "
                "Claude and Gemini parsers are planned for v0.2.0."
            )
        self.source = source
        self._sanitiser = Sanitiser()
        self._validator  = Validator()
        self._fidelity   = FidelityScorer()
        self._profile: UCSProfile | None = None
        self._fidelity_report: FidelityReport | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def from_file(self, path: str) -> "ParsedProfile":
        """
        Parse a ChatGPT data export (.zip or conversations.json).
        Returns a ParsedProfile with validate() and fidelity_report() methods.
        """
        conversations = self._load_conversations(path)
        return self._parse_chatgpt(conversations)

    def from_dict(self, conversations: list[dict[str, Any]]) -> "ParsedProfile":
        """Parse from an already-loaded list of conversation dicts."""
        return self._parse_chatgpt(conversations)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load_conversations(self, path: str) -> list[dict[str, Any]]:
        p = Path(path)

        if p.suffix not in (".zip", ".json"):
            raise ValueError(f"Unsupported file type '{p.suffix}'. Expected .zip or .json.")

        if not p.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if p.suffix == ".zip":
            return self._load_from_zip(p)
        else:
            with open(p, encoding="utf-8") as f:
                return json.load(f)

    def _load_from_zip(self, path: Path) -> list[dict[str, Any]]:
        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()
            target = next(
                (n for n in names if n.endswith("conversations.json")),
                None
            )
            if not target:
                raise ValueError(
                    "Could not find 'conversations.json' in the zip archive. "
                    "Ensure this is a standard ChatGPT data export."
                )
            with zf.open(target) as f:
                return json.load(f)

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_chatgpt(self, conversations: list[dict[str, Any]]) -> "ParsedProfile":
        messages        = self._extract_messages(conversations)
        user_messages   = [m for m in messages if m["role"] == "user"]
        assist_messages = [m for m in messages if m["role"] == "assistant"]
        n               = len(messages)

        persona              = self._infer_persona(user_messages)
        expertise_map        = self._infer_expertise(user_messages)
        preference_corpus    = self._infer_preferences(user_messages)
        interaction_patterns = self._infer_patterns(user_messages)
        temporal_context     = self._infer_temporal(conversations, user_messages)

        now = datetime.now(timezone.utc)
        raw_profile = UCSProfile(
            profile_id=uuid.uuid4(),
            created_at=now,
            updated_at=now,
            persona=persona,
            expertise_map=expertise_map,
            project_graph=ProjectGraph(),
            preference_corpus=preference_corpus,
            interaction_patterns=interaction_patterns,
            temporal_context=temporal_context,
            provenance=Provenance(
                source_platforms=["chatgpt"],
                extraction_method=ExtractionMethod.export,
                sanitised=False,
                sanitised_at=None,
                attestation_signature=None,
            ),
        )

        # Sanitise
        raw_dict = raw_profile.to_dict()
        sanitised_dict, redactions = self._sanitiser.sanitise_profile(raw_dict)
        sanitised_dict["provenance"]["sanitised"] = True
        sanitised_dict["provenance"]["sanitised_at"] = now.isoformat()

        # Fidelity
        fidelity_report = self._fidelity.score(sanitised_dict, interaction_count=n)
        sanitised_dict["fidelity"] = fidelity_report.to_dict()

        profile = UCSProfile.model_validate(sanitised_dict)
        return ParsedProfile(profile, fidelity_report, redactions, self._validator)

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    def _extract_messages(self, conversations: list[dict]) -> list[dict[str, Any]]:
        messages = []
        for conv in conversations:
            mapping = conv.get("mapping", {})
            for node in mapping.values():
                msg = node.get("message")
                if not msg:
                    continue
                role = msg.get("author", {}).get("role")
                if role not in ("user", "assistant"):
                    continue
                parts = msg.get("content", {}).get("parts", [])
                text = " ".join(str(p) for p in parts if isinstance(p, str)).strip()
                if not text:
                    continue
                messages.append({
                    "role": role,
                    "text": text,
                    "created_at": msg.get("create_time"),
                })
        return messages

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def _infer_persona(self, user_msgs: list[dict]) -> Persona:
        if not user_msgs:
            return Persona()

        texts = [m["text"] for m in user_msgs]
        all_text = " ".join(texts).lower()
        avg_len = sum(len(t) for t in texts) / len(texts)

        # Communication style heuristics
        question_ratio = sum(1 for t in texts if "?" in t) / len(texts)
        list_ratio     = sum(1 for t in texts if re.search(r"\n[-*]|\d+\.", t)) / len(texts)
        please_ratio   = sum(1 for t in texts if re.search(r"\bplease\b", t, re.I)) / len(texts)

        direct        = max(0.0, 0.6 - question_ratio * 0.4 - please_ratio * 0.2)
        collaborative = min(1.0, please_ratio * 0.8 + 0.1)
        socratic      = min(1.0, question_ratio * 0.7)
        narrative     = min(1.0, list_ratio * 0.3)

        total = direct + collaborative + socratic + narrative
        if total > 0:
            direct        /= total
            collaborative /= total
            socratic      /= total
            narrative     /= total
        else:
            direct = 1.0

        formality = min(1.0, max(0.0,
            0.5
            + (0.2 if re.search(r"\bkindly\b|\bhereby\b|\bregarding\b", all_text) else 0)
            - (0.2 if re.search(r"\bgonna\b|\bwanna\b|\bdunno\b|\blol\b", all_text) else 0)
        ))
        verbosity = min(1.0, avg_len / 500)

        tone_markers: list[str] = []
        if re.search(r"\bwhy\b.*\?", all_text): tone_markers.append("curious / questioning")
        if re.search(r"\bexactly\b|\bprecisely\b", all_text): tone_markers.append("precise")
        if re.search(r"\bironically\b|\bto\s+be\s+fair\b", all_text): tone_markers.append("nuanced")
        if question_ratio > 0.6: tone_markers.append("interrogative")
        if avg_len < 80: tone_markers.append("terse")
        if avg_len > 300: tone_markers.append("detailed prompts")

        return Persona(
            communication_style=CommunicationStyle(
                direct=round(direct, 2),
                collaborative=round(collaborative, 2),
                socratic=round(socratic, 2),
                narrative=round(narrative, 2),
            ),
            formality=round(formality, 2),
            verbosity=round(verbosity, 2),
            tone_markers=tone_markers[:5],
            language_preferences=LanguagePreferences(primary="en"),
        )

    def _infer_expertise(self, user_msgs: list[dict]) -> ExpertiseMap:
        all_text = " ".join(m["text"] for m in user_msgs).lower()
        domain_hits: dict[str, int] = {}

        for domain, keywords in _DOMAIN_KEYWORDS.items():
            count = sum(all_text.count(kw) for kw in keywords)
            if count > 0:
                domain_hits[domain] = count

        if not domain_hits:
            return ExpertiseMap(domains=[])

        max_hits = max(domain_hits.values())
        domains: list[ExpertiseDomain] = []

        for domain, hits in sorted(domain_hits.items(), key=lambda x: -x[1])[:10]:
            ratio = hits / max_hits
            if ratio >= 0.6:
                depth = ExpertiseDepth.expert
            elif ratio >= 0.3:
                depth = ExpertiseDepth.proficient
            elif ratio >= 0.1:
                depth = ExpertiseDepth.functional
            else:
                depth = ExpertiseDepth.aware

            domains.append(ExpertiseDomain(name=domain, depth=depth))

        return ExpertiseMap(domains=domains)

    def _infer_preferences(self, user_msgs: list[dict]) -> PreferenceCorpus:
        all_text = " ".join(m["text"] for m in user_msgs).lower()

        format_votes: Counter = Counter()
        for fmt, signals in _FORMAT_SIGNALS.items():
            for sig in signals:
                if sig in all_text:
                    format_votes[fmt] += 1

        output_format = None
        if format_votes:
            top = format_votes.most_common(1)[0][0]
            output_format = OutputFormat(top)

        # Length preference
        concise_signals = ["concise", "brief", "short answer", "just the", "tldr"]
        thorough_signals = ["in detail", "comprehensive", "exhaustive", "full explanation", "walk me through"]
        concise_score  = sum(1 for s in concise_signals if s in all_text)
        thorough_score = sum(1 for s in thorough_signals if s in all_text)

        if thorough_score > concise_score:
            response_length = ResponseLength.thorough
        elif concise_score > thorough_score:
            response_length = ResponseLength.concise
        else:
            response_length = ResponseLength.moderate

        # Code language preferences
        lang_scores: Counter = Counter()
        for lang, kws in _DOMAIN_KEYWORDS.items():
            if any(lang.lower() in kw.lower() or kw.lower() in lang.lower() for kw in kws):
                for kw in kws:
                    lang_scores[lang] += all_text.count(kw)
        code_langs = [lang for lang, _ in lang_scores.most_common(4) if lang_scores[lang] > 0]

        return PreferenceCorpus(
            output_format=output_format,
            response_length=response_length,
            code_language_preferences=code_langs,
        )

    def _infer_patterns(self, user_msgs: list[dict]) -> InteractionPatterns:
        corrections: list[str] = []
        for pattern, label in _CORRECTION_PATTERNS:
            if any(pattern.search(m["text"]) for m in user_msgs):
                corrections.append(label)

        texts = [m["text"] for m in user_msgs]
        if not texts:
            return InteractionPatterns()

        avg_len = sum(len(t) for t in texts) / len(texts)
        question_ratio = sum(1 for t in texts if "?" in t) / len(texts)
        has_preamble = sum(
            1 for t in texts
            if re.match(r"^(i\s+am|i'm|we\s+are|context:|background:)", t.strip(), re.I)
        ) / len(texts)

        if has_preamble > 0.3:
            opener = "context-then-ask"
        elif question_ratio > 0.7:
            opener = "question"
        else:
            opener = "command"

        from .models import PromptLength, PromptStructure
        length = (PromptLength.short if avg_len < 80
                  else PromptLength.long if avg_len > 250
                  else PromptLength.medium)

        bullet_ratio = sum(1 for t in texts if re.search(r"\n[-*]|\d+\.", t)) / len(texts)
        structure = (PromptStructure.bulleted if bullet_ratio > 0.3
                     else PromptStructure.multi_paragraph if avg_len > 200
                     else PromptStructure.single_line)

        return InteractionPatterns(
            typical_prompt_style=TypicalPromptStyle(
                opener=opener,
                structure=structure,
                avg_length=length,
            ),
            common_corrections=corrections,
        )

    def _infer_temporal(
        self,
        conversations: list[dict],
        user_msgs: list[dict],
    ) -> TemporalContext:
        timestamps = [
            m["created_at"] for m in user_msgs
            if m.get("created_at") is not None
        ]

        if not timestamps:
            return TemporalContext(recency_weight=0.7)

        min_ts = min(timestamps)
        max_ts = max(timestamps)

        from_dt = datetime.fromtimestamp(min_ts, tz=timezone.utc)
        to_dt   = datetime.fromtimestamp(max_ts, tz=timezone.utc)

        from .models import LifeChapter
        chapter = LifeChapter(**{
            "from": from_dt,
            "to": None,
            "label": f"AI usage period ({from_dt.strftime('%Y-%m')} – present)",
            "active": True,
            "notes": (
                f"Inferred from {len(user_msgs):,} user messages across "
                f"{len(conversations)} conversation(s) spanning "
                f"{from_dt.strftime('%b %Y')} to {to_dt.strftime('%b %Y')}."
            ),
        })

        return TemporalContext(
            recency_weight=0.7,
            life_chapters=[chapter],
        )


# ---------------------------------------------------------------------------
# ParsedProfile — the object returned from parser.from_file()
# ---------------------------------------------------------------------------

class ParsedProfile:
    """
    Wraps a parsed UCSProfile with validation and fidelity reporting.
    This is the object you interact with after parsing.
    """

    def __init__(
        self,
        profile: UCSProfile,
        fidelity: FidelityReport,
        redactions: list[str],
        validator: Validator,
    ) -> None:
        self._profile    = profile
        self._fidelity   = fidelity
        self._redactions = redactions
        self._validator  = validator

    def to_json(self, path: str, indent: int = 2) -> None:
        """Write the UCS profile to a .ucs.json file."""
        self._profile.to_json(path, indent=indent)
        print(f"Profile written to {path}")

    def to_dict(self) -> dict[str, Any]:
        return self._profile.to_dict()

    def validate(self) -> bool:
        """Validate against the UCS JSON Schema. Prints a report. Returns True if valid."""
        result = self._validator.validate(self._profile.to_dict())
        if result.valid:
            print("✓ Profile is valid against UCS v0.1.0 schema.")
        else:
            print(f"✗ Profile has {len(result.errors)} validation error(s):")
            for err in result.errors:
                print(f"  - {err}")
        return result.valid

    def fidelity_report(self) -> str:
        """Return a human-readable fidelity report."""
        lines = [self._fidelity.summary()]
        if self._redactions:
            lines.append(f"\n⚠ Sanitiser removed/flagged {len(self._redactions)} item(s):")
            for r in self._redactions[:10]:
                lines.append(f"  - {r}")
        return "\n".join(lines)

    @property
    def profile(self) -> UCSProfile:
        return self._profile
