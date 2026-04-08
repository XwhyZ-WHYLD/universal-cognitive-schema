#!/usr/bin/env python3
"""
stage1_mvp.py – UCS Stage 1 First Echo MVP
Loads a UCS cognitive profile, builds a constraint-driven prompt,
sends it to two model adapters, validates responses, and presents results.

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
    Raises FileNotFoundError, json.JSONDecodeError, or ValueError on failure.
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


def _validate_profile(profile: dict) -> list[str]:
    """Lightweight structural validation. Returns list of error strings."""
    errors = []
    required = ["schema_version", "identity", "communication_style", "formality", "verbosity", "tone_markers"]
    for field in required:
        if field not in profile:
            errors.append(f"Missing required field: '{field}'")

    if "identity" in profile:
        for id_field in ["name", "created_at"]:
            if id_field not in profile["identity"]:
                errors.append(f"Missing identity field: '{id_field}'")

    valid_styles = ["analytical", "narrative", "socratic", "direct", "collaborative", "visionary"]
    if profile.get("communication_style") not in valid_styles:
        errors.append(f"Invalid communication_style: '{profile.get('communication_style')}'")

    if profile.get("formality") not in ["casual", "neutral", "formal", "academic"]:
        errors.append(f"Invalid formality: '{profile.get('formality')}'")

    if profile.get("verbosity") not in ["concise", "moderate", "detailed", "exhaustive"]:
        errors.append(f"Invalid verbosity: '{profile.get('verbosity')}'")

    if "tone_markers" in profile:
        if not isinstance(profile["tone_markers"], list) or len(profile["tone_markers"]) < 1:
            errors.append("'tone_markers' must be a non-empty list")

    return errors


# ─────────────────────────────────────────────
# 2. Constraint Engine
# ─────────────────────────────────────────────

VERBOSITY_GUIDANCE = {
    "concise":    "Keep responses brief — ideally under 150 words. Prioritise essential information only.",
    "moderate":   "Aim for 150-400 words. Balance depth with clarity.",
    "detailed":   "Aim for 400-800 words. Provide thorough explanations with supporting detail.",
    "exhaustive": "Be comprehensive. No artificial length limit. Cover all angles.",
}

FORMALITY_GUIDANCE = {
    "casual":   "Use conversational, informal language. Contractions and colloquialisms are fine.",
    "neutral":  "Use clear, professional language without being stiff or overly formal.",
    "formal":   "Use precise, professional language. Avoid contractions and colloquialisms.",
    "academic": "Use rigorous, evidence-based language. Cite reasoning explicitly. Avoid ambiguity.",
}

STYLE_GUIDANCE = {
    "analytical":    "Break problems into components. Use structured reasoning. Surface trade-offs explicitly.",
    "narrative":     "Explain through stories and examples. Build context before conclusions.",
    "socratic":      "Ask clarifying questions. Surface assumptions. Guide thinking rather than dictate answers.",
    "direct":        "Lead with conclusions. Be blunt. Eliminate hedging and filler.",
    "collaborative": "Frame responses as shared exploration. Use 'we' framing. Invite dialogue.",
    "visionary":     "Connect to big-picture implications. Think long-term. Surface systemic patterns.",
}


def build_prompt(user_profile: dict, user_query: str) -> str:
    """
    Construct a UCS constraint-driven system prompt from the profile and query.
    This is the core of the Constraint Engine — the Echo's behavioural fingerprint.
    """
    identity = user_profile.get("identity", {})
    name = identity.get("name", "the user")
    bio = identity.get("bio", "")
    domains = identity.get("domains", [])

    style = user_profile.get("communication_style", "direct")
    formality = user_profile.get("formality", "neutral")
    verbosity = user_profile.get("verbosity", "moderate")
    tone_markers = user_profile.get("tone_markers", [])

    prefs = user_profile.get("preference_corpus", {})
    trust = user_profile.get("trust_boundaries", {})
    expertise = user_profile.get("expertise_map", {})

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
    if expertise:
        exp_str = ", ".join(f"{d} ({l})" for d, l in expertise.items())
        lines.append(f"Expertise levels: {exp_str}")

    lines += [
        "",
        "=== COMMUNICATION CONSTRAINTS ===",
        f"Communication style: {STYLE_GUIDANCE.get(style, style)}",
        f"Formality: {FORMALITY_GUIDANCE.get(formality, formality)}",
        f"Verbosity: {VERBOSITY_GUIDANCE.get(verbosity, verbosity)}",
    ]

    if tone_markers:
        tone_instruction = ", ".join(f'"{t}"' for t in tone_markers)
        lines.append(f"Tone: Your response must embody these qualities: {tone_instruction}.")

    if prefs:
        lines.append("")
        lines.append("=== FORMAT PREFERENCES ===")
        if prefs.get("prefers_tables_for_comparisons"):
            lines.append("- Use markdown tables when comparing multiple options or dimensions.")
        if prefs.get("prefers_bullet_points"):
            lines.append("- Prefer bullet points over dense prose where appropriate.")
        if prefs.get("prefers_examples"):
            lines.append("- Illustrate abstract points with concrete examples.")

    if trust:
        lines.append("")
        lines.append("=== TRUST BOUNDARIES ===")
        forbidden = trust.get("forbidden_topics", [])
        if forbidden:
            lines.append(f"- Never engage with these topics: {', '.join(forbidden)}.")
        review_required = trust.get("require_human_review_for", [])
        if review_required:
            lines.append(f"- Flag and defer these action types to the human: {', '.join(review_required)}.")
        conf = trust.get("confidentiality_level")
        if conf:
            lines.append(f"- Confidentiality posture: {conf}.")

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
    """Base class for all model adapters."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Send the UCS prompt to the model and return the response string."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable adapter name for display."""


class OpenAIAdapter(ModelAdapter):
    """Adapter for OpenAI GPT models (openai>=1.0 SDK)."""

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
            raise RuntimeError(
                "openai package not installed. Run: pip install openai"
            )


class ClaudeAdapter(ModelAdapter):
    """Adapter for Anthropic Claude models."""

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
            # content is a list of blocks; extract text from first block
            return response.content[0].text
        except ImportError:
            raise RuntimeError(
                "anthropic package not installed. Run: pip install anthropic"
            )


class DummyAdapter(ModelAdapter):
    """
    Stub adapter for testing without external API access.
    Echoes the prompt back with the model name prepended.
    Simulates constraint-respecting behaviour for unit testing.
    """

    def __init__(self, model_label: str = "dummy"):
        self._name = model_label

    @property
    def name(self) -> str:
        return self._name

    def generate(self, prompt: str) -> str:
        # Extract the query from the prompt for a more realistic stub
        lines = prompt.split("\n")
        query_idx = next((i for i, l in enumerate(lines) if l.strip() == "=== QUERY ==="), -1)
        query = lines[query_idx + 1] if query_idx >= 0 and query_idx + 1 < len(lines) else "unknown query"

        return (
            f"[{self._name} STUB RESPONSE]\n"
            f"Query received: {query}\n"
            f"This is a simulated response for testing constraint enforcement. "
            f"In production, this would be a real model response shaped by your cognitive profile."
        )


# ─────────────────────────────────────────────
# 4. Output Validation
# ─────────────────────────────────────────────

VERBOSITY_CHAR_LIMITS = {
    "concise":    (0, 600),
    "moderate":   (0, 1600),
    "detailed":   (0, 3200),
    "exhaustive": (0, 999999),
}


def validate_response(response: str, user_profile: dict) -> tuple[bool, list[str]]:
    """
    Heuristic validation of a model response against the UCS profile.

    NOTE: These checks are deliberately simple and surface-level.
    They detect gross structural violations but cannot guarantee semantic
    fidelity or nuanced stylistic adherence. Deep validation is deferred
    to Stage 5 of the UCS roadmap.

    Returns:
        (passed: bool, violations: list[str])
    """
    violations = []
    verbosity = user_profile.get("verbosity", "moderate")
    prefs = user_profile.get("preference_corpus", {})
    tone_markers = user_profile.get("tone_markers", [])

    # Length check
    _, max_chars = VERBOSITY_CHAR_LIMITS.get(verbosity, (0, 999999))
    if len(response) > max_chars:
        violations.append(
            f"Response length ({len(response)} chars) exceeds {verbosity} limit ({max_chars} chars)"
        )

    # Tone keyword presence (heuristic — keyword matching only)
    if tone_markers:
        response_lower = response.lower()
        missing_tone = [t for t in tone_markers if t.lower() not in response_lower]
        if len(missing_tone) == len(tone_markers):
            violations.append(
                f"No tone markers detected in response. Expected at least one of: {', '.join(tone_markers)}"
            )

    # Table structure check
    if prefs.get("prefers_tables_for_comparisons"):
        if "|" not in response and "\t" not in response:
            violations.append("Tabular format requested but no table structure detected (missing '|' characters)")

    # Bullet point check
    if prefs.get("prefers_bullet_points"):
        has_bullets = any(line.strip().startswith(("-", "*", "•")) for line in response.split("\n"))
        if not has_bullets:
            violations.append("Bullet point format requested but no bullet points detected")

    # Empty response check
    if not response.strip():
        violations.append("Empty response received from model")

    passed = len(violations) == 0
    return passed, violations


# ─────────────────────────────────────────────
# 5. Presentation
# ─────────────────────────────────────────────

def print_header(profile: dict):
    name = profile.get("identity", {}).get("name", "Unknown")
    style = profile.get("communication_style", "?")
    formality = profile.get("formality", "?")
    verbosity = profile.get("verbosity", "?")
    tones = ", ".join(profile.get("tone_markers", []))

    print("\n" + "=" * 64)
    print(f"  UCS First Echo — Stage 1 MVP")
    print(f"  Echo of: {name}")
    print(f"  Profile: {style} / {formality} / {verbosity}")
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
        print(f"  {r['adapter']:<35} {status}")
    print()


# ─────────────────────────────────────────────
# 6. Adapter Factory
# ─────────────────────────────────────────────

def build_adapters(args) -> list[ModelAdapter]:
    """
    Build the list of adapters to run based on CLI args and environment.
    Falls back to dummy adapters if no API keys are provided.
    """
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
        adapters = [
            DummyAdapter("dummy/openai-stub"),
            DummyAdapter("dummy/claude-stub"),
        ]

    return adapters


# ─────────────────────────────────────────────
# 7. Main Entrypoint
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="UCS Stage 1 – Run a question through your Echo across multiple models."
    )
    parser.add_argument("--profile", required=True, help="Path to UCS profile JSON file.")
    parser.add_argument("--question", type=str, default=None, help="Question to ask your Echo.")
    parser.add_argument("--openai-key", type=str, default=None, help="OpenAI API key (or set OPENAI_API_KEY).")
    parser.add_argument("--anthropic-key", type=str, default=None, help="Anthropic API key (or set ANTHROPIC_API_KEY).")
    parser.add_argument("--openai-model", type=str, default="gpt-4", help="OpenAI model name (default: gpt-4).")
    parser.add_argument("--claude-model", type=str, default="claude-sonnet-4-6", help="Claude model name.")
    parser.add_argument("--show-prompt", action="store_true", help="Print the full system prompt before running.")
    args = parser.parse_args()

    # Load profile
    try:
        profile = load_profile(args.profile)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        print(f"\nError loading profile: {e}")
        sys.exit(1)

    print_header(profile)

    # Get question
    question = args.question
    if not question:
        print("\nEnter your question (or press Enter for a demo question):")
        question = input("  > ").strip()
        if not question:
            question = f"What are your most important principles when making a high-stakes decision?"

    # Build prompt
    prompt = build_prompt(profile, question)

    if args.show_prompt:
        print("\n" + "─" * 64)
        print("  SYSTEM PROMPT")
        print("─" * 64)
        print(prompt)

    # Build adapters
    adapters = build_adapters(args)

    # Run each adapter
    results = []
    for adapter in adapters:
        print(f"\n  Querying {adapter.name}...")
        try:
            response = adapter.generate(prompt)
            passed, violations = validate_response(response, profile)
            print_result(adapter.name, response, passed, violations)
            results.append({
                "adapter": adapter.name,
                "passed": passed,
                "violations": violations,
            })
        except RuntimeError as e:
            print(f"\n  Error with {adapter.name}: {e}")
            results.append({
                "adapter": adapter.name,
                "passed": False,
                "violations": [str(e)],
            })

    print_summary(results)

    # Exit code: 0 if all passed, 1 if any failed
    all_passed = all(r["passed"] for r in results)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
