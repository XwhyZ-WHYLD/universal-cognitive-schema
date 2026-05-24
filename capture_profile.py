#!/usr/bin/env python3
"""
capture_profile.py – UCS Stage 1
Interactive CLI that walks a user through creating a UCS-compliant
cognitive profile and writes it to a JSON file.

Output format conforms to schema/ucs.schema.json (v0.1.0).
"""

import json
import sys
import uuid
import argparse
from datetime import datetime, timezone
from pathlib import Path


UCS_VERSION = "0.1.0"
SCHEMA_URL = "https://ucs-standard.org/schema/v0.1.0/ucs.schema.json"

COMMUNICATION_STYLES = ["direct", "collaborative", "socratic", "narrative", "analytical", "visionary"]
EXPERTISE_DEPTHS = ["aware", "functional", "proficient", "expert"]
AUTONOMY_LEVELS = ["low", "medium", "high"]
CONFIRMATION_FREQUENCIES = ["always", "sometimes", "rarely"]
OUTPUT_FORMATS = ["prose", "bullets", "structured", "mixed"]
RESPONSE_LENGTHS = ["concise", "moderate", "thorough"]


# ─────────────────────────────────────────────
# Prompt helpers
# ─────────────────────────────────────────────

def prompt_choice(question: str, options: list[str], default: str = None) -> str:
    """Present a numbered menu and return the chosen option."""
    print(f"\n{question}")
    for i, opt in enumerate(options, 1):
        marker = " (default)" if opt == default else ""
        print(f"  {i}. {opt}{marker}")
    while True:
        raw = input("  Your choice [number]: ").strip()
        if raw == "" and default:
            return default
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except ValueError:
            pass
        print("  Please enter a valid number.")


def prompt_float(question: str, default: float = 0.5) -> float:
    """Prompt for a float between 0.0 and 1.0."""
    print(f"\n{question} [0.0–1.0, default {default}]")
    while True:
        raw = input("  > ").strip()
        if raw == "":
            return default
        try:
            val = float(raw)
            if 0.0 <= val <= 1.0:
                return val
        except ValueError:
            pass
        print("  Please enter a number between 0.0 and 1.0.")


def prompt_list(question: str, hint: str = "", min_items: int = 1, max_items: int = 10) -> list[str]:
    """Prompt for a comma-separated list of values."""
    print(f"\n{question}")
    if hint:
        print(f"  Hint: {hint}")
    while True:
        raw = input("  Enter values (comma-separated): ").strip()
        items = [x.strip() for x in raw.split(",") if x.strip()]
        if min_items <= len(items) <= max_items:
            return items
        print(f"  Please enter between {min_items} and {max_items} values.")


def prompt_text(question: str, max_length: int = None, required: bool = True) -> str:
    """Prompt for a free-text string."""
    print(f"\n{question}")
    while True:
        raw = input("  > ").strip()
        if not raw and not required:
            return ""
        if not raw:
            print("  This field is required.")
            continue
        if max_length and len(raw) > max_length:
            print(f"  Please keep it under {max_length} characters (currently {len(raw)}).")
            continue
        return raw


def prompt_bool(question: str, default: bool = False) -> bool:
    """Prompt for a yes/no answer."""
    default_str = "Y/n" if default else "y/N"
    print(f"\n{question} [{default_str}]")
    raw = input("  > ").strip().lower()
    if raw == "":
        return default
    return raw in ("y", "yes")


# ─────────────────────────────────────────────
# Section builders
# ─────────────────────────────────────────────

def collect_persona() -> dict:
    """Collect persona / communication identity fields."""
    print("\n── COMMUNICATION STYLE ──────────────────────────────────")

    style = prompt_choice(
        "Which best describes your dominant communication style?",
        COMMUNICATION_STYLES,
        default="direct",
    )

    # Build weighted style dict — dominant style gets 0.7, user can split the rest
    style_weights: dict[str, float] = {s: 0.0 for s in ["direct", "collaborative", "socratic", "narrative"]}
    if style in style_weights:
        style_weights[style] = 0.7
    elif style == "analytical":
        style_weights["direct"] = 0.5
        style_weights["socratic"] = 0.2
    elif style == "visionary":
        style_weights["narrative"] = 0.5
        style_weights["collaborative"] = 0.2

    formality = prompt_float(
        "Formality level (0.0 = fully casual, 1.0 = fully formal)",
        default=0.4,
    )
    verbosity = prompt_float(
        "Verbosity level (0.0 = terse/minimal, 1.0 = highly detailed)",
        default=0.5,
    )

    tone_markers = prompt_list(
        "List 3-5 words that best describe your tone:",
        hint="e.g. precise, curious, bold, empathetic, strategic",
        min_items=2,
        max_items=8,
    )

    primary_lang = prompt_text(
        "Primary language (BCP-47 code, e.g. 'en', 'en-GB', 'ar'):",
        required=False,
    ) or "en"

    return {
        "communication_style": style_weights,
        "formality": formality,
        "verbosity": verbosity,
        "tone_markers": tone_markers,
        "language_preferences": {
            "primary": primary_lang,
        },
    }


def collect_expertise_map() -> dict | None:
    """Optionally collect a domain expertise map."""
    if not prompt_bool("Would you like to specify your expertise levels per domain?", default=True):
        return None

    print("\n── EXPERTISE MAP ────────────────────────────────────────")
    domains_raw = prompt_list(
        "List the domains you want to rate:",
        hint="e.g. venture building, AI infrastructure, product strategy",
        min_items=1,
        max_items=10,
    )

    now = datetime.now(timezone.utc).isoformat()
    domains = []
    for domain in domains_raw:
        depth = prompt_choice(
            f"  Depth for '{domain}':",
            EXPERTISE_DEPTHS,
            default="proficient",
        )
        note = prompt_text(
            f"  One-line note for '{domain}' (optional, press Enter to skip):",
            required=False,
        )
        entry: dict = {"name": domain, "depth": depth, "last_active": now}
        if note:
            entry["notes"] = note
        domains.append(entry)

    return {"domains": domains}


def collect_preference_corpus() -> dict | None:
    """Optionally collect output format preferences."""
    if not prompt_bool("Would you like to specify output format preferences?", default=True):
        return None

    print("\n── FORMAT PREFERENCES ───────────────────────────────────")
    output_format = prompt_choice(
        "Preferred output format:",
        OUTPUT_FORMATS,
        default="prose",
    )
    response_length = prompt_choice(
        "Preferred response length:",
        RESPONSE_LENGTHS,
        default="moderate",
    )

    prefs: dict = {
        "output_format": output_format,
        "response_length": response_length,
    }

    langs = prompt_list(
        "Preferred programming languages (comma-separated, or press Enter to skip):",
        hint="e.g. Python, TypeScript",
        min_items=0,
        max_items=10,
    ) if prompt_bool("  Do you have preferred programming languages?", default=False) else []
    if langs:
        prefs["code_language_preferences"] = langs

    return prefs


def collect_trust_boundaries() -> dict | None:
    """Optionally collect trust boundary settings."""
    if not prompt_bool("Would you like to define trust boundaries for your Echo?", default=True):
        return None

    print("\n── TRUST BOUNDARIES ─────────────────────────────────────")
    autonomy = prompt_choice(
        "How much should your Echo act without asking you first?",
        AUTONOMY_LEVELS,
        default="medium",
    )
    confirmation = prompt_choice(
        "How often should your Echo confirm before acting?",
        CONFIRMATION_FREQUENCIES,
        default="sometimes",
    )

    sensitive: list[str] = []
    if prompt_bool("  Any sensitive domains requiring extra care?", default=False):
        sensitive = prompt_list(
            "  List sensitive domains:",
            hint="e.g. legal commitments, financial decisions, family matters",
            min_items=1,
            max_items=10,
        )

    return {
        "autonomous_action_tolerance": autonomy,
        "preferred_confirmation_frequency": confirmation,
        "sensitive_domains": sensitive,
    }


def collect_project_graph() -> dict | None:
    """Optionally collect active project context."""
    if not prompt_bool("Would you like to add any active projects to your profile?", default=False):
        return None

    print("\n── ACTIVE PROJECTS ──────────────────────────────────────")
    projects = []
    now = datetime.now(timezone.utc).isoformat()

    while True:
        name = prompt_text("Project name (or press Enter to finish):", required=False)
        if not name:
            break
        description = prompt_text("  One-line description:", required=False)
        context = prompt_text("  Context summary (what stage, what problem):", required=False)
        tags_raw = prompt_list(
            "  Tags (comma-separated):",
            hint="e.g. preseed, AI, open-source",
            min_items=0,
            max_items=10,
        ) if prompt_bool("  Add tags?", default=False) else []

        project: dict = {
            "id": str(uuid.uuid4()),
            "name": name,
            "created_at": now,
            "status": "active",
        }
        if description:
            project["description"] = description
        if context:
            project["context_summary"] = context
        if tags_raw:
            project["tags"] = tags_raw
        projects.append(project)

        if not prompt_bool("  Add another project?", default=False):
            break

    return {"active": projects, "archived": []} if projects else None


# ─────────────────────────────────────────────
# Profile assembly
# ─────────────────────────────────────────────

def build_profile(
    persona: dict,
    expertise_map: dict | None,
    preference_corpus: dict | None,
    trust_boundaries: dict | None,
    project_graph: dict | None,
) -> dict:
    """Assemble a ucs.schema.json-compliant profile."""
    now = datetime.now(timezone.utc).isoformat()

    profile: dict = {
        "ucs_version": UCS_VERSION,
        "profile_id": str(uuid.uuid4()),
        "created_at": now,
        "updated_at": now,
        "schema_url": SCHEMA_URL,
        "persona": persona,
        "provenance": {
            "source_platforms": ["manual"],
            "extraction_method": "manual",
            "sanitised": True,
            "sanitised_at": now,
            "attestation_signature": None,
        },
    }

    if expertise_map:
        profile["expertise_map"] = expertise_map
    if preference_corpus:
        profile["preference_corpus"] = preference_corpus
    if trust_boundaries:
        profile["trust_boundaries"] = trust_boundaries
    if project_graph:
        profile["project_graph"] = project_graph

    return profile


# ─────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────

def validate_profile(profile: dict) -> list[str]:
    """
    Lightweight structural validation without external jsonschema dependency.
    Returns list of error strings. Empty = valid.
    """
    errors = []
    required_top = ["ucs_version", "profile_id", "created_at", "updated_at",
                    "schema_url", "persona", "provenance"]
    for field in required_top:
        if field not in profile:
            errors.append(f"Missing required field: '{field}'")

    if "persona" in profile:
        if "communication_style" not in profile["persona"]:
            errors.append("Missing persona.communication_style")
        else:
            cs = profile["persona"]["communication_style"]
            if not isinstance(cs, dict):
                errors.append("persona.communication_style must be a weighted dict")

    if "provenance" in profile:
        for pf in ["source_platforms", "extraction_method", "sanitised"]:
            if pf not in profile["provenance"]:
                errors.append(f"Missing provenance.{pf}")

    return errors


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="UCS Stage 1 – Capture a cognitive profile for your Echo."
    )
    parser.add_argument(
        "--output",
        type=str,
        default="my_echo_profile.json",
        help="Output path for the generated profile JSON (default: my_echo_profile.json)",
    )
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  UCS First Echo — Cognitive Profile Capture")
    print("  Stage 1 MVP  |  github.com/XwhyZ-WHYLD/universal-cognitive-schema")
    print("=" * 60)
    print("\nThis takes about 5 minutes. Your answers shape your Echo.")
    print("Output conforms to UCS schema v0.1.0 (ucs.schema.json).")
    print("Press Ctrl+C at any time to cancel.\n")

    try:
        persona = collect_persona()
        expertise_map = collect_expertise_map()
        preference_corpus = collect_preference_corpus()
        trust_boundaries = collect_trust_boundaries()
        project_graph = collect_project_graph()
    except KeyboardInterrupt:
        print("\n\nProfile capture cancelled.")
        sys.exit(0)

    profile = build_profile(
        persona=persona,
        expertise_map=expertise_map,
        preference_corpus=preference_corpus,
        trust_boundaries=trust_boundaries,
        project_graph=project_graph,
    )

    errors = validate_profile(profile)
    if errors:
        print("\nValidation errors found:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)

    style_summary = ", ".join(
        f"{k}:{v}" for k, v in profile["persona"]["communication_style"].items() if v > 0
    )
    print(f"\n{'=' * 60}")
    print(f"  Echo profile saved → {output_path}")
    print(f"  Profile ID: {profile['profile_id']}")
    print(f"  Style:      {style_summary}")
    print(f"  Formality:  {profile['persona']['formality']}")
    print(f"  Verbosity:  {profile['persona']['verbosity']}")
    print(f"  Tone:       {', '.join(profile['persona']['tone_markers'])}")
    print(f"{'=' * 60}")
    print("\nNext step:")
    print(f"  python stage1_mvp.py --profile {output_path} --question \"Your question here\"")
    print("\nValidate against schema:")
    print(f"  python -c \"from ucs_parser import Validator; v=Validator(); print(v.validate_file('{output_path}'))\"")


if __name__ == "__main__":
    main()
