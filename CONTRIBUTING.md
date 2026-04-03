# Contributing to Universal Cognitive Schema

Thank you for contributing to UCS. This project exists because AI portability is too important to be left to any single company — and that means it depends on a community of people who care enough to shape it.

This document explains how contributions work, how the RFC process operates, and what we expect from everyone involved.

---

## Table of contents

- [Ways to contribute](#ways-to-contribute)
- [RFC process — proposing schema changes](#rfc-process)
- [Code contributions — parsers and tooling](#code-contributions)
- [Documentation contributions](#documentation-contributions)
- [Bug reports and issues](#bug-reports-and-issues)
- [Code of conduct](#code-of-conduct)
- [Governance](#governance)

---

## Ways to contribute

There are four ways to contribute, and all are equally valued:

**1. Propose or review an RFC** — the schema evolves through community consensus. If you think a dimension is missing, a field needs changing, or a new platform's data model should be represented, open an RFC.

**2. Build a parser** — we need extraction libraries for every major AI platform. If you can parse a platform's data export format into UCS, that is one of the most valuable contributions possible.

**3. Write tests** — schema validators, parser test suites, and interoperability tests. Correctness is a community responsibility.

**4. Improve documentation** — translate docs, add examples, clarify ambiguous sections, or write tutorials that make UCS more accessible.

---

## RFC process

All changes to the UCS schema specification go through the RFC (Request for Comments) process. This ensures every change is discussed, challenged, and improved before it becomes part of the standard.

### When do you need an RFC?

You need an RFC for:
- Adding a new top-level dimension to the schema
- Adding, removing, or renaming a required field
- Changing the type or enum values of an existing field
- Changing validation rules (required fields, constraints)
- Any change to the `provenance` or `extensions` blocks
- Deprecating any part of the schema

You do **not** need an RFC for:
- Fixing typos or improving descriptions
- Adding examples
- Updating tooling or parsers without schema changes
- Documentation improvements

### How to open an RFC

1. Fork the repository
2. Copy `rfcs/RFC-TEMPLATE.md` to `rfcs/RFC-XXXX-your-title.md` (use the next available number)
3. Fill in every section of the template — particularly the motivation and the alternatives considered
4. Open a pull request with the title `RFC-XXXX: Your title`
5. The community discussion happens in the pull request comments
6. After a minimum 14-day comment period with no unresolved objections, a maintainer will merge or close the RFC

### RFC states

| State | Meaning |
|---|---|
| `Draft` | Under active discussion — not yet accepted |
| `Accepted` | Approved — will be implemented in the next minor version |
| `Rejected` | Not accepted — PR closed with explanation |
| `Withdrawn` | Author withdrew the proposal |
| `Implemented` | Merged into a released version of the schema |

### What makes a good RFC?

- A clear one-sentence summary of what you are proposing
- A concrete motivation — what problem does this solve for real users?
- An example showing what the schema looks like before and after
- Alternatives considered — why is this approach better than the others?
- Backward compatibility analysis — does this break existing profiles?

---

## Code contributions

### Setting up locally

```bash
# Clone the repo
git clone https://github.com/XwhyZ-WHYLD/universal-cognitive-schema.git
cd universal-cognitive-schema

# If working on the Python parser
cd parsers/python
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Run tests
pytest
```

### Contribution workflow

1. **Fork** the repository on GitHub
2. **Create a branch** — use a descriptive name:
   ```bash
   git checkout -b feat/add-gemini-parser
   git checkout -b fix/persona-validation-bug
   git checkout -b docs/improve-fidelity-explanation
   ```
3. **Make your changes** — keep commits focused and atomic
4. **Write or update tests** — every parser contribution must include tests
5. **Open a pull request** — fill in the PR template completely

### Commit message format

```
type: short description (max 72 chars)

Optional longer explanation if needed.
```

Types:
- `feat` — new feature or parser
- `fix` — bug fix
- `docs` — documentation only
- `schema` — schema spec changes (must have an associated RFC)
- `test` — adding or updating tests
- `chore` — maintenance, formatting, dependency updates

### Parser requirements

A parser contribution must:

- Accept the platform's native data export format as input
- Output a valid UCS profile JSON that passes schema validation
- Include a `fidelity` report showing confidence scores per dimension
- Set `provenance.sanitised` only after running the sanitisation checks
- Include a test suite with at least one real (anonymised) export example
- Document which dimensions it can and cannot extract from the source platform

### What we will not merge

- Any parser that sets `sanitised: true` without actually running sanitisation
- Code that stores decrypted profile data outside the user's local environment
- Parsers that require users to share credentials with a third-party service
- Any contribution that introduces a mandatory proprietary dependency

---

## Documentation contributions

Documentation lives alongside the code. Good documentation is not optional — for a standards project, it is the product.

To contribute documentation:
- Fix typos or unclear phrasing: open a PR directly, no issue needed
- Add a new section or tutorial: open an issue first to discuss scope
- Translate documentation: open an issue to coordinate — we want consistency across translations

---

## Bug reports and issues

Before opening an issue, check whether it already exists.

**Schema bugs** — fields that are ambiguous, validation rules that produce wrong results, or examples that don't match the spec. Include the specific field path, the expected behaviour, and the actual behaviour.

**Parser bugs** — include the platform name, the type of export file, and a minimal anonymised example that reproduces the issue.

**Feature requests that don't require an RFC** — tooling features, new examples, documentation requests. Open an issue with the `enhancement` label.

Use the issue templates where provided. An issue with no reproduction steps or context will be closed with a request for more information.

---

## Code of conduct

UCS is a public good project. Everyone contributing is expected to:

- Be direct and constructive — criticism of ideas is welcome, criticism of people is not
- Assume good faith — most contributors are here because they care about the problem
- Respect the RFC process — schema changes need discussion, not just PRs
- Disclose conflicts of interest — if you work for a platform that would be affected by a proposed change, say so

Issues or pull requests that are disrespectful, dismissive, or deliberately obstructive will be closed.

---

## Governance

UCS is currently maintained by its founding contributors. As the standard matures, governance will transition to an independent foundation — no single company or individual will control the schema roadmap.

Decisions follow this hierarchy:

1. **Rough consensus** — most decisions are made by discussion in issues and PRs
2. **RFC process** — all schema changes go through RFC regardless of who proposes them
3. **Maintainer resolution** — if consensus cannot be reached, active maintainers resolve deadlocks
4. **Foundation** — once established, the foundation governs major version changes and maintainer selection

The goal is a standard that serves users, not any platform or commercial interest. Contributions that serve that goal are welcome. Contributions that would compromise neutrality will not be merged.

---

## Questions?

Open an issue with the `question` label. There are no stupid questions about a new standard — ambiguity in the spec is itself a bug worth reporting.
