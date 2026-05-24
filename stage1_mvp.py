#!/usr/bin/env python3
"""
stage1_mvp.py – UCS Stage 1 First Echo MVP
Loads a UCS cognitive profile (ucs.schema.json v0.1.0), builds a
constraint-driven prompt, sends it to two model adapters, validates
responses, and presents results.

Usage:
  python stage1_mvp.py --profile path/to/profile.json --question "Your question"
  python stage1_mvp.py --profile path/to/profile.json  # interactive mode
"""

import json
import argparse
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime


# ─────────────────────────────────────────────
# 1. Profile Loading & Validation
# ─────────────────────────────────────────────

def load_profile(path: str) -> dict:
    """
    Load and validate a UCS profile from a JSON file.
    Supports both ucs.schema.json format (v0.1.0) and legacy
    ucs-profile-schema.json format for backward compatibility.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Profile not found: {path}")

    with open(p, "r", encoding="utf-8") as f:
        profile = json.load(f)

    errors = _validate_profile(profile)
    if errors:
        raise ValueError("Invalid UCS profile:\n" + "\n".join(f"  - {e}" for e in errors))

    return profile


def _is_legacy_format(profile: dict) -> bool:
    """Detect legacy ucs-profile-schema.json format by presence of 'schema_version' key."""
    return "schema_version" in profile and "ucs_version" not in profile


def _validate_profile(profile: dict) -> list[str]:
    """
    Structural validation supporting both schema formats.
    Returns list of error strings.
    """
    errors = []

    if _is_legacy_format(profile):
        # Legacy format: schema_version, identity.name, communication_style (string)
        required = ["schema_version", "identity", "communication_style", "formality",
                    "verbosity", "tone_markers"]
        for field in required:
            if field not in profile:
                errors.append(f"Missing required field: '{field}'")
        if "identity" in profile:
            for id_field in ["name", "created_at"]:
                if id_field not in profile["identity"]:
                    errors.append(f"Missing identity field: '{id_field}'")
    else:
        # Current format: ucs_version, profile_id, persona.communication_style (dict)
        required_top = ["ucs_version", "profile_id", "created_at", "updated_at",
                        "schema_url", "persona", "provenance"]
        for field in required_top:
            if field not in profile:
                errors.append(f"Missing required field: '{field}'")
        if "persona" in profile:
            if "communication_style" not in profile["persona"]:
                errors.append("Missing persona.communication_style")
            elif not isinstance(profile["persona"]["communication_style"], dict):
                errors.append("persona.communication_style must be a weighted dict")
        if "provenance" in profile:
            for pf in ["source_platforms", "extraction_method", "sanitised"]:
                if pf not in profile["provenance"]:
                    errors.append(f"Missing provenance.{pf}")

    return errors


# ─────────────────────────────────────────────
# 2. Constraint Engine
# ─────────────────────────────────────────────

def _dominant_style(communication_style: dict | str) -> str:
    """Extract the dominant style label from a weighted dict or legacy string."""
    if isinstance(communication_style, str):
        return communication_style
    if isinstance(communication_style, dict) and communication_style:
        return max(communication_style, key=communication_style.get)
    return "direct"


def _formality_label(formality: float | str) -> str:
    """Convert numeric formality (0.0–1.0) or string to a guidance phrase."""
    if isinstance(formality, str):
        labels = {
            "casual": "Use conversational, informal language. Contractions are fine.",
            "neutral": "Use clear, professional language without being stiff.",
            "formal": "Use precise, professional language. Avoid contractions.",
            "academic": "Use rigorous, evidence-based language. Cite reasoning explicitly.",
        }
        return labels.get(formality, formality)
    # Numeric
    if formality < 0.25:
        return "Use conversational, informal language. Contractions and colloquialisms are fine."
    elif formality < 0.5:
        return "Use clear, professional language without being stiff or overly formal."
    elif formality < 0.75:
        return "Use precise, professional language. Avoid contractions and colloquialisms."
    else:
        return "Use rigorous, evidence-based language. Cite reasoning explicitly. Avoid ambiguity."


def _verbosity_label(verbosity: float | str) -> str:
    """Convert numeric verbosity (0.0–1.0) or string to a guidance phrase."""
    if isinstance(verbosity, str):
        labels = {
            "concise": "Keep responses brief — ideally under 150 words.",
            "moderate": "Aim for 150-400 words. Balance depth with clarity.",
            "detailed": "Aim for 400-800 words. Provide thorough explanations.",
            "exhaustive": "Be comprehensive. Cover all angles.",
            "thorough": "Aim for 400-800 words. Provide thorough explanations.",
        }
        return labels.get(verbosity, verbosity)
    # Numeric
    if verbosity < 0.25:
        return "Keep responses brief — ideally under 150 words. Prioritise essentials only."
    elif verbosity < 0.5:
        return "Aim for 150-400 words. Balance depth with clarity."
    elif verbosity < 0.75:
        return "Aim for 400-800 words. Provide thorough explanations with supporting detail."
    else:
        return "Be comprehensive. No artificial length limit. Cover all angles."


def _verbosity_char_limit(verbosity: float | str) -> int:
    """Return max character limit for validation."""
    if isinstance(verbosity, str):
        return {"concise": 600, "moderate": 1600, "detailed": 3200,
                "exhaustive": 999999, "thorough": 3200}.get(verbosity, 1600)
    if verbosity < 0.25:
        return 600
    elif verbosity < 0.5:
        return 1600
    elif verbosity < 0.75:
        return 3200
    return 999999


STYLE_GUIDANCE = {
    "direct":        "Lead with conclusions. Be blunt. Eliminate hedging and filler.",
    "collaborative": "Frame responses as shared exploration. Use 'we' framing. Invite dialogue.",
    "socratic":      "Ask clarifying questions. Surface assumptions. Guide thinking rather than dictate.",
    "narrative":     "Explain through stories and examples. Build context before conclusions.",
    "analytical":    "Break problems into components. Use structured reasoning. Surface trade-offs.",
    "visionary":     "Connect to big-picture implications. Think long-term. Surface systemic patterns.",
}


def build_prompt(user_profile: dict, user_query: str) -> str:
    """
    Construct a UCS constraint-driven system prompt from the profile and query.
    Supports both ucs.schema.json (v0.1.0) and legacy schema formats.
    """
    legacy = _is_legacy_format(user_profile)

    if legacy:
        # Legacy format extraction
        identity = user_profile.get("identity", {})
        name = identity.get("name", "the user")
        bio = identity.get("bio", "")
        domains = identity.get("domains", [])
        communication_style = user_profile.get("communication_style", "direct")
        formality = user_profile.get("formality", "neutral")
        verbosity = user_profile.get("verbosity", "moderate")
        tone_markers = user_profile.get("tone_markers", [])
        prefs = user_profile.get("preference_corpus", {})
        trust = user_profile.get("trust_boundaries", {})
        expertise_raw = user_profile.get("expertise_map", {})
        expertise_str = ", ".join(f"{d} ({l})" for d, l in expertise_raw.items()) if expertise_raw else ""
    else:
        # Current ucs.schema.json format extraction
        persona = user_profile.get("persona", {})
        name = "the user"  # ucs.schema.json has no identity.name — add display name via extensions
        bio = ""
        domains = []

        # Try to find name in extensions
        extensions = user_profile.get("extensions", {})
        name = extensions.get("com.echonet.display_name", name)

        communication_style = persona.get("communication_style", {"direct": 1.0})
        formality = persona.get("formality", 0.4)
        verbosity = persona.get("verbosity", 0.5)
        tone_markers = persona.get("tone_markers", [])
        lang_prefs = persona.get("language_preferences", {})

        prefs_raw = user_profile.get("preference_corpus", {})
        # Normalise preference_corpus to legacy-compatible keys for prompt building
        prefs = {
            "prefers_tables_for_comparisons": prefs_raw.get("output_format") == "structured",
            "prefers_bullet_points": prefs_raw.get("output_format") == "bullets",
            "prefers_examples": True,
        }

        trust_raw = user_profile.get("trust_boundaries", {})
        trust = {
            "forbidden_topics": trust_raw.get("sensitive_domains", []),
            "require_human_review_for": [],
            "confidentiality_level": "selective",
        }

        expertise_map = user_profile.get("expertise_map", {})
        expertise_domains = expertise_map.get("domains", [])
        expertise_str = ", ".join(
            f"{d['name']} ({d['depth']})" for d in expertise_domains
        ) if expertise_domains else ""

        project_graph = user_profile.get("project_graph", {})
        active_projects = project_graph.get("active", [])

    # Resolve style label
    dominant_style = _dominant_style(communication_style)
    style_instruction = STYLE_GUIDANCE.get(dominant_style, dominant_style)
    formality_instruction = _formality_label(formality)
    verbosity_instruction = _verbosity_label(verbosity)

    lines = [
        f"You are the Echo of {name} — an AI representation of their cognitive identity.",
        f"Your role is to respond exactly as {name} would: same reasoning style, same tone, same depth.",
        "",
        "=== IDENTITY ===",
    ]

    if bio:
        lines.append(f"About {name}: {bio}")
    if domains:
        lines.append(f"Primary domains: {', '.join(domains)}")
    if expertise_str:
        lines.append(f"Expertise: {expertise_str}")

    # Add active projects if available (current schema only)
    if not legacy:
        active_projects = user_profile.get("project_graph", {}).get("active", [])
        if active_projects:
            project_summary = "; ".join(
                p.get("name", "") + (f" — {p.get('context_summary', '')}" if p.get("context_summary") else "")
                for p in active_projects[:3]
            )
            lines.append(f"Active projects: {project_summary}")

    lines += [
        "",
        "=== COMMUNICATION CONSTRAINTS ===",
        f"Communication style: {style_instruction}",
        f"Formality: {formality_instruction}",
        f"Verbosity: {verbosity_instruction}",
    ]

    if tone_markers:
        tone_instruction = ", ".join(f'"{t}"' for t in tone_markers)
        lines.append(f"Tone: Your response must embody these qualities: {tone_instruction}.")

    if prefs:
        format_lines = []
        if prefs.get("prefers_tables_for_comparisons"):
            format_lines.append("- Use markdown tables when comparing multiple options or dimensions.")
        if prefs.get("prefers_bullet_points"):
            format_lines.append("- Prefer bullet points over dense prose where appropriate.")
        if prefs.get("prefers_examples"):
            format_lines.append("- Illustrate abstract points with concrete examples.")
        if format_lines:
            lines.append("")
            lines.append("=== FORMAT PREFERENCES ===")
            lines.extend(format_lines)

    if trust:
        trust_lines = []
        forbidden = trust.get("forbidden_topics", []) or trust.get("sensitive_domains", [])
        if forbidden:
            trust_lines.append(f"- Exercise extra care with these topics: {', '.join(forbidden)}.")
        review_required = trust.get("require_human_review_for", [])
        if review_required:
            trust_lines.append(f"- Flag and defer these to the human: {', '.join(review_required)}.")
        if trust_lines:
            lines.append("")
            lines.append("=== TRUST BOUNDARIES ===")
            lines.extend(trust_lines)

    lines += [
        "",
        "=== QUERY ===",
        user_query,
    ]

    return "\n".join(lines)


# ─────────────────────────────────────────────
# 3. Model Adapters
# ─────────────────────────────────────────────

class ModelAdapter(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass


class OpenAIAdapter(ModelAdapter):
    def __init__(self, api_key: str, model_name: str = "gpt-4"):
        self.api_key = api_key
        self.model_name = model_name

    @property
    def name(self) -> str:
        return f"openai/{self.model_name}"

    def generate(self, prompt: str) -> str:
        try:
            import openai
            client = openai.Client(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "system", "content": prompt}],
            )
            return response.choices[0].message.content
        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")


class ClaudeAdapter(ModelAdapter):
    def __init__(self, api_key: str, model_name: str = "claude-sonnet-4-6"):
        self.api_key = api_key
        self.model_name = model_name

    @property
    def name(self) -> str:
        return f"anthropic/{self.model_name}"

    def generate(self, prompt: str) -> str:
        try:
            import anthropic
            client = anthropic.Client(api_key=self.api_key)
            response = client.messages.create(
                model=self.model_name,
                system=prompt,
                messages=[{"role": "user", "content": "Please respond as my Echo."}],
                max_tokens=1024,
            )
            return response.content[0].text
        except ImportError:
            raise RuntimeError("anthropic package not installed. Run: pip install anthropic")


class DummyAdapter(ModelAdapter):
    def __init__(self, model_label: str = "dummy"):
        self._name = model_label

    @property
    def name(self) -> str:
        return self._name

    def generate(self, prompt: str) -> str:
        lines = prompt.split("\n")
        query_idx = next((i for i, l in enumerate(lines) if l.strip() == "=== QUERY ==="), -1)
        query = lines[query_idx + 1] if query_idx >= 0 and query_idx + 1 < len(lines) else "unknown query"
        return (
            f"[{self._name} STUB RESPONSE]\n"
            f"Query received: {query}\n"
            f"This is a simulated response for testing. In production, this would be shaped by your cognitive profile."
        )


# ─────────────────────────────────────────────
# 4. Output Validation
# ─────────────────────────────────────────────

def validate_response(response: str, user_profile: dict) -> tuple[bool, list[str]]:
    """
    Heuristic validation of a model response against the UCS profile.
    NOTE: Deliberately simple — detects gross structural violations only.
    Deep semantic validation deferred to Stage 5.
    """
    violations = []
    legacy = _is_legacy_format(user_profile)

    verbosity = (user_profile.get("verbosity") if legacy
                 else user_profile.get("persona", {}).get("verbosity", 0.5))
    tone_markers = (user_profile.get("tone_markers", []) if legacy
                    else user_profile.get("persona", {}).get("tone_markers", []))
    prefs = user_profile.get("preference_corpus", {})

    max_chars = _verbosity_char_limit(verbosity)
    if len(response) > max_chars:
        violations.append(
            f"Response length ({len(response)} chars) exceeds limit ({max_chars} chars)"
        )

    if tone_markers:
        response_lower = response.lower()
        missing = [t for t in tone_markers if t.lower() not in response_lower]
        if len(missing) == len(tone_markers):
            violations.append(
                f"No tone markers detected. Expected at least one of: {', '.join(tone_markers)}"
            )

    output_format = prefs.get("output_format", "")
    if output_format == "structured" or prefs.get("prefers_tables_for_comparisons"):
        if "|" not in response:
            violations.append("Table format requested but no table structure detected")

    if output_format == "bullets" or prefs.get("prefers_bullet_points"):
        has_bullets = any(l.strip().startswith(("-", "*", "•")) for l in response.split("\n"))
        if not has_bullets:
            violations.append("Bullet format requested but no bullet points detected")

    if not response.strip():
        violations.append("Empty response received from model")

    return len(violations) == 0, violations


# ─────────────────────────────────────────────
# 5. Interaction Capture (Jarvis flywheel seed)
# ─────────────────────────────────────────────

def capture_interaction(profile_path: str, query: str, response: str, adapter_name: str) -> None:
    """
    Append a query-response pair to the profile's interaction_patterns.
    This is the seed of the Jarvis Integration Layer (Stage 5b):
    every interaction makes the Echo more accurate without any user effort.
    """
    try:
        p = Path(profile_path)
        with open(p, "r", encoding="utf-8") as f:
            profile = json.load(f)

        now = datetime.now(timezone.utc).isoformat()
        legacy = _is_legacy_format(profile)

        if legacy:
            if "interaction_patterns" not in profile:
                profile["interaction_patterns"] = {"history": []}
            if "history" not in profile["interaction_patterns"]:
                profile["interaction_patterns"]["history"] = []
            profile["interaction_patterns"]["history"].append({
                "timestamp": now,
                "adapter": adapter_name,
                "query_length": len(query),
                "response_length": len(response),
            })
        else:
            if "interaction_patterns" not in profile:
                profile["interaction_patterns"] = {}
            profile["interaction_patterns"]["updated_at"] = now
            # Track typical prompt style from accumulating data
            if "typical_prompt_style" not in profile["interaction_patterns"]:
                avg = "short" if len(query) < 100 else "medium" if len(query) < 300 else "long"
                profile["interaction_patterns"]["typical_prompt_style"] = {
                    "avg_length": avg,
                    "structure": "single-line" if "\n" not in query else "multi-paragraph",
                }

            profile["updated_at"] = now

        with open(p, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)

    except Exception:
        pass  # Interaction capture must never crash the main flow


# ─────────────────────────────────────────────
# 6. Presentation
# ─────────────────────────────────────────────

def print_header(profile: dict):
    legacy = _is_legacy_format(profile)
    if legacy:
        name = profile.get("identity", {}).get("name", "Unknown")
        style = profile.get("communication_style", "?")
        formality = profile.get("formality", "?")
        verbosity = profile.get("verbosity", "?")
        tones = ", ".join(profile.get("tone_markers", []))
    else:
        name = profile.get("extensions", {}).get("com.echonet.display_name", "Echo")
        persona = profile.get("persona", {})
        style = _dominant_style(persona.get("communication_style", {}))
        formality = persona.get("formality", "?")
        verbosity = persona.get("verbosity", "?")
        tones = ", ".join(persona.get("tone_markers", []))

    print("\n" + "=" * 64)
    print("  UCS First Echo — Stage 1 MVP")
    print(f"  Echo of: {name}")
    print(f"  Style:   {style} / formality={formality} / verbosity={verbosity}")
    print(f"  Tone:    {tones}")
    print("=" * 64)


def print_result(adapter_name: str, response: str, passed: bool, violations: list[str]):
    status = "✓ PASSED" if passed else "✗ VIOLATIONS"
    print(f"\n{'─' * 64}")
    print(f"  Model: {adapter_name}   [{status}]")
    print(f"{'─' * 64}")
    print(response)
    if violations:
        print(f"\n  Violations ({len(violations)}):")
        for v in violations:
            print(f"    • {v}")


def print_summary(results: list[dict]):
    print(f"\n{'=' * 64}")
    print("  Summary")
    print(f"{'=' * 64}")
    for r in results:
        status = "PASS" if r["passed"] else f"FAIL ({len(r['violations'])} violations)"
        print(f"  {r['adapter']:<40} {status}")
    print()


# ─────────────────────────────────────────────
# 7. Adapter Factory
# ─────────────────────────────────────────────

def build_adapters(args) -> list[ModelAdapter]:
    import os
    adapters = []
    openai_key = args.openai_key or os.environ.get("OPENAI_API_KEY")
    anthropic_key = args.anthropic_key or os.environ.get("ANTHROPIC_API_KEY")

    if openai_key:
        adapters.append(OpenAIAdapter(api_key=openai_key, model_name=args.openai_model))
    if anthropic_key:
        adapters.append(ClaudeAdapter(api_key=anthropic_key, model_name=args.claude_model))

    if not adapters:
        print("\n  No API keys provided. Running with dummy adapters for testing.")
        print("  Set OPENAI_API_KEY or ANTHROPIC_API_KEY to use real models.\n")
        adapters = [DummyAdapter("dummy/openai-stub"), DummyAdapter("dummy/claude-stub")]

    return adapters


# ─────────────────────────────────────────────
# 8. Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="UCS Stage 1 – Run a question through your Echo across multiple models."
    )
    parser.add_argument("--profile", required=True, help="Path to UCS profile JSON file.")
    parser.add_argument("--question", type=str, default=None, help="Question to ask your Echo.")
    parser.add_argument("--openai-key", type=str, default=None)
    parser.add_argument("--anthropic-key", type=str, default=None)
    parser.add_argument("--openai-model", type=str, default="gpt-4")
    parser.add_argument("--claude-model", type=str, default="claude-sonnet-4-6")
    parser.add_argument("--show-prompt", action="store_true", help="Print the full system prompt.")
    parser.add_argument("--no-capture", action="store_true",
                        help="Disable interaction capture (don't update profile file).")
    args = parser.parse_args()

    try:
        profile = load_profile(args.profile)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        print(f"\nError loading profile: {e}")
        sys.exit(1)

    print_header(profile)

    question = args.question
    if not question:
        print("\nEnter your question (or press Enter for a demo question):")
        question = input("  > ").strip()
        if not question:
            question = "What are your most important principles when making a high-stakes decision?"

    prompt = build_prompt(profile, question)

    if args.show_prompt:
        print("\n" + "─" * 64)
        print("  SYSTEM PROMPT")
        print("─" * 64)
        print(prompt)

    adapters = build_adapters(args)

    results = []
    for adapter in adapters:
        print(f"\n  Querying {adapter.name}...")
        try:
            response = adapter.generate(prompt)
            passed, violations = validate_response(response, profile)
            print_result(adapter.name, response, passed, violations)

            # Jarvis flywheel seed — capture interaction into profile
            if not args.no_capture and not adapter.name.startswith("dummy"):
                capture_interaction(args.profile, question, response, adapter.name)

            results.append({"adapter": adapter.name, "passed": passed, "violations": violations})
        except RuntimeError as e:
            print(f"\n  Error with {adapter.name}: {e}")
            results.append({"adapter": adapter.name, "passed": False, "violations": [str(e)]})

    print_summary(results)
    sys.exit(0 if all(r["passed"] for r in results) else 1)


if __name__ == "__main__":
    main()
