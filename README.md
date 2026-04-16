# ucs-parser

**Reference parser for the [Universal Cognitive Schema (UCS)](https://github.com/XwhyZ-WHYLD/universal-cognitive-schema)** — the open standard for portable AI identity across platforms.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Schema Version](https://img.shields.io/badge/schema-v0.1.0--alpha-blue)](https://github.com/XwhyZ-WHYLD/universal-cognitive-schema/blob/main/schema)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://pypi.org/project/ucs-parser/)

---

## What is UCS?

UCS is an open standard for representing a person's accumulated AI interaction profile in a portable, platform-agnostic format. It lets you move your cognitive identity — preferences, expertise, interaction patterns, projects — between AI platforms without starting from zero every time.

## Installation

```bash
pip install ucs-parser
```

For full JSON Schema validation:

```bash
pip install "ucs-parser[validate]"
```

## Quickstart

### Parse a ChatGPT export

```python
from ucs_parser import Parser

parser = Parser(source="chatgpt")
profile = parser.from_file("chatgpt_export.zip")  # or conversations.json

# Write to file
profile.to_json("my_profile.ucs.json")

# Validate against the UCS schema
profile.validate()

# See per-dimension fidelity scores
print(profile.fidelity_report())
```

### CLI

```bash
ucs parse chatgpt_export.zip --output my_profile.ucs.json
ucs validate my_profile.ucs.json
ucs fidelity my_profile.ucs.json
```

## What gets inferred

From a ChatGPT `conversations.json` export, the parser automatically infers:

| Dimension | What is captured |
|---|---|
| **Persona** | Communication style blend, formality, verbosity, tone markers |
| **Expertise map** | Domains and depth levels from topic frequency |
| **Preference corpus** | Output format, response length, code language preferences |
| **Interaction patterns** | Prompt structure, common corrections, rejected behaviours |
| **Temporal context** | AI usage period and life chapter from message timestamps |
| **Provenance** | Source platform, extraction method, sanitisation attestation |
| **Fidelity** | Per-dimension confidence scores with interaction count |

## Fidelity report

Every parsed profile includes an honest fidelity report:

```
Fidelity Report (generated 2026-04-16 13:00 UTC)
  Overall:              0.72  Good overall fidelity with some gaps.
  Persona               ██████████  0.91  High confidence — inferred from 2,847 interactions.
  Expertise map         ████████░░  0.78  Good — 14 domains identified.
  Project graph         ██████░░░░  0.65  Moderate — some projects lacked structured context.
  Preference corpus     █████████░  0.88  High — strong signal from format corrections.
  Interaction patterns  ████████░░  0.83  Good — consistent correction patterns detected.
  Trust boundaries      █████░░░░░  0.52  Low — insufficient explicit delegation signal.
  Temporal context      ███████░░░  0.72  Good — life chapters inferred from topic shifts.
```

## Security

All profiles are sanitised by default. The sanitiser strips prompt-injection patterns, role-override syntax, and executable instructions before any content is written to a profile. The `provenance.sanitised` field attests to this.

## Roadmap

- **v0.1.0** — ChatGPT parser ✅
- **v0.2.0** — Claude + Gemini parsers
- **v0.3.0** — Injection library (UCS → system prompt for major platforms)
- **v0.4.0** — Standalone fidelity scoring engine
- **v0.5.0** — Delta sync protocol
- **v1.0.0** — Stable schema + IETF Internet-Draft

## Links

- [GitHub Repository](https://github.com/XwhyZ-WHYLD/universal-cognitive-schema)
- [Schema Specification](https://github.com/XwhyZ-WHYLD/universal-cognitive-schema/blob/main/schema/ucs.schema.json)
- [Contributing](https://github.com/XwhyZ-WHYLD/universal-cognitive-schema/blob/main/CONTRIBUTING.md)

## License

MIT — schema additionally released under CC0 1.0
