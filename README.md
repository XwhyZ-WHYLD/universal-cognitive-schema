# Universal Cognitive Schema (UCS)

> The open standard for portable AI identity across platforms.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Schema Version](https://img.shields.io/badge/schema-v0.1.0--alpha-blue)](./schema)
[![Status](https://img.shields.io/badge/status-RFC-orange)](./RFC.md)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](./CONTRIBUTING.md)

---

## The problem

Your intelligence is fragmented.

Every AI system you use:
- learns you separately  
- stores context separately  
- responds differently  

You don’t move between systems.

You restart.

You have spent months — maybe years — working with AI tools. ChatGPT knows how you think. Claude understands your writing voice. Gemini is woven into your daily workflow.

Now you want to try a new model. Or your company switches vendors. Or a better tool launches.

You start from zero. Every time.

There is no way to take your cognitive history with you. No standard for what "your AI persona" even means. No format any platform agrees on. No migration path that doesn't involve pasting the same context document into every new chat window for the rest of your professional life.

**This is not a feature gap. It is a structural problem — and no platform will ever fix it.**

OpenAI, Anthropic, Google, and every other AI lab have a direct financial incentive to keep your memory, preferences, projects, and interaction history locked inside their ecosystem. The more you invest in a platform, the harder it is to leave. That is not a bug in their strategy. That is the strategy.

The platforms will never cooperate on this. They are not building the same product. They do not share a common data model. They do not agree on what "memory" even means — because each has defined it in a way that serves their specific product, not your interests.

ChatGPT's memory is your conversation preferences. Claude's memory is your project context and writing style. Gemini's memory is your entire Google account — your Gmail, your Photos, your purchase history. Grok's memory is your behaviour on X.

These are not different implementations of the same concept. They are fundamentally different things that happen to share a word.

No standard will emerge from the platforms. No regulator will mandate one in time. **Only a neutral, open, user-owned schema can solve this.** That is what this project is.

---

## What is UCS?

Your intelligence is fragmented.

Every AI system you use:
- learns you separately  
- stores context separately  
- responds differently  

You don’t move between systems.

You restart.

---

## UCS introduces a missing layer

Universal Cognitive Schema (UCS) defines a **portable cognitive identity**.

Instead of adapting to every AI system:

> AI systems adapt to you

---

## What this repo is

This is not a product.

It is an exploration of:

> a standard for how humans interface with AI systems

UCS defines a structured, human-readable, machine-parseable format for seven core dimensions of AI identity:

| Dimension | What it captures |
|---|---|
| **Persona** | Communication style, tone preferences, formality level, humour calibration |
| **Expertise map** | Domains of knowledge, depth calibration per domain, trusted sources |
| **Project graph** | Active and archived projects, their context, goals, and constraints |
| **Preference corpus** | Output format preferences, length defaults, structural preferences |
| **Interaction patterns** | How you prompt, what you correct, what you reinforce, what you reject |
| **Trust boundaries** | What tasks you delegate, your risk tolerance, your autonomy preferences |
| **Temporal context** | Recency weights, life chapters, evolution over time |

---

## What UCS is not

- It is **not** a product you pay for
- It is **not** a centralised database of your data
- It is **not** owned by any company, including the one that wrote it
- It is **not** a complete solution on its own — it is the standard that solutions are built on

---

## Example Output

Without UCS:
<generic response>

With UCS:
<constrained / identity-aligned response>

---

## Why open source, why now

The history of technology is littered with proprietary standards that entrenched incumbents and punished users. It is also full of open standards that became the invisible infrastructure of entire eras — HTTP, SMTP, OAuth, OpenAPI.

UCS is submitted as a public good for the same reason those standards were: **the value of a portability standard comes entirely from its neutrality.** A standard owned by one company is a moat. A standard owned by no one is infrastructure.

We are publishing this now — before any commercial product exists around it — because the window to establish a neutral standard is narrow. The platforms are deepening their memory features rapidly. Every month that passes without an open standard is another month of lock-in accumulating for billions of users.

The goal is not to build a business on top of this schema. The goal is for this schema to be so widely adopted that any business built on top of it — including commercial migration and identity products — is forced to interoperate, compete on quality, and serve users rather than trap them.

## Why now?

- AI ecosystems are fragmenting  
- Identity is becoming persistent  
- Interoperability is missing  

UCS explores filling that gap.

## What happens if UCS succeeds?
## If this works

- You stop rewriting yourself across tools  
- AI systems begin adapting to your identity  
- Cognitive state becomes portable  
- New categories of products emerge  

UCS is not a tool.

It is a layer.
---

## Schema structure (v0.1.0-alpha)

```json
{
  "ucs_version": "0.1.0",
  "profile_id": "uuid-v4",
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "schema_url": "https://ucs-standard.org/schema/v0.1.0",

  "persona": {
    "communication_style": "direct | collaborative | socratic | narrative",
    "formality": 0.0,
    "verbosity": 0.0,
    "tone_markers": ["string"],
    "language_preferences": {
      "primary": "en",
      "others": ["string"]
    }
  },

  "expertise_map": {
    "domains": [
      {
        "name": "string",
        "depth": "aware | functional | proficient | expert",
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
        "created_at": "ISO-8601",
        "tags": ["string"]
      }
    ],
    "archived": []
  },

  "preference_corpus": {
    "output_format": "prose | bullets | structured | mixed",
    "response_length": "concise | moderate | thorough",
    "code_language_preferences": ["string"],
    "citation_style": "inline | footnote | none",
    "custom": {}
  },

  "interaction_patterns": {
    "typical_prompt_style": "string",
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
        "active": true
      }
    ]
  },

  "extensions": {
    "namespace": "platform-specific or community extensions here"
  },

  "provenance": {
    "source_platforms": ["string"],
    "extraction_method": "api | export | manual | synthesised",
    "sanitised": true,
    "sanitised_at": "ISO-8601",
    "attestation_signature": "string"
  }
}
```

---

## Reference implementation

A reference parser is included that can read a ChatGPT data export and produce a UCS-compliant JSON profile.

```bash
pip install ucs-parser
```

```python
from ucs import Parser

# Parse a ChatGPT export
parser = Parser(source="chatgpt")
profile = parser.from_file("chatgpt_export.zip")

# Output a UCS-compliant profile
profile.to_json("my_profile.ucs.json")

# Validate against the schema
profile.validate()

# Get fidelity report — which dimensions were captured well
print(profile.fidelity_report())
```

---

## Fidelity and transparency

UCS is honest about what it can and cannot capture. Every profile export includes a fidelity report:

```json
{
  "fidelity": {
    "persona": { "score": 0.91, "note": "High confidence — inferred from 2,400 interactions" },
    "expertise_map": { "score": 0.78, "note": "Good — 14 domains identified" },
    "project_graph": { "score": 0.65, "note": "Moderate — some projects lacked structured context" },
    "preference_corpus": { "score": 0.88, "note": "High — strong signal from format corrections" },
    "interaction_patterns": { "score": 0.82, "note": "Good — consistent patterns detected" },
    "trust_boundaries": { "score": 0.55, "note": "Low — insufficient signal in source data" },
    "temporal_context": { "score": 0.70, "note": "Good — life chapters inferred from topic clusters" }
  }
}
```

Users always know what migrated well and what didn't. No silent failures. No false precision.

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
This schema is governed by an independent foundation, not by any commercial entity. No company — including those who contribute to the standard — may require proprietary extensions as a condition of compatibility.

---

## Roadmap

- [x] v0.1.0-alpha — Core schema definition, reference parser (ChatGPT → UCS)
- [ ] v0.2.0 — Claude export parser, Gemini export parser
- [ ] v0.3.0 — Injection library (UCS → system prompt / custom instructions for major platforms)
- [ ] v0.4.0 — Fidelity scoring engine
- [ ] v0.5.0 — Delta sync protocol (incremental profile updates)
- [ ] v1.0.0 — Stable schema, IETF Internet-Draft submission
- [ ] Post-1.0 — Multi-agent trust dimensions, agentic action profiles

---

## Security

Cognitive profiles are sensitive data. Before contributing or integrating, read the [Security Model](./SECURITY.md).

Key commitments:
- All profiles must be encrypted at rest and in transit
- Sanitisation attestation is a required field in compliant implementations
- No compliant implementation may transmit a decrypted profile to a third party without explicit, per-dimension user consent
- Vulnerability reports: security@ucs-standard.org (PGP key in SECURITY.md)

---

## Contributing

UCS is an open standard. The schema improves through contribution from everyone who cares about AI portability.

Ways to contribute:
- **Open an RFC** — propose additions or changes to the schema
- **Build a parser** — add extraction support for a new platform
- **Write a test suite** — help ensure schema implementations are consistent
- **Translate documentation** — make UCS accessible in more languages
- **Review open RFCs** — the schema is shaped by community consensus

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the full contribution guide and RFC process.

---

## FAQ

**Is this competing with Mem0?**
No. Mem0 is developer infrastructure for building AI apps with memory. UCS is a portability standard for users who want to move their accumulated AI identity between platforms. They operate at different layers and are complementary.

**Will OpenAI / Anthropic / Google support this?**
They don't need to. UCS works with their existing data export features (which GDPR and similar regulations already require). Native support from platforms would improve fidelity — but the standard works without it.

**Who owns this?**
No one. UCS is published under MIT license. Governance will move to an independent foundation as the standard matures. No commercial entity controls the roadmap.

**What about privacy?**
A cognitive profile is sensitive data. The schema is designed so that no centralised party ever needs to hold a decrypted profile. See [SECURITY.md](./SECURITY.md) and the zero-knowledge architecture principle above.

**Can I build a commercial product on top of UCS?**
Yes. MIT license. Build freely. The only restriction is that you may not call your product "UCS-compliant" if it adds mandatory proprietary extensions that break interoperability with other compliant implementations.

---

## Citation

If you use UCS in research or reference it in a publication:

```bibtex
@misc{ucs2026,
  title  = {Universal Cognitive Schema: An open standard for portable AI identity},
  year   = {2026},
  url    = {https://github.com/ucs-standard/ucs}
}
```

---

## License

MIT License — see [LICENSE](./LICENSE) for details.

The schema specification itself is additionally released under [CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/) — no rights reserved, maximum adoptability.

---

## Built by

UCS is developed by XWHYZ

Focused on:
- AI interoperability
- identity portability
- cognitive infrastructure

---

*UCS is an open standard project. It is not affiliated with OpenAI, Anthropic, Google, or any AI platform.*
