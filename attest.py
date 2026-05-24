#!/usr/bin/env python3
"""
UCS Peer Attestation CLI

Creates a signed peer attestation over an Echo/UCS profile.

Usage:
    python attest.py \
      --profile echo_profile.json \
      --anchor alice_trust_anchor.json \
      --attestor-name "Alice Example" \
      --statement "I know this Echo owner and confirm this profile behaves consistently with them." \
      --out peer_attestation.json
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def future_iso(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def b64decode_nopad(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)

def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def canonical_json(data: Dict[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")

def sha3_512_json(data: Dict[str, Any]) -> str:
    return hashlib.sha3_512(canonical_json(data)).hexdigest()

def extract_profile_did(profile: Dict[str, Any]) -> str | None:
    provenance = profile.get("provenance", {})
    roots = provenance.get("identity_roots", {})
    return roots.get("did") or profile.get("did") or profile.get("id")

def sign_attestation(payload: Dict[str, Any], private_key_b64: str) -> str:
    private_key = Ed25519PrivateKey.from_private_bytes(b64decode_nopad(private_key_b64))
    return b64(private_key.sign(canonical_json(payload)))

def build_attestation(
    profile: Dict[str, Any],
    anchor: Dict[str, Any],
    attestor_name: str,
    statement: str,
    expires_days: int,
) -> Dict[str, Any]:
    profile_hash = sha3_512_json(profile)
    unsigned_payload = {
        "type": "peer",
        "format": "UCS-peer-attestation-v1",
        "target_did": extract_profile_did(profile),
        "target_profile_hash": profile_hash,
        "attestor_name": attestor_name,
        "attestor_did": anchor["did"],
        "attestor_public_key_b64": anchor["public_key_b64"],
        "statement": statement,
        "created_at": now_iso(),
        "expires_at": future_iso(expires_days),
        "signature_algorithm": anchor.get("algorithm", "Ed25519"),
        "key_epoch": anchor.get("key_epoch", 1),
    }
    signature = sign_attestation(unsigned_payload, anchor["private_key_b64"])
    attestation_hash = sha3_512_json(unsigned_payload)
    return {
        **unsigned_payload,
        "attestation_hash": attestation_hash,
        "signature": signature,
        "revocation_pointer": f"rev://{attestation_hash[:32]}",
    }

def main() -> None:
    parser = argparse.ArgumentParser(description="Create a signed UCS peer attestation.")
    parser.add_argument("--profile", required=True, help="Path to target Echo/UCS profile JSON.")
    parser.add_argument("--anchor", required=True, help="Path to attestor trust anchor JSON.")
    parser.add_argument("--attestor-name", required=True, help="Human-readable attestor name.")
    parser.add_argument("--statement", required=True, help="Attestation statement.")
    parser.add_argument("--expires-days", type=int, default=365, help="Attestation validity window in days.")
    parser.add_argument("--out", default="peer_attestation.json", help="Output attestation JSON path.")
    args = parser.parse_args()
    profile = load_json(Path(args.profile))
    anchor = load_json(Path(args.anchor))
    attestation = build_attestation(
        profile=profile,
        anchor=anchor,
        attestor_name=args.attestor_name,
        statement=args.statement,
        expires_days=args.expires_days,
    )
    out = Path(args.out)
    out.write_text(json.dumps(attestation, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": "created",
        "type": "peer",
        "target_did": attestation["target_did"],
        "attestor_did": attestation["attestor_did"],
        "attestation_hash": attestation["attestation_hash"],
        "output": str(out),
    }, indent=2))

if __name__ == "__main__":
    main()
