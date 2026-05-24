#!/usr/bin/env python3
"""
UCS Trust Anchor
Creates an Ed25519 keypair and a UCS DID:
    did:ucs:<sha3-256(public_key)>

Security note:
This reference implementation writes the private key to disk for local development.
Production deployments should store the private key in a hardware-backed keystore,
secure enclave, TPM, HSM, or passkey-compatible authenticator.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

@dataclass
class TrustAnchor:
    did: str
    algorithm: str
    public_key_b64: str
    private_key_b64: str
    public_key_sha3_256: str
    created_at: str
    key_epoch: int = 1

def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

def generate_anchor() -> TrustAnchor:
    private_key = Ed25519PrivateKey.generate()
    private_raw = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_key = private_key.public_key()
    public_raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    digest = hashlib.sha3_256(public_raw).hexdigest()
    did = f"did:ucs:{digest}"
    return TrustAnchor(
        did=did,
        algorithm="Ed25519",
        public_key_b64=b64(public_raw),
        private_key_b64=b64(private_raw),
        public_key_sha3_256=digest,
        created_at=now_iso(),
    )

def write_anchor(anchor: TrustAnchor, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(asdict(anchor), indent=2), encoding="utf-8")
    output.chmod(0o600)

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a UCS Trust Fabric DID and Ed25519 trust anchor.")
    parser.add_argument("--out", default="ucs_trust_anchor.json", help="Output path for generated trust anchor JSON.")
    args = parser.parse_args()
    anchor = generate_anchor()
    write_anchor(anchor, Path(args.out))
    print(json.dumps({
        "did": anchor.did,
        "algorithm": anchor.algorithm,
        "public_key_sha3_256": anchor.public_key_sha3_256,
        "key_epoch": anchor.key_epoch,
        "created_at": anchor.created_at,
        "output": args.out,
    }, indent=2))

if __name__ == "__main__":
    main()
