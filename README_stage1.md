# UCS Stage 1 – First Echo MVP

The First Echo MVP proves that a single human can create a portable cognitive identity and observe consistent behaviour across multiple AI models.

## Files

| File | Purpose |
|------|---------|
| `schema/ucs-profile-schema.json` | Formal JSON Schema for a UCS cognitive profile |
| `schema/examples/sample-profile.json` | Sample profile for immediate testing |
| `capture_profile.py` | Interactive CLI to create your Echo profile |
| `stage1_mvp.py` | Main CLI — runs your question through two model adapters |

## Quick Start

### Step 1 — Create your Echo profile

```bash
python capture_profile.py --output my_profile.json
```

Or use the sample profile to test immediately:

```bash
cp schema/examples/sample-profile.json my_profile.json
```

### Step 2 — Run with dummy adapters (no API keys needed)

```bash
python stage1_mvp.py --profile my_profile.json --question "What is your approach to risk?"
```

### Step 3 — Run with real models

```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...

python stage1_mvp.py --profile my_profile.json --question "What is your approach to risk?"
```

### Optional flags

```bash
# Show the full system prompt being sent to models
python stage1_mvp.py --profile my_profile.json --show-prompt

# Specify a different Claude model
python stage1_mvp.py --profile my_profile.json --claude-model claude-opus-4-6
```

## Dependencies

The skeleton requires only the Python standard library (3.10+).

API clients are optional:

```bash
pip install openai        # for OpenAI adapter
pip install anthropic     # for Claude adapter
```

## Success Criteria (Stage 1)

- [ ] First user feels the Echo accurately reflects their style and thinking
- [ ] Consistent outputs observed across two models
- [ ] Feedback collected to refine constraint engine and profile schema

## Validation Note

Validators in this MVP are deliberately heuristic. They detect gross structural violations but cannot guarantee semantic fidelity. Deep semantic validation is deferred to Stage 5.

## Next Steps

After Stage 1 is proven with a real user:
- **Stage 2** — Trust Bootstrap (verified identity tiers, attestation)
- **Stage 3** — Governance v1 (ownership, dispute, posthumous use policies)
- **Stage 4** — Multi-Echo Expansion (5–10 users)
