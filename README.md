# Universal Cognitive Schema (UCS)

> The open standard for portable AI identity across platforms.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Schema Version](https://img.shields.io/badge/schema-v0.1.0-blue)](https://github.com/XwhyZ-WHYLD/universal-cognitive-schema/blob/main/schema)
[![PyPI](https://img.shields.io/pypi/v/ucs-parser)](https://pypi.org/project/ucs-parser/)
[![Tests](https://github.com/XwhyZ-WHYLD/universal-cognitive-schema/actions/workflows/tests.yml/badge.svg)](https://github.com/XwhyZ-WHYLD/universal-cognitive-schema/actions/workflows/tests.yml)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/XwhyZ-WHYLD/universal-cognitive-schema/blob/main/CONTRIBUTING.md)

---

## The problem

You have spent months — maybe years — working with AI tools. ChatGPT knows how you think. Claude understands your writing voice. Gemini is woven into your daily workflow.

Now you want to try a new model. Or your company switches vendors. Or a better tool launches.

**You start from zero. Every time.**

There is no way to take your cognitive history with you. No standard for what "your AI persona" even means. No format any platform agrees on. No migration path that does not involve pasting the same context document into every new chat window for the rest of your professional life.

This is not a feature gap. It is a structural problem — and no platform will ever fix it.

OpenAI, Anthropic, Google, and every other AI lab have a direct financial incentive to keep your memory, preferences, projects, and interaction history locked inside their ecosystem. The more you invest in a platform, the harder it is to leave. That is not a bug in their strategy. That is the strategy.

**Only a neutral, open, user-owned schema can solve this. That is what this project is.**

---

## What UCS is

The Universal Cognitive Schema (UCS) is an open, versioned, platform-agnostic data standard for representing a person's accumulated AI interaction profile.

It is not a product. It is not a company. It is a **schema** — a shared language that any platform, tool, or application can speak — so that your cognitive identity can travel with you across the AI landscape, the same way your contacts travel across devices and your financial data travels across apps.

UCS defines a structured, human-readable, machine-parseable format for seven core dimensions of AI identity:

| Dimension | What it captures |
| --- | --- |
| **Persona** | Communication style blend, formality level, verbosity, tone markers |
| **Expertise map** | Domains of knowledge, depth calibration per domain, trusted sources |
| **Project graph** | Active and archived projects, their context, goals, and constraints |
| **Preference corpus** | Output format preferences, length defaults, structural preferences |
| **Interaction patterns** | How you prompt, what you correct, what you reinforce, what you reject |
| **Trust boundaries** | What tasks you delegate, your risk tolerance, your autonomy preferences |
| **Temporal context** | Recency weights, life chapters, evolution over time |

---

## Quickstart

```bash
pip install ucs-parser
```

```python
from ucs_parser import Parser

# Parse a ChatGPT data export
parser = Parser(source="chatgpt")
profile = parser.from_file("chatgpt_export.zip")  # or conversations.json

# Write a UCS-compliant profile
profile.to_json("my_profile.ucs.json")

# Validate against the schema
profile.validate()

# See per-dimension fidelity scores
print(profile.fidelity_report())
```

Or use the CLI:

```bash
ucs parse chatgpt_export.zip --output my_profile.ucs.json
ucs validate my_profile.ucs.json
ucs fidelity my_profile.ucs.json
```

---

## Schema structure (v0.1.0)

The full machine-readable schema is at [`schema/ucs.schema.json`](schema/ucs.schema.json). Example profiles are in [`schema/examples/`](schema/examples/).

```json
{
  "ucs_version": "0.1.0",
  "profile_id": "uuid-v4",
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "schema_url": "https://ucs-standard.org/schema/v0.1.0/ucs.schema.json",

  "persona": {
    "communication_style": {
      "direct": 0.6,
      "collaborative": 0.3,
      "socratic": 0.1,
      "narrative": 0.0
    },
    "formality": 0.35,
    "verbosity": 0.65,
    "tone_markers": ["precise", "direct", "dry wit"],
    "language_preferences": {
      "primary": "en",
      "others": []
    }
  },

  "expertise_map": {
    "domains": [
      {
        "name": "Software architecture",
        "depth": "expert",
        "last_active": "ISO-8601",
        "notes": "string"
      }
    ]
  },

  "project_graph": {
    "active": [
      {
        "id": "uuid-v4",
        "name": "string",
        "description": "string",
        "context_summary": "string",
        "status": "active | paused | completed | abandoned",
        "created_at": "ISO-8601",
        "tags": ["string"]
      }
    ],
    "archived": []
  },

  "preference_corpus": {
    "output_format": "prose | bullets | structured | mixed",
    "response_length": "concise | moderate | thorough",
    "code_language_preferences": ["Python", "TypeScript"],
    "citation_style": "inline | footnote | none",
    "custom": {}
  },

  "interaction_patterns": {
    "typical_prompt_style": {
      "opener": "context-then-ask | question | command",
      "structure": "single-line | multi-paragraph | bulleted | mixed",
      "avg_length": "short | medium | long"
    },
    "common_corrections": ["string"],
    "reinforced_behaviours": ["string"],
    "rejected_behaviours": ["string"]
  },

  "trust_boundaries": {
    "autonomous_action_tolerance": "low | medium | high",
    "preferred_confirmation_frequency": "always | sometimes | rarely",
    "sensitive_domains": ["string"]
  },

  "temporal_context": {
    "recency_weight": 0.7,
    "life_chapters": [
      {
        "label": "string",
        "from": "ISO-8601",
        "to": "ISO-8601 | null",
        "active": true,
        "notes": "string"
      }
    ]
  },

  "extensions": {
    "com.example.platform": {}
  },

  "provenance": {
    "source_platforms": ["chatgpt"],
    "extraction_method": "api | export | manual | synthesised",
    "sanitised": true,
    "sanitised_at": "ISO-8601",
    "attestation_signature": null
  },

  "fidelity": {
    "persona":              { "score": 0.91, "note": "High confidence — inferred from 2,847 interactions." },
    "expertise_map":        { "score": 0.78, "note": "Good — 14 domains identified." },
    "project_graph":        { "score": 0.65, "note": "Moderate — some projects lacked structured context." },
    "preference_corpus":    { "score": 0.88, "note": "High — strong signal from format corrections." },
    "interaction_patterns": { "score": 0.83, "note": "Good — consistent patterns detected." },
    "trust_boundaries":     { "score": 0.52, "note": "Low — insufficient signal in source data." },
    "temporal_context":     { "score": 0.72, "note": "Good — life chapters inferred from topic clusters." }
  }
}
```

---

## Design principles

**1. Zero-knowledge by architecture**
UCS profiles are encrypted on the user's device. No central server ever holds a decrypted profile. The schema is a format, not a storage system.

**2. Extensible, not brittle**
A versioned envelope with a stable core and optional platform-specific extension namespaces. A v2 profile degrades gracefully in a v1 reader. Unknown extensions are ignored, never errors.

**3. Sanitisation is mandatory**
Every profile passing through a UCS-compliant tool must pass through a sanitisation layer that strips prompt-injection patterns, executable instructions, and role-override syntax. The schema spec includes a sanitisation attestation field.

**4. Temporal by design**
Profiles are not snapshots. Recent interactions carry higher weight than older ones. Life chapter controls allow explicit resets. The right to delete is enforced at the schema level.

**5. Selective disclosure**
UCS supports dimension-level sharing. A user can share their `persona` and `preference_corpus` with a writing tool without exposing their `project_graph` or `trust_boundaries`. Consent is granular, not all-or-nothing.

**6. Neutral by governance**
This schema is governed by an independent foundation, not by any commercial entity. No company may require proprietary extensions as a condition of compatibility.

---

## Roadmap

| Version | Description | Status |
| --- | --- | --- |
| v0.1.0 | Core schema + ChatGPT parser + 77-test suite | ✅ Released |
| v0.2.0 | Claude export parser, Gemini export parser | 🔲 Planned |
| v0.3.0 | Injection library (UCS → system prompt for major platforms) | 🔲 Planned |
| v0.4.0 | Standalone fidelity scoring engine | 🔲 Planned |
| v0.5.0 | Delta sync protocol (incremental profile updates) | 🔲 Planned |
| v1.0.0 | Stable schema, IETF Internet-Draft submission | 🔲 Planned |
| Post-1.0 | Multi-agent trust dimensions, agentic action profiles | 🔲 Planned |

---

## Security

Cognitive profiles are sensitive data. Before contributing or integrating, read the [Security Model](SECURITY.md).

Key commitments:
- All profiles must be encrypted at rest and in transit
- Sanitisation attestation is a required field in compliant implementations
- No compliant implementation may transmit a decrypted profile to a third party without explicit, per-dimension user consent
- Vulnerability reports: [security@ucs-standard.org](mailto:security@ucs-standard.org)

---

## Contributing

UCS is an open standard. The schema improves through contribution from everyone who cares about AI portability.

- **Open an RFC** — propose additions or changes to the schema
- **Build a parser** — add extraction support for a new platform
- **Write a test suite** — help ensure schema implementations are consistent
- **Translate documentation** — make UCS accessible in more languages
- **Review open RFCs** — the schema is shaped by community consensus

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full contribution guide and RFC process.

---

## FAQ

**Is this competing with Mem0?**
No. Mem0 is developer infrastructure for building AI apps with memory. UCS is a portability standard for users. They operate at different layers and are complementary.

**Will OpenAI / Anthropic / Google support this?**
They don't need to. UCS works with their existing data export features. Native support would improve fidelity — but the standard works without it.

**Who owns this?**
No one. UCS is published under MIT license. Governance will move to an independent foundation as the standard matures.

**Can I build a commercial product on top of UCS?**
Yes. MIT license. Build freely. You may not call your product "UCS-compliant" if it adds mandatory proprietary extensions that break interoperability.

---

## Citation

```bibtex
@misc{ucs2026,
  title  = {Universal Cognitive Schema: An open standard for portable AI identity},
  year   = {2026},
  url    = {https://github.com/XwhyZ-WHYLD/universal-cognitive-schema}
}
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.

The schema specification itself is additionally released under [CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/) — no rights reserved, maximum adoptability.

---

*UCS is an open standard project. It is not affiliated with OpenAI, Anthropic, Google, or any AI platform.*
