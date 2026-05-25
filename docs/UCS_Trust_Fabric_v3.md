# UCS Trust Fabric v3

> Open standard specification for quantum-ready, synthetic-resilient cognitive identity continuity.

---

## 1. Purpose

The Trust Fabric augments a standard UCS profile with a verifiable, post-quantum ready identity and provenance layer. It combines cryptographic anchors, social attestations, behavioural continuity and temporal stewardship into a unified trust calculus.

The goal is not to prove absolute identity, but to provide a continuously updated probability that a profile has remained under the same human control over time.

---

## 2. Identity Model

We model an Echo identity as a seven-tuple:

```
E = (K, A, B, G, R, T, W)
```

| Symbol | Dimension | Description |
|---|---|---|
| **K** | Cryptographic anchors | DID and keypairs (Ed25519, ML-DSA) |
| **A** | Attestations | Peer, institutional, cryptographic proofs |
| **B** | Behavioural continuity | Semantic style, temporal rhythm, linguistic fingerprint, cognitive consistency, interaction cadence |
| **G** | Trust graph topology | Network of attesting entities and their relationships |
| **R** | Revocation state | Key epochs, revocation registry, rotation history |
| **T** | Temporal continuity | Timestamps, session history, lifecycle events |
| **W** | Witness layer | Temporal stewardship signals and drift monitoring |

---

## 3. Trust Aggregation

Trust is computed via probabilistic aggregation of independent proofs. Each proof `q_i` is a scalar in [0,1] that decays over time:

```
q_i(t) = α_i × β_i × γ_i × exp(−λ × t)
```

Where:
- **α** models verifier reputation
- **β** captures cryptographic validity
- **γ** indicates freshness

The global trust score is:

```
T(E) = 1 − ∏_i (1 − q_i(t))
```

This multiplicative form means a single strong signal can raise trust significantly, while several weak signals cannot inflate trust beyond their combined probability.

---

## 4. Risk Penalty Factors

Three adversarial risk factors reduce the final trust score:

| Factor | Symbol | Models |
|---|---|---|
| Synthetic risk | R_synthetic | Deepfake and AI-generated identity attacks |
| Cyber compromise | R_cyber | Key compromise or session hijack risk |
| Collusion / Sybil | R_collusion | Coordinated graph attacks and Sybil manipulation |

---

## 5. Final Trust Equation

```
T_final = T(E) × (1 − R_synthetic) × (1 − R_cyber) × (1 − R_collusion) × W
```

Where `W` is the temporal witness factor (see Section 6).

---

## 6. Temporal Stewardship

To detect long-term drift, a witness factor decays with cumulative drift from the baseline:

```
W = exp(−λ_d × D_t)
```

Where `D_t` is the cumulative drift between the current state and the baseline at creation time. Higher drift reduces trust over time even if all other factors remain stable.

The TSSI (Temporal Stewardship Signal Index) monitors five drift dimensions:

| Dimension | Description |
|---|---|
| Behavioural | Changes in communication style and reasoning patterns |
| Claims | New assertions that contradict established profile content |
| Values | Shifts in ethical boundaries or trust policies |
| Security | Key rotation events, failed authentication attempts |
| Attestation | Loss or expiry of supporting attestations |

---

## 7. DID and Key Generation

Each profile SHOULD have a decentralised identifier derived from the public key:

```
did:ucs:sha3-256(public_key)
```

The initial implementation uses Ed25519. Future versions SHOULD support hybrid signing:

| Algorithm | Purpose |
|---|---|
| Ed25519 | Classical signatures |
| ML-DSA | Post-quantum signatures |
| SLH-DSA | Recovery and root signatures |
| ML-KEM | Key establishment |
| SHA3-512 / SHAKE256 | Hashing |

Reference implementation: `trust_anchor.py`

---

## 8. Trust Tiers

| Tier | Label | Trust Score | Description |
|---|---|---|---|
| T0 | Self-claimed | < 0.25 | Profile asserts its own authenticity |
| T1 | Socially attested | 0.25–0.50 | One or more named peers have signed |
| T2 | Institutionally verified | 0.50–0.75 | LinkedIn, credential authority, or government ID |
| T3 | Cryptographically anchored | 0.75–0.92 | Hardware key or biometric anchor |
| T4 | Quantum-ready verified | 0.92–0.99 | Hybrid classical + post-quantum signing |
| T5 | Multi-domain continuity | ≥ 0.99 | Cross-platform behavioural consensus |

---

## 9. Provenance v3 Schema

The legacy `attestation_signature` field is replaced by a structured `attestations` array. A minimal v3 provenance block:

```json
{
  "version": "3.0",
  "trust_model": "UCS-TF-v3-TSSI",
  "source_platforms": ["manual"],
  "extraction_method": "manual",
  "sanitised": true,
  "sanitised_at": "<ISO timestamp>",
  "identity_roots": {
    "did": "did:ucs:…",
    "classical_public_key": "…",
    "classical_algorithm": "Ed25519",
    "pq_public_key": null,
    "pq_algorithm": null,
    "hardware_key_id": null,
    "recovery_key_hash": null,
    "key_epoch": 1
  },
  "attestations": [],
  "continuity": {
    "behavioral_score": null,
    "interaction_history_score": null,
    "semantic_drift": null
  },
  "risk": {
    "synthetic_risk": null,
    "cyber_compromise_risk": null,
    "collusion_risk": null,
    "replay_risk": null
  },
  "temporal_stewardship": {
    "mode": "MONITOR",
    "baseline_hash": "…",
    "current_state_hash": "…",
    "drift_score": 0.0,
    "witness_score": 1.0,
    "last_comparison_at": "<ISO timestamp>",
    "signals": []
  }
}
```

---

## 10. Peer Attestation Format

Each attestation in the `attestations` array follows this structure:

```json
{
  "type": "peer",
  "format": "UCS-peer-attestation-v1",
  "target_did": "did:ucs:…",
  "target_profile_hash": "<SHA3-512 of canonical JSON>",
  "attestor_name": "Alice Example",
  "attestor_did": "did:ucs:…",
  "attestor_public_key_b64": "…",
  "statement": "I know this Echo owner and confirm this profile behaves consistently with them.",
  "created_at": "<ISO timestamp>",
  "expires_at": "<ISO timestamp>",
  "signature_algorithm": "Ed25519",
  "key_epoch": 1,
  "attestation_hash": "<SHA3-512 of unsigned payload>",
  "signature": "…",
  "revocation_pointer": "rev://…"
}
```

Reference implementation: `attest.py`

---

## 11. Revocation

All keys and attestations SHOULD support:

- **Expiry** via `expires_at` timestamp
- **Revocation** via `revocation_pointer`
- **Key rotation** via `key_epoch` increment
- **Epoch tracking** to detect stale credentials

---

## 12. Migration from v0.1.0

Existing profiles using the legacy provenance format MAY be migrated to v3 using:

```bash
python provenance_v3.py \
  --profile echo_profile.json \
  --anchor trust_anchor.json \
  --out echo_profile_v3.json
```

Legacy `attestation_signature` values are preserved as `type: legacy` attestation entries. No data is lost during migration.

---

## 13. Automatic Integration

When `capture_profile.py` creates a new profile, Trust Fabric v3 is attached automatically:

```bash
python capture_profile.py --output my_echo.json
```

This generates a DID, Ed25519 keypair, and v3 provenance block in a single step. Use `--no-trust-fabric` to skip if needed.

---

## 14. Quick Start

```bash
# Install dependency
pip install cryptography

# Step 1 — Generate trust anchor
python trust_anchor.py --out alice_anchor.json

# Step 2 — Migrate existing profile to v3
python provenance_v3.py \
  --profile echo_profile.json \
  --anchor alice_anchor.json \
  --out echo_profile_v3.json

# Step 3 — Create peer attestation
python attest.py \
  --profile echo_profile_v3.json \
  --anchor alice_anchor.json \
  --attestor-name "Alice Example" \
  --statement "I know this Echo owner and confirm this Echo behaves consistently with them." \
  --out peer_attestation.json
```

---

## 15. Security Considerations

The framework aims to be:
- **Post-quantum ready** — hybrid signing path defined
- **Tamper-evident** — SHA3-512 canonical hashing
- **Synthetic-resilient** — deepfake and AI-mimicry risk modelled explicitly
- **Revocable** — every key and attestation has an expiry and revocation pointer

It does not provide perfect or immutable identity. Operators MUST:
- Rotate keys periodically via `key_epoch`
- Monitor risk factors (`synthetic_risk`, `cyber_compromise_risk`)
- Implement revocation registries for production deployments
- Treat high drift or high risk scores as signals for manual review

Acceptable language: *quantum-ready, tamper-evident, synthetic-resilient, revocable.*
Not acceptable: *immune to all attacks, perfect identity, immutable.*

---

## 16. Related Documents

| Document | Location |
|---|---|
| RFC-0003 — Trust Fabric v3 RFC | `rfcs/RFC-0003.md` |
| Hardened architecture specification | `hardened_spec.md` |
| Interactive trust equation prototype | `prototypes/trust_fabric_v3.jsx` |
| Trust anchor generator | `trust_anchor.py` |
| Peer attestation CLI | `attest.py` |
| Provenance v3 migration | `provenance_v3.py` |

---

## 17. Revision History

| Version | Date | Change |
|---|---|---|
| v1.0 | 2026-05-24 | Initial specification |
| v1.1 | 2026-05-25 | Expanded sections 10–16, added quick start |
