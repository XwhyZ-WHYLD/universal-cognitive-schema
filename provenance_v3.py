#!/usr/bin/env python3
"""
UCS Provenance v3 Migration

Migrates older UCS profile provenance into Trust Fabric v3 structure.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def canonical_json(data: Dict[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")

def sha3_512_json(data: Dict[str, Any]) -> str:
    return hashlib.sha3_512(canonical_json(data)).hexdigest()

def migrate_profile(profile: Dict[str, Any], anchor: Dict[str, Any] | None = None) -> Dict[str, Any]:
    old = profile.get("provenance", {}) or {}
    baseline_hash = sha3_512_json(profile)
    did = public_key = algorithm = None
    key_epoch = 1
    if anchor:
        did = anchor.get("did")
        public_key = anchor.get("public_key_b64")
        algorithm = anchor.get("algorithm", "Ed25519")
        key_epoch = anchor.get("key_epoch", 1)
    legacy_attestation = old.get("attestation_signature")
    attestations = []
    if legacy_attestation:
        attestations.append({
            "id": "legacy-attestation-001",
            "type": "legacy",
            "format": "UCS-v0.1.0-attestation_signature",
            "signature": legacy_attestation,
            "created_at": old.get("sanitised_at") or now_iso(),
            "expires_at": None,
            "revocation_pointer": None,
        })
    profile["provenance"] = {
        "version": "3.0",
        "trust_model": "UCS-TF-v3-TSSI",
        "source_platforms": old.get("source_platforms", ["manual"]),
        "extraction_method": old.get("extraction_method", "manual"),
        "sanitised": old.get("sanitised", True),
        "sanitised_at": old.get("sanitised_at") or now_iso(),
        "identity_roots": {
            "did": did,
            "classical_public_key": public_key,
            "classical_algorithm": algorithm,
            "pq_public_key": None,
            "pq_algorithm": None,
            "hardware_key_id": None,
            "recovery_key_hash": None,
            "key_epoch": key_epoch,
        },
        "attestations": attestations,
        "continuity": {
            "behavioral_score": None,
            "interaction_history_score": None,
            "semantic_drift": None,
        },
        "risk": {
            "synthetic_risk": None,
            "cyber_compromise_risk": None,
            "collusion_risk": None,
            "replay_risk": None,
        },
        "temporal_stewardship": {
            "mode": "MONITOR",
            "baseline_hash": baseline_hash,
            "current_state_hash": baseline_hash,
            "drift_score": 0.0,
            "witness_score": 1.0,
            "last_comparison_at": now_iso(),
            "signals": [],
        },
    }
    if did:
        profile["did"] = did
    return profile

def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate UCS profile provenance to Trust Fabric v3.")
    parser.add_argument("--profile", required=True, help="Input UCS profile JSON.")
    parser.add_argument("--anchor", help="Optional trust anchor JSON created by trust_anchor.py.")
    parser.add_argument("--out", required=True, help="Output migrated profile JSON.")
    args = parser.parse_args()
    profile = load_json(Path(args.profile))
    anchor = load_json(Path(args.anchor)) if args.anchor else None
    migrated = migrate_profile(profile, anchor)
    Path(args.out).write_text(json.dumps(migrated, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": "migrated",
        "version": "3.0",
        "did": migrated.get("did"),
        "output": args.out,
    }, indent=2))

if __name__ == "__main__":
    main()
