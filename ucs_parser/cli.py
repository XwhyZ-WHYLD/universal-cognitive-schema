"""
ucs-parser CLI

Usage:
    ucs parse chatgpt_export.zip --output my_profile.ucs.json
    ucs validate my_profile.ucs.json
    ucs fidelity my_profile.ucs.json
"""

from __future__ import annotations

import argparse
import json
import sys


def cmd_parse(args: argparse.Namespace) -> None:
    from ucs_parser import Parser

    print(f"Parsing {args.source} export: {args.input}")
    parser = Parser(source=args.source)
    result = parser.from_file(args.input)

    output = args.output or args.input.replace(".zip", "").replace(".json", "") + ".ucs.json"
    result.to_json(output)
    result.validate()
    print()
    print(result.fidelity_report())


def cmd_validate(args: argparse.Namespace) -> None:
    from ucs_parser import Validator

    v = Validator()
    result = v.validate_file(args.file)
    if result.valid:
        print(f"✓ {args.file} is valid.")
        sys.exit(0)
    else:
        print(f"✗ {args.file} is invalid:")
        for err in result.errors:
            print(f"  - {err}")
        sys.exit(1)


def cmd_fidelity(args: argparse.Namespace) -> None:
    from ucs_parser import FidelityScorer

    with open(args.file, encoding="utf-8") as f:
        data = json.load(f)

    scorer = FidelityScorer()
    report = scorer.score(data)
    print(report.summary())


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ucs",
        description="Universal Cognitive Schema — reference CLI (v0.1.0)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # parse
    p_parse = sub.add_parser("parse", help="Parse a platform export into a UCS profile.")
    p_parse.add_argument("input", help="Path to export file (.zip or .json)")
    p_parse.add_argument("--source", default="chatgpt", choices=["chatgpt"],
                         help="Source platform (default: chatgpt)")
    p_parse.add_argument("--output", "-o", help="Output path for .ucs.json file")
    p_parse.set_defaults(func=cmd_parse)

    # validate
    p_val = sub.add_parser("validate", help="Validate a .ucs.json profile against the schema.")
    p_val.add_argument("file", help="Path to .ucs.json file")
    p_val.set_defaults(func=cmd_validate)

    # fidelity
    p_fid = sub.add_parser("fidelity", help="Print fidelity report for a .ucs.json profile.")
    p_fid.add_argument("file", help="Path to .ucs.json file")
    p_fid.set_defaults(func=cmd_fidelity)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
