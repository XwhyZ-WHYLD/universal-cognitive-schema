#!/usr/bin/env python3
"""
UCS Trust Score Engine
======================

Reference implementation of the Trust Fabric v3 trust calculus
(docs/UCS_Trust_Fabric_v3.md, sections 3-8).

This module reads the v3 `provenance` block produced by provenance_v3.py /
attest.py and computes:

    - per-proof scores q_i(t) with time decay
    - aggregate trust T(E) = 1 - prod(1 - q_i(t))
    - final trust T_final after risk penalties and the temporal witness factor
    - the discrete trust tier (T0-T5)

It is deliberately dependency-free (stdlib only) so it can run inside CI,
inside governance.py, and inside the capture pipeline without pulling in
`cryptography`. Signature *verification* lives in attest.py / a verifier;
this module consumes the *result* of verification via the `beta`
(cryptographic-validity) coefficient on each proof.

Design note — reconciliation of two published forms
----------------------------------------------------
RFC-0003 sec. 6 writes the final equation with explicit component factors
(T_identity x T_crypto x T_behavior x T_system x ... x graph_decay), while
the Trust Fabric v3 spec sec. 5 writes the compact probabilistic form
(T(E) x penalties x W). These are the same object viewed at two resolutions:
the spec's T(E) already aggregates the per-component proofs. This module
implements the spec's compact canonical form and exposes the component
contributions in `TrustResult.components` for transparency.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants — single source of truth for the trust calculus
# ---------------------------------------------------------------------------

# Decay constant for proof freshness, per day. exp(-LAMBDA_PROOF * age_days).
# ~0.0019/day puts a one-year-old proof at ~0.50 freshness.
LAMBDA_PROOF: float = 0.0019

# Decay constant for the temporal witness factor W = exp(-LAMBDA_DRIFT * D_t).
LAMBDA_DRIFT: float = 1.0

# Default verifier-reputation (alpha) by attestation type, in [0, 1].
# These are conservative priors; a production trust graph would learn them.
ALPHA_BY_TYPE: Dict[str, float] = {
    "cryptographic": 0.95,
    "institutional": 0.85,
    "peer": 0.55,
    "legacy": 0.40,
    "self": 0.20,
}

# Tier thresholds, aligned with Trust Fabric v3 spec section 8.
# (lower_inclusive_bound, tier_id, label)
TIER_TABLE = [
    (0.99, "T5", "Multi-domain continuity verified"),
    (0.92, "T4", "Quantum-ready verified"),
    (0.75, "T3", "Cryptographically anchored"),
    (0.50, "T2", "Institutionally verified"),
    (0.25, "T1", "Socially attested"),
    (0.00, "T0", "Self-claimed"),
]


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class ProofContribution:
    """A single proof's contribution to aggregate trust."""
    source: str            # e.g. "attestation:peer", "identity_root:did"
    proof_type: str        # peer | institutional | cryptographic | legacy | self
    alpha: float           # verifier reputation
    beta: float            # cryptographic validity (1.0 valid, 0.0 invalid/unknown)
    gamma: float           # freshness coefficient in [0,1]
    age_days: Optional[float]
    q: float               # final q_i(t) = alpha * beta * gamma * exp(-lambda * t)
    expired: bool = False
    revoked: bool = False


@dataclass
class TrustResult:
    did: Optional[str]
    trust_aggregate: float          # T(E) before penalties / witness
    trust_final: float              # after risk penalties and witness factor
    tier: str
    tier_label: str
    witness_factor: float
    risk_synthetic: float
    risk_cyber: float
    risk_collusion: float
    proofs: List[ProofContribution] = field(default_factory=list)
    components: Dict[str, float] = field(default_factory=dict)
    computed_at: str = ""
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return now_utc().replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        cleaned = ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _coerce_risk(value: Any) -> float:
    """Risk fields may be null in a freshly migrated profile. Treat unknown
    risk as 0.0 (no penalty) but record a note when we do so."""
    if value is None:
        return 0.0
    try:
        return _clamp(float(value))
    except (TypeError, ValueError):
        return 0.0


def freshness(age_days: Optional[float]) -> float:
    """gamma * exp(-lambda*t) folded into a single freshness coefficient.
    Unknown age is treated as moderately fresh (0.7) rather than fully fresh,
    so undated proofs cannot masquerade as brand-new."""
    if age_days is None:
        return 0.7
    if age_days < 0:
        age_days = 0.0
    return math.exp(-LAMBDA_PROOF * age_days)


def tier_for(score: float) -> tuple[str, str]:
    for lower, tid, label in TIER_TABLE:
        if score >= lower:
            return tid, label
    return "T0", "Self-claimed"


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def _attestation_proofs(provenance: Dict[str, Any], ref_time: datetime,
                        notes: List[str]) -> List[ProofContribution]:
    proofs: List[ProofContribution] = []
    attestations = provenance.get("attestations", []) or []
    for att in attestations:
        ptype = (att.get("type") or "peer").lower()
        alpha = ALPHA_BY_TYPE.get(ptype, ALPHA_BY_TYPE["peer"])

        created = parse_iso(att.get("created_at"))
        expires = parse_iso(att.get("expires_at"))
        age_days = ((ref_time - created).total_seconds() / 86400.0
                    if created else None)

        expired = bool(expires and ref_time > expires)
        # An attestation carrying a revocation_pointer is not itself revoked;
        # revocation is asserted by a registry. We expose the hook and treat a
        # caller-supplied "_revoked": true marker as authoritative for testing.
        revoked = bool(att.get("_revoked", False))

        # beta = cryptographic validity. We assume signatures were verified
        # upstream unless explicitly flagged invalid; a missing signature => 0.
        if att.get("signature") in (None, "",):
            beta = 0.0
            notes.append(f"attestation {att.get('attestation_hash','?')[:12]} "
                         "has no signature; beta=0")
        elif att.get("_signature_valid") is False:
            beta = 0.0
        else:
            beta = 1.0

        gamma = freshness(age_days)
        if expired or revoked:
            q = 0.0
        else:
            q = _clamp(alpha * beta * gamma)

        proofs.append(ProofContribution(
            source=f"attestation:{ptype}",
            proof_type=ptype,
            alpha=alpha, beta=beta, gamma=round(gamma, 6),
            age_days=round(age_days, 2) if age_days is not None else None,
            q=round(q, 6), expired=expired, revoked=revoked,
        ))
    return proofs


def _identity_root_proof(provenance: Dict[str, Any], ref_time: datetime,
                         notes: List[str]) -> Optional[ProofContribution]:
    roots = provenance.get("identity_roots", {}) or {}
    did = roots.get("did")
    if not did:
        return None

    has_classical = bool(roots.get("classical_public_key"))
    has_pq = bool(roots.get("pq_public_key"))
    has_hardware = bool(roots.get("hardware_key_id"))

    if not has_classical and not has_pq:
        # DID present but no key material — self-claimed root only.
        return ProofContribution(
            source="identity_root:did",
            proof_type="self", alpha=ALPHA_BY_TYPE["self"], beta=0.0,
            gamma=1.0, age_days=None, q=0.0,
        )

    # A cryptographic anchor. PQ + hardware raise alpha toward the quantum-ready
    # and hardware-anchored tiers.
    alpha = 0.78
    if has_pq:
        alpha = max(alpha, 0.93)
    if has_hardware:
        alpha = max(alpha, 0.88)
    q = _clamp(alpha * 1.0 * 1.0)
    return ProofContribution(
        source="identity_root:crypto",
        proof_type="cryptographic", alpha=alpha, beta=1.0, gamma=1.0,
        age_days=None, q=round(q, 6),
    )


def compute_trust(profile: Dict[str, Any],
                  ref_time: Optional[datetime] = None) -> TrustResult:
    """Compute the full Trust Fabric v3 trust result for a profile."""
    ref_time = ref_time or now_utc()
    notes: List[str] = []
    provenance = profile.get("provenance", {}) or {}
    did = (provenance.get("identity_roots", {}) or {}).get("did") \
        or profile.get("did")

    proofs: List[ProofContribution] = []
    root_proof = _identity_root_proof(provenance, ref_time, notes)
    if root_proof:
        proofs.append(root_proof)
    proofs.extend(_attestation_proofs(provenance, ref_time, notes))

    if not proofs:
        notes.append("No proofs present; profile is self-claimed (T0).")

    # T(E) = 1 - prod(1 - q_i)
    product = 1.0
    for p in proofs:
        product *= (1.0 - p.q)
    trust_aggregate = _clamp(1.0 - product)

    # Risk penalties
    risk = provenance.get("risk", {}) or {}
    r_syn = _coerce_risk(risk.get("synthetic_risk"))
    r_cyb = _coerce_risk(risk.get("cyber_compromise_risk"))
    r_col = _coerce_risk(risk.get("collusion_risk"))
    if all(risk.get(k) is None for k in
           ("synthetic_risk", "cyber_compromise_risk", "collusion_risk")):
        notes.append("Risk factors unset; treated as 0.0 (no penalty).")

    # Temporal witness factor W = exp(-lambda_d * drift)
    stewardship = provenance.get("temporal_stewardship", {}) or {}
    drift = stewardship.get("drift_score")
    if drift is None:
        witness = 1.0
        notes.append("No drift score; witness factor W=1.0.")
    else:
        witness = _clamp(math.exp(-LAMBDA_DRIFT * _clamp(float(drift))))

    trust_final = _clamp(
        trust_aggregate
        * (1.0 - r_syn)
        * (1.0 - r_cyb)
        * (1.0 - r_col)
        * witness
    )

    tier_id, tier_label = tier_for(trust_final)

    components = {
        "trust_aggregate": round(trust_aggregate, 6),
        "penalty_synthetic": round(1.0 - r_syn, 6),
        "penalty_cyber": round(1.0 - r_cyb, 6),
        "penalty_collusion": round(1.0 - r_col, 6),
        "witness_factor": round(witness, 6),
    }

    return TrustResult(
        did=did,
        trust_aggregate=round(trust_aggregate, 6),
        trust_final=round(trust_final, 6),
        tier=tier_id,
        tier_label=tier_label,
        witness_factor=round(witness, 6),
        risk_synthetic=r_syn,
        risk_cyber=r_cyb,
        risk_collusion=r_col,
        proofs=proofs,
        components=components,
        computed_at=now_iso(),
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Convenience API
# ---------------------------------------------------------------------------

def tier_at_least(profile: Dict[str, Any], minimum: str,
                  ref_time: Optional[datetime] = None) -> bool:
    """True if the profile's computed tier is >= `minimum` (e.g. 'T2')."""
    order = {tid: i for i, (_, tid, _) in
             enumerate(reversed(TIER_TABLE))}  # T0=0 .. T5=5
    result = compute_trust(profile, ref_time)
    return order.get(result.tier, 0) >= order.get(minimum, 99)


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute the UCS Trust Fabric v3 trust score and tier.")
    parser.add_argument("--profile", required=True,
                        help="Path to a UCS profile JSON (v3 provenance).")
    parser.add_argument("--json", action="store_true",
                        help="Emit the full result as JSON.")
    args = parser.parse_args()

    profile = load_json(Path(args.profile))
    result = compute_trust(profile)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
        return

    print(f"DID:          {result.did}")
    print(f"Trust (raw):  {result.trust_aggregate:.4f}")
    print(f"Trust final:  {result.trust_final:.4f}")
    print(f"Tier:         {result.tier} — {result.tier_label}")
    print(f"Witness W:    {result.witness_factor:.4f}")
    print(f"Proofs:       {len(result.proofs)}")
    for p in result.proofs:
        flag = " [EXPIRED]" if p.expired else (" [REVOKED]" if p.revoked else "")
        print(f"  - {p.source:28s} q={p.q:.4f} "
              f"(a={p.alpha:.2f} b={p.beta:.2f} g={p.gamma:.3f}){flag}")
    if result.notes:
        print("Notes:")
        for n in result.notes:
            print(f"  * {n}")


if __name__ == "__main__":
    main()
