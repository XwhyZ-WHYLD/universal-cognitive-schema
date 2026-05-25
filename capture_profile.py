#!/usr/bin/env python3
"""
capture_profile.py – UCS Stage 1 + Stage 2
Interactive CLI that walks a user through creating a UCS-compliant
cognitive profile and writes it to a JSON file.

Stage 2 addition: attach_trust_fabric_v3() automatically generates
a DID and Ed25519 trust anchor at profile creation time, upgrading
the provenance block to Trust Fabric v3 structure.
"""

import json
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = "1.0.0"

COMMUNICATION_STYLES = ["analytical", "narrative", "socratic", "direct", "collaborative", "visionary"]
FORMALITY_LEVELS = ["casual", "neutral", "formal", "academic"]
VERBOSITY_LEVELS = ["concise", "moderate", "detailed", "exhaustive"]
EXPERTISE_LEVELS = ["beginner", "intermediate", "advanced", "expert"]
CONFIDENTIALITY_LEVELS = ["open", "selective", "restricted", "private"]


# ─────────────────────────────────────────────
# Stage 2 — Trust Fabric v3 Integration
# ─────────────────────────────────────────────

def attach_trust_fabric_v3(profile: dict, anchor_output_path: str = None) -> dict:
    """
    Automatically generate a DID and Ed25519 trust anchor for a UCS profile
    and upgrade its provenance block to Trust Fabric v3 structure.

    This is the Stage 2 integration point — called automatically at profile
    creation time so every new Echo has a cryptographic identity from birth.

    Args:
        profile: The assembled UCS profile dict (post-validation).
        anchor_output_path: Optional path to write the trust anchor JSON.
                           Defaults to <profile_name>_trust_anchor.json

    Returns:
        The profile dict with v3 provenance attached and DID set.
    """
    try:
        from trust_anchor import generate_anchor, write_anchor, TrustAnchor
        from provenance_v3 import migrate_profile
        import dataclasses

        # Generate Ed25519 keypair and DID
        anchor = generate_anchor()

        # Write anchor to disk (chmod 600 — private key protected)
        if anchor_output_path is None:
            name_slug = profile.get("identity", {}).get("name", "echo").lower().replace(" ", "_")
            anchor_output_path = f"{name_slug}_trust_anchor.json"

        write_anchor(anchor, Path(anchor_output_path))

        # Migrate provenance to v3 structure with DID attached
        profile = migrate_profile(profile, dataclasses.asdict(anchor))

        print(f"\n  ✓ Trust Fabric v3 attached")
        print(f"  DID:    {anchor.did}")
        print(f"  Anchor: {anchor_output_path} (keep this file private)")

        return profile

    except ImportError:
        # trust_anchor.py or provenance_v3.py not found — skip silently
        # Stage 2 modules are optional; Stage 1 profile still valid
        print("\n  ⚠ Trust Fabric v3 skipped (trust_anchor.py not found)")
        print("    Run: pip install cryptography  and ensure trust_anchor.py is present")
        return profile

    except Exception as e:
        # Never crash profile creation due to Trust Fabric failure
        print(f"\n  ⚠ Trust Fabric v3 attachment failed: {e}")
        print("    Profile saved without v3 provenance.")
        return profile


# ─────────────────────────────────────────────
# Prompt helpers (unchanged from Stage 1)
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
# Profile collection (unchanged from Stage 1)
# ─────────────────────────────────────────────

def prompt_expertise_map() -> dict:
    if not prompt_bool("Would you like to specify your expertise levels per domain?", default=False):
        return {}
    domains = prompt_list(
        "List the domains you want to rate:",
        hint="e.g. machine learning, product strategy, finance",
        min_items=1,
        max_items=8,
    )
    expertise_map = {}
    for domain in domains:
        level = prompt_choice(f"  Expertise level for '{domain}':", EXPERTISE_LEVELS, default="intermediate")
        expertise_map[domain] = level
    return expertise_map


def prompt_trust_boundaries() -> dict:
    if not prompt_bool("Would you like to define trust boundaries for your Echo?", default=False):
        return {}
    boundaries = {}
    if prompt_bool("  Do you have any forbidden topics?", default=False):
        boundaries["forbidden_topics"] = prompt_list(
            "  List topics your Echo must never engage with:",
            hint="e.g. personal finances, family matters",
            min_items=1,
            max_items=10,
        )
    if prompt_bool("  Any actions requiring human review before your Echo proceeds?", default=False):
        boundaries["require_human_review_for"] = prompt_list(
            "  List action categories requiring your approval:",
            hint="e.g. legal commitments, financial decisions",
            min_items=1,
            max_items=10,
        )
    boundaries["confidentiality_level"] = prompt_choice(
        "  Default confidentiality posture for information sharing:",
        CONFIDENTIALITY_LEVELS,
        default="selective",
    )
    return boundaries


def build_profile(answers: dict) -> dict:
    """Assemble a UCS-compliant profile dict from collected answers."""
    profile = {
        "schema_version": SCHEMA_VERSION,
        "identity": {
            "name": answers["name"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        "communication_style": answers["communication_style"],
        "formality": answers["formality"],
        "verbosity": answers["verbosity"],
        "tone_markers": answers["tone_markers"],
    }
    if answers.get("bio"):
        profile["identity"]["bio"] = answers["bio"]
    if answers.get("domains"):
        profile["identity"]["domains"] = answers["domains"]
    if answers.get("expertise_map"):
        profile["expertise_map"] = answers["expertise_map"]
    preference_corpus = {}
    if "prefers_tables" in answers:
        preference_corpus["prefers_tables_for_comparisons"] = answers["prefers_tables"]
    if "prefers_bullets" in answers:
        preference_corpus["prefers_bullet_points"] = answers["prefers_bullets"]
    if preference_corpus:
        profile["preference_corpus"] = preference_corpus
    if answers.get("trust_boundaries"):
        profile["trust_boundaries"] = answers["trust_boundaries"]
    return profile


def collect_answers() -> dict:
    """Run the interactive questionnaire and return raw answers."""
    print("\n" + "=" * 60)
    print("  UCS First Echo — Cognitive Profile Capture")
    print("  Stage 1 + Stage 2 Trust Fabric  |  github.com/XwhyZ-WHYLD/universal-cognitive-schema")
    print("=" * 60)
    print("\nThis takes about 5 minutes. Your answers shape your Echo.")
    print("Press Ctrl+C at any time to cancel.\n")

    answers = {}
    answers["name"] = prompt_text("What is your full name?")
    answers["bio"] = prompt_text(
        "Write a short bio (2-3 sentences about who you are professionally):",
        max_length=500,
        required=False,
    )
    answers["domains"] = prompt_list(
        "What are your primary domains of expertise or interest?",
        hint="e.g. venture capital, AI research, product design",
        min_items=1,
        max_items=10,
    )
    answers["communication_style"] = prompt_choice(
        "Which best describes your communication style?",
        COMMUNICATION_STYLES,
        default="direct",
    )
    answers["formality"] = prompt_choice(
        "What is your default level of formality?",
        FORMALITY_LEVELS,
        default="neutral",
    )
    answers["verbosity"] = prompt_choice(
        "How detailed do you prefer your responses to be?",
        VERBOSITY_LEVELS,
        default="moderate",
    )
    answers["tone_markers"] = prompt_list(
        "List 3-5 words that best describe your tone:",
        hint="e.g. precise, curious, bold, empathetic, strategic",
        min_items=2,
        max_items=8,
    )
    answers["prefers_tables"] = prompt_bool(
        "Do you prefer tables when comparing options?", default=False
    )
    answers["prefers_bullets"] = prompt_bool(
        "Do you prefer bullet points over prose?", default=False
    )
    answers["expertise_map"] = prompt_expertise_map()
    answers["trust_boundaries"] = prompt_trust_boundaries()
    return answers


def validate_profile(profile: dict) -> list[str]:
    """Lightweight validation. Returns list of error strings."""
    errors = []
    required = ["schema_version", "identity", "communication_style", "formality", "verbosity", "tone_markers"]
    for field in required:
        if field not in profile:
            errors.append(f"Missing required field: {field}")
    if "identity" in profile:
        for id_field in ["name", "created_at"]:
            if id_field not in profile["identity"]:
                errors.append(f"Missing identity field: {id_field}")
    if "communication_style" in profile:
        valid = ["analytical", "narrative", "socratic", "direct", "collaborative", "visionary"]
        if profile["communication_style"] not in valid:
            errors.append(f"Invalid communication_style: {profile['communication_style']}")
    if "formality" in profile:
        if profile["formality"] not in ["casual", "neutral", "formal", "academic"]:
            errors.append(f"Invalid formality: {profile['formality']}")
    if "verbosity" in profile:
        if profile["verbosity"] not in ["concise", "moderate", "detailed", "exhaustive"]:
            errors.append(f"Invalid verbosity: {profile['verbosity']}")
    if "tone_markers" in profile:
        if not isinstance(profile["tone_markers"], list) or len(profile["tone_markers"]) < 1:
            errors.append("tone_markers must be a non-empty list")
    return errors


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="UCS Stage 1 + Stage 2 – Capture a cognitive profile for your Echo."
    )
    parser.add_argument(
        "--output",
        type=str,
        default="my_echo_profile.json",
        help="Output path for the generated profile JSON (default: my_echo_profile.json)",
    )
    parser.add_argument(
        "--no-trust-fabric",
        action="store_true",
        help="Skip Trust Fabric v3 DID generation (Stage 1 profile only)",
    )
    args = parser.parse_args()

    try:
        answers = collect_answers()
    except KeyboardInterrupt:
        print("\n\nProfile capture cancelled.")
        sys.exit(0)

    profile = build_profile(answers)

    errors = validate_profile(profile)
    if errors:
        print("\nValidation errors found:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    # ── Stage 2: attach Trust Fabric v3 DID and provenance ──
    if not args.no_trust_fabric:
        profile = attach_trust_fabric_v3(profile)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)

    print(f"\n{'=' * 60}")
    print(f"  Echo profile saved to: {output_path}")
    print(f"  Name:  {profile['identity']['name']}")
    print(f"  Style: {profile['communication_style']} / {profile['formality']} / {profile['verbosity']}")
    print(f"  Tone:  {', '.join(profile['tone_markers'])}")
    if profile.get('did'):
        print(f"  DID:   {profile['did']}")
    print(f"{'=' * 60}")
    print("\nNext step:")
    print(f"  python stage1_mvp.py --profile {output_path} --question \"Your question here\"")


if __name__ == "__main__":
    main()
