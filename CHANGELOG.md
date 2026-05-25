## v0.3.0 — Stage 3: Governance v1 (2026-05-25)
- Added `governance.py`: ownership, lifecycle states, posthumous modes
  (dormant/memorial/active), deletion (soft/hard/purge), dispute resolution,
  tamper-evident hash-chained audit log, and the central `can_operate()` gate.
- Added `trust_score.py`: reference implementation of the Trust Fabric v3 trust
  calculus (q_i decay, aggregate T(E), risk penalties, witness factor, tiers
  T0–T5). Unblocks the posthumous "active" gate (requires tier ≥ T2).
- Added `schema/ucs-governance.schema.json` (Draft 2020-12).
- Added `rfcs/RFC-0004.md` and `docs/UCS_Governance_v1.md`.
- Added `tests/test_governance.py` (40 tests). Full suite: 117 passing.
- NOTE — spec reconciliation: RFC-0003 §6 and Trust Fabric v3 spec §5 stated two
  different final trust equations. `trust_score.py` implements the spec's compact
  canonical form `T(E) × penalties × W` and exposes component contributions in
  `TrustResult.components`; the RFC's expanded factor form is the same object at
  finer resolution. Flagging for a future RFC-0003 erratum.

## v0.1.0-alpha
- Initial schema
- Stage 1 MVP
- CLI profile generator
