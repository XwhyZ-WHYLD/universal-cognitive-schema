#!/usr/bin/env python3
"""
UCS Governance v1 (Stage 3)
===========================

Governance for UCS / EchoNet profiles: ownership, deletion, posthumous use,
and dispute resolution. This module implements the *policy engine* and the
*data structures*. It deliberately does NOT implement Stage 6 inheritance
*execution* (actually running a successor's Echo) — it writes and enforces the
rules under which such execution would later be permitted.

Relationship to existing layers
--------------------------------
  - Identity / keys / attestations .... trust_anchor.py, attest.py  (Stage 2)
  - Trust score and tier (T0-T5) ...... trust_score.py              (Stage 2/3)
  - Runtime delegation consent ........ profile["trust_boundaries"] (existing)
  - Inheritance data shape ............ profile["inheritance"]       (existing)
  - Governance policy + lifecycle ..... THIS MODULE                 (Stage 3)

The governance block is stored under profile["governance"] and is versioned
independently of the schema and trust-fabric versions.

Core principle (from the threat model): governance is a *witness and gate*,
not an owner. It never silently mutates cognitive content; it records
ownership, evaluates whether a requested action is permitted, and logs an
auditable event. Every state transition is appended to an event log so
disputes can be reconstructed.

EchoNet v1 release policy — retire on death
-------------------------------------------
For the first EchoNet release an Echo is a living-person construct. When the
principal dies the Echo retires: permanently admin-only (export, delete, audit).
No posthumous operating mode is reachable by the runtime.

This is enforced via `retire_on_death = True` in the governance block and the
`retire_echo()` function. The MEMORIAL/ACTIVE mode machinery is preserved in
full for Stage 6 (Inheritance Lite) but is unreachable while this flag is set.
Flipping it to False is the deliberate Stage 6 unlock — not a code change.

The policy logic for WHAT posthumous operation looks like (whose consent, what
tier floor, objector rights) is deferred to a structured decision process before
Stage 6, once real Echo candidates and real estate concerns exist to reason from.
See docs/posthumous_decision_framework.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    # trust_score lives alongside this module in the repo root.
    from trust_score import compute_trust, tier_at_least
except ImportError:  # pragma: no cover - allow standalone import paths
    compute_trust = None
    tier_at_least = None

GOVERNANCE_VERSION = "1.0"

# v1 release flag — True = Echo retires on death; no posthumous operation.
# Set to False only when Stage 6 (Inheritance Lite) is ready to ship.
RETIRE_ON_DEATH_DEFAULT: bool = True


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class LifecycleState(str, Enum):
    """Top-level lifecycle of a profile."""
    ACTIVE = "active"            # normal operation by the living principal
    SUSPENDED = "suspended"      # temporarily frozen (dispute, security)
    DECEASED_PENDING = "deceased_pending"  # death asserted, not yet confirmed
    POSTHUMOUS = "posthumous"    # death confirmed; posthumous mode applies
    DELETED = "deleted"          # tombstoned; content erased


class PosthumousMode(str, Enum):
    DORMANT = "dormant"
    MEMORIAL = "memorial"
    ACTIVE = "active"


class DeletionMode(str, Enum):
    SOFT = "soft"        # reversible within grace window; content retained
    HARD = "hard"        # content erased, tombstone + audit log retained
    PURGE = "purge"      # erase everything including audit log (regulatory)


class DisputeState(str, Enum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED_UPHELD = "resolved_upheld"      # claimant prevailed
    RESOLVED_REJECTED = "resolved_rejected"  # claim rejected
    WITHDRAWN = "withdrawn"


class GovernanceError(Exception):
    """Raised when a governance action is not permitted."""


# ---------------------------------------------------------------------------
# Time / hashing helpers
# ---------------------------------------------------------------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha3_512_hex(data: Any) -> str:
    return hashlib.sha3_512(canonical_json(data)).hexdigest()


def event_id(payload: Dict[str, Any]) -> str:
    return "evt_" + sha3_512_hex(payload)[:24]


# ---------------------------------------------------------------------------
# Event log
# ---------------------------------------------------------------------------

@dataclass
class GovernanceEvent:
    id: str
    type: str
    actor_did: Optional[str]
    timestamp: str
    detail: Dict[str, Any] = field(default_factory=dict)
    prev_event_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def append_event(profile: Dict[str, Any], etype: str,
                 actor_did: Optional[str], detail: Dict[str, Any]) -> GovernanceEvent:
    """Append a tamper-evident event to the governance log.

    Each event embeds the hash of the previous event, forming a hash chain so
    that retroactive edits to the log are detectable.
    """
    gov = profile.setdefault("governance", {})
    log: List[Dict[str, Any]] = gov.setdefault("event_log", [])
    prev_hash = sha3_512_hex(log[-1]) if log else None
    base = {
        "type": etype,
        "actor_did": actor_did,
        "timestamp": now_iso(),
        "detail": detail,
        "prev_event_hash": prev_hash,
    }
    ev = GovernanceEvent(id=event_id(base), **base)
    log.append(ev.to_dict())
    return ev


def verify_event_chain(profile: Dict[str, Any]) -> bool:
    """Verify the integrity of the governance event hash chain."""
    log = (profile.get("governance", {}) or {}).get("event_log", []) or []
    prev_hash = None
    for entry in log:
        if entry.get("prev_event_hash") != prev_hash:
            return False
        prev_hash = sha3_512_hex(entry)
    return True


# ---------------------------------------------------------------------------
# Governance block initialisation
# ---------------------------------------------------------------------------

def _principal_did(profile: Dict[str, Any]) -> Optional[str]:
    return ((profile.get("provenance", {}) or {}).get("identity_roots", {}) or {}).get("did") \
        or profile.get("did")


def init_governance(profile: Dict[str, Any],
                    owner_did: Optional[str] = None) -> Dict[str, Any]:
    """Attach a default governance block. Idempotent: existing block kept."""
    if "governance" in profile and profile["governance"].get("version"):
        return profile["governance"]

    owner = owner_did or _principal_did(profile)
    gov: Dict[str, Any] = {
        "version": GOVERNANCE_VERSION,
        "policy_model": "UCS-GOV-v1",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "lifecycle_state": LifecycleState.ACTIVE.value,
        # Ownership: the principal owns by default. Controllers may act on the
        # owner's behalf within scoped permissions (never to alter ownership).
        "ownership": {
            "owner_did": owner,
            "owner_label": None,
            "controllers": [],        # [{did, role, scopes:[...], added_at}]
            "transfer_locked": True,   # ownership transfer disabled by default
        },
        # Posthumous policy. Default is conservative.
        "posthumous": {
            "mode": PosthumousMode.DORMANT.value,
            "directive_present": False,     # signed pre-mortem directive?
            "directive_hash": None,
            "disclosure_label_required": True,
            "successor_revocable": True,
            "objectors": [],                # DIDs who may force DORMANT
            "min_tier_for_active": "T2",
        },
        # Deletion policy.
        "deletion": {
            "soft_delete_grace_days": 30,
            "allow_hard_delete": True,
            "allow_purge": True,            # purge requires owner or legal order
            "purge_requires": "owner_or_legal_order",
        },
        # Dispute registry.
        "disputes": [],
        # Tamper-evident event chain.
        "event_log": [],
        # v1 release policy: retire Echo on death (no posthumous operation).
        # Stage 6 unlock: set to False when Inheritance Lite ships.
        "retire_on_death": RETIRE_ON_DEATH_DEFAULT,
    }
    profile["governance"] = gov
    append_event(profile, "governance.initialised", owner,
                 {"owner_did": owner, "version": GOVERNANCE_VERSION})
    return gov


def _touch(profile: Dict[str, Any]) -> None:
    profile["governance"]["updated_at"] = now_iso()


# ---------------------------------------------------------------------------
# Ownership
# ---------------------------------------------------------------------------

def add_controller(profile: Dict[str, Any], actor_did: str, controller_did: str,
                   role: str, scopes: List[str]) -> Dict[str, Any]:
    """Grant a controller scoped authority. Only the owner may add controllers."""
    gov = profile.get("governance") or init_governance(profile)
    if actor_did != gov["ownership"]["owner_did"]:
        raise GovernanceError("Only the owner may add controllers.")
    controller = {
        "did": controller_did,
        "role": role,
        "scopes": sorted(set(scopes)),
        "added_at": now_iso(),
    }
    gov["ownership"]["controllers"].append(controller)
    _touch(profile)
    append_event(profile, "ownership.controller_added", actor_did, controller)
    return controller


def _actor_has_scope(profile: Dict[str, Any], actor_did: str, scope: str) -> bool:
    gov = profile.get("governance", {})
    own = gov.get("ownership", {})
    if actor_did == own.get("owner_did"):
        return True
    for c in own.get("controllers", []):
        if c.get("did") == actor_did and (
            scope in c.get("scopes", []) or "*" in c.get("scopes", [])
        ):
            return True
    return False


def transfer_ownership(profile: Dict[str, Any], actor_did: str,
                       new_owner_did: str, unlock_token: Optional[str] = None) -> None:
    """Transfer ownership. Locked by default; requires the current owner and an
    explicit unlock. Transfer is itself logged and reversible only by the new
    owner. Ownership cannot be transferred while a profile is SUSPENDED or in a
    posthumous state — those paths go through inheritance, not transfer."""
    gov = profile.get("governance") or init_governance(profile)
    own = gov["ownership"]
    if actor_did != own["owner_did"]:
        raise GovernanceError("Only the current owner may transfer ownership.")
    state = gov["lifecycle_state"]
    if state not in (LifecycleState.ACTIVE.value,):
        raise GovernanceError(
            f"Ownership transfer not permitted in lifecycle state '{state}'.")
    if own.get("transfer_locked") and not unlock_token:
        raise GovernanceError(
            "Ownership transfer is locked. Provide an unlock_token to proceed.")
    prev = own["owner_did"]
    own["owner_did"] = new_owner_did
    _touch(profile)
    append_event(profile, "ownership.transferred", actor_did,
                 {"from": prev, "to": new_owner_did})


# ---------------------------------------------------------------------------
# Posthumous lifecycle
# ---------------------------------------------------------------------------

def register_posthumous_directive(profile: Dict[str, Any], actor_did: str,
                                   directive: Dict[str, Any]) -> str:
    """Record a signed pre-mortem directive expressing the principal's wishes.

    The directive itself should be signed by the principal's key (verified
    upstream by attest-style verification); here we store its hash and mark it
    present. A directive is what unlocks the ACTIVE posthumous path.
    """
    gov = profile.get("governance") or init_governance(profile)
    if actor_did != gov["ownership"]["owner_did"]:
        raise GovernanceError("Only the principal/owner may register a directive.")
    dhash = sha3_512_hex(directive)
    gov["posthumous"]["directive_present"] = True
    gov["posthumous"]["directive_hash"] = dhash
    # The directive may request a specific intended posthumous mode.
    requested = directive.get("requested_mode")
    if requested in {m.value for m in PosthumousMode}:
        gov["posthumous"]["requested_mode"] = requested
    _touch(profile)
    append_event(profile, "posthumous.directive_registered", actor_did,
                 {"directive_hash": dhash,
                  "requested_mode": gov["posthumous"].get("requested_mode")})
    return dhash


def assert_death(profile: Dict[str, Any], actor_did: str,
                 evidence_ref: Optional[str] = None) -> None:
    """Move a profile into DECEASED_PENDING. Does not yet activate any
    posthumous mode — confirmation is a separate, deliberate step so a single
    false assertion cannot flip a live person's Echo into posthumous use."""
    gov = profile.get("governance") or init_governance(profile)
    if not _actor_has_scope(profile, actor_did, "lifecycle"):
        raise GovernanceError("Actor lacks 'lifecycle' scope to assert death.")
    gov["lifecycle_state"] = LifecycleState.DECEASED_PENDING.value
    _touch(profile)
    append_event(profile, "lifecycle.death_asserted", actor_did,
                 {"evidence_ref": evidence_ref})


def confirm_posthumous(profile: Dict[str, Any], actor_did: str,
                       requested_mode: str,
                       ref_time: Optional[datetime] = None) -> PosthumousMode:
    """Confirm death and resolve the effective posthumous mode under policy.

    Enforces the conservative gate:
      - MEMORIAL requires inheritable=true and a designated successor.
      - ACTIVE additionally requires a signed pre-mortem directive AND
        trust tier >= configured minimum (default T2).
      - Any registered objector forces DORMANT.
    Returns the *effective* mode actually granted (may be downgraded).
    """
    gov = profile.get("governance") or init_governance(profile)
    if gov["lifecycle_state"] not in (
        LifecycleState.DECEASED_PENDING.value, LifecycleState.POSTHUMOUS.value
    ):
        raise GovernanceError(
            "Death must be asserted before posthumous confirmation.")
    if not _actor_has_scope(profile, actor_did, "lifecycle"):
        raise GovernanceError("Actor lacks 'lifecycle' scope to confirm.")

    post = gov["posthumous"]
    requested = PosthumousMode(requested_mode)

    # Objectors always win — collapse to DORMANT.
    if post.get("objectors"):
        effective = PosthumousMode.DORMANT
        reason = "objector_present"
    else:
        effective, reason = _resolve_posthumous_mode(
            profile, requested, ref_time)

    post["mode"] = effective.value
    post["confirmed_at"] = now_iso()
    post["effective_reason"] = reason
    gov["lifecycle_state"] = LifecycleState.POSTHUMOUS.value
    _touch(profile)
    append_event(profile, "lifecycle.posthumous_confirmed", actor_did,
                 {"requested": requested.value, "effective": effective.value,
                  "reason": reason})
    return effective


def _resolve_posthumous_mode(profile: Dict[str, Any], requested: PosthumousMode,
                             ref_time: Optional[datetime]
                             ) -> tuple[PosthumousMode, str]:
    gov = profile["governance"]
    post = gov["posthumous"]
    inheritance = profile.get("inheritance", {}) or {}
    inheritable = bool(inheritance.get("inheritable"))
    has_successor = bool(inheritance.get("successor_id"))

    if requested == PosthumousMode.DORMANT:
        return PosthumousMode.DORMANT, "requested_dormant"

    # MEMORIAL gate
    if not (inheritable and has_successor):
        return PosthumousMode.DORMANT, "not_inheritable_or_no_successor"

    if requested == PosthumousMode.MEMORIAL:
        return PosthumousMode.MEMORIAL, "memorial_granted"

    # ACTIVE gate (strictest)
    if requested == PosthumousMode.ACTIVE:
        if not post.get("directive_present"):
            return PosthumousMode.MEMORIAL, "active_denied_no_directive_downgraded_memorial"
        min_tier = post.get("min_tier_for_active", "T2")
        if tier_at_least is not None:
            meets = tier_at_least(profile, min_tier, ref_time)
        else:
            # Without the trust engine we cannot verify the tier — fail closed.
            meets = False
        if not meets:
            return PosthumousMode.MEMORIAL, f"active_denied_below_{min_tier}_downgraded_memorial"
        return PosthumousMode.ACTIVE, "active_granted"

    return PosthumousMode.DORMANT, "unknown_request"


def add_objector(profile: Dict[str, Any], objector_did: str,
                 relationship: Optional[str] = None) -> None:
    """Register an objector who can force DORMANT. Objection is a brake, not a
    claim of ownership; it cannot grant the objector any operating rights."""
    gov = profile.get("governance") or init_governance(profile)
    gov["posthumous"].setdefault("objectors", []).append(
        {"did": objector_did, "relationship": relationship, "at": now_iso()})
    # If already posthumously active/memorial, immediately freeze.
    if gov["lifecycle_state"] == LifecycleState.POSTHUMOUS.value:
        gov["posthumous"]["mode"] = PosthumousMode.DORMANT.value
        gov["posthumous"]["effective_reason"] = "objector_added_post_confirmation"
    _touch(profile)
    append_event(profile, "posthumous.objector_added", objector_did,
                 {"relationship": relationship})


def disclosure_label(profile: Dict[str, Any]) -> Optional[str]:
    """Return the mandatory disclosure string for a posthumously-operating Echo,
    or None if no label is required in the current state."""
    gov = profile.get("governance", {})
    if gov.get("lifecycle_state") != LifecycleState.POSTHUMOUS.value:
        return None
    post = gov.get("posthumous", {})
    if post.get("mode") == PosthumousMode.DORMANT.value:
        return None
    if not post.get("disclosure_label_required", True):
        return None
    owner = gov.get("ownership", {}).get("owner_label") or "the original person"
    return (f"This Echo operates posthumously and does not represent the live "
            f"intentions of {owner}. Mode: {post.get('mode')}.")


# ---------------------------------------------------------------------------
# Deletion
# ---------------------------------------------------------------------------

# Fields considered cognitive content for erasure purposes.
_CONTENT_FIELDS = [
    "persona", "expertise_map", "project_graph", "preference_corpus",
    "interaction_patterns", "temporal_context",
    # profile-schema variant field names
    "communication_style", "tone_markers", "identity",
]


def request_deletion(profile: Dict[str, Any], actor_did: str,
                     mode: str = "soft", reason: Optional[str] = None) -> Dict[str, Any]:
    """Request deletion. SOFT is reversible within a grace window; HARD erases
    content but retains a tombstone and the audit log; PURGE erases everything
    including the audit log and requires owner or legal order."""
    gov = profile.get("governance") or init_governance(profile)
    dmode = DeletionMode(mode)

    if not _actor_has_scope(profile, actor_did, "delete"):
        raise GovernanceError("Actor lacks 'delete' scope.")
    if dmode in (DeletionMode.HARD, DeletionMode.PURGE) \
            and not gov["deletion"].get("allow_hard_delete", True) \
            and dmode == DeletionMode.HARD:
        raise GovernanceError("Hard delete disabled by policy.")
    if dmode == DeletionMode.PURGE:
        is_owner = actor_did == gov["ownership"]["owner_did"]
        if not (is_owner or reason == "legal_order"):
            raise GovernanceError(
                "Purge requires the owner or a legal_order reason.")

    if dmode == DeletionMode.SOFT:
        grace = gov["deletion"].get("soft_delete_grace_days", 30)
        gov["lifecycle_state"] = LifecycleState.SUSPENDED.value
        gov["deletion"]["pending"] = {
            "mode": "soft", "requested_at": now_iso(),
            "grace_days": grace, "reversible_until": _plus_days(grace),
        }
        append_event(profile, "deletion.soft_requested", actor_did,
                     {"grace_days": grace, "reason": reason})
        _touch(profile)
        return {"status": "soft_pending", "reversible_until":
                gov["deletion"]["pending"]["reversible_until"]}

    # HARD or PURGE — erase content now.
    erased = _erase_content(profile)
    gov["lifecycle_state"] = LifecycleState.DELETED.value
    tombstone = {
        "deleted_at": now_iso(), "mode": dmode.value,
        "erased_fields": erased, "reason": reason,
        "owner_did_at_deletion": gov["ownership"]["owner_did"],
    }
    if dmode == DeletionMode.PURGE:
        # Purge removes the event log too, leaving only a minimal tombstone.
        append_event(profile, "deletion.purged", actor_did, {"reason": reason})
        gov["event_log"] = []
        tombstone["purged"] = True
    else:
        append_event(profile, "deletion.hard", actor_did,
                     {"erased_fields": erased, "reason": reason})
    gov["deletion"]["tombstone"] = tombstone
    _touch(profile)
    return {"status": "deleted", "mode": dmode.value, "erased_fields": erased}


def cancel_soft_deletion(profile: Dict[str, Any], actor_did: str) -> None:
    gov = profile.get("governance") or init_governance(profile)
    pending = gov["deletion"].get("pending")
    if not pending or pending.get("mode") != "soft":
        raise GovernanceError("No soft deletion pending.")
    if not _actor_has_scope(profile, actor_did, "delete"):
        raise GovernanceError("Actor lacks 'delete' scope.")
    gov["deletion"].pop("pending", None)
    gov["lifecycle_state"] = LifecycleState.ACTIVE.value
    _touch(profile)
    append_event(profile, "deletion.soft_cancelled", actor_did, {})


def _erase_content(profile: Dict[str, Any]) -> List[str]:
    erased = []
    for f in _CONTENT_FIELDS:
        if f in profile and profile[f] not in (None, {}, []):
            profile[f] = None
            erased.append(f)
    return erased


def _plus_days(days: int) -> str:
    from datetime import timedelta
    return (datetime.now(timezone.utc) + timedelta(days=days)) \
        .replace(microsecond=0).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# Disputes
# ---------------------------------------------------------------------------

def file_dispute(profile: Dict[str, Any], claimant_did: str, category: str,
                 statement: str, evidence_refs: Optional[List[str]] = None
                 ) -> Dict[str, Any]:
    """File a dispute. Filing a dispute does not by itself freeze the profile;
    escalation does. Categories: impersonation, ownership, accuracy,
    posthumous_objection, data_rights, other."""
    gov = profile.get("governance") or init_governance(profile)
    dispute = {
        "id": "dsp_" + sha3_512_hex(
            {"c": claimant_did, "t": now_iso(), "s": statement})[:20],
        "claimant_did": claimant_did,
        "category": category,
        "statement": statement,
        "evidence_refs": evidence_refs or [],
        "state": DisputeState.OPEN.value,
        "filed_at": now_iso(),
        "history": [{"state": DisputeState.OPEN.value, "at": now_iso()}],
    }
    gov.setdefault("disputes", []).append(dispute)
    _touch(profile)
    append_event(profile, "dispute.filed", claimant_did,
                 {"dispute_id": dispute["id"], "category": category})
    return dispute


def escalate_dispute(profile: Dict[str, Any], actor_did: str, dispute_id: str,
                     freeze: bool = True) -> None:
    """Move a dispute to UNDER_REVIEW and optionally SUSPEND the profile while
    it is adjudicated."""
    gov = profile.get("governance") or init_governance(profile)
    dispute = _find_dispute(gov, dispute_id)
    dispute["state"] = DisputeState.UNDER_REVIEW.value
    dispute["history"].append(
        {"state": DisputeState.UNDER_REVIEW.value, "at": now_iso()})
    if freeze:
        if gov["lifecycle_state"] == LifecycleState.ACTIVE.value:
            gov["lifecycle_state"] = LifecycleState.SUSPENDED.value
        # Mark this dispute as a freezer whenever the profile is (now) frozen,
        # so resolving an earlier dispute does not prematurely unfreeze while
        # this one is still under review.
        if gov["lifecycle_state"] == LifecycleState.SUSPENDED.value:
            dispute["froze_profile"] = True
    _touch(profile)
    append_event(profile, "dispute.escalated", actor_did,
                 {"dispute_id": dispute_id, "froze": dispute.get("froze_profile", False)})


def resolve_dispute(profile: Dict[str, Any], actor_did: str, dispute_id: str,
                    upheld: bool, resolution_note: str) -> None:
    """Resolve a dispute. If the profile was frozen for this dispute and no
    other dispute keeps it frozen, restore it to ACTIVE."""
    gov = profile.get("governance") or init_governance(profile)
    dispute = _find_dispute(gov, dispute_id)
    new_state = (DisputeState.RESOLVED_UPHELD if upheld
                 else DisputeState.RESOLVED_REJECTED)
    dispute["state"] = new_state.value
    dispute["resolution_note"] = resolution_note
    dispute["resolved_at"] = now_iso()
    dispute["history"].append({"state": new_state.value, "at": now_iso()})

    # Unfreeze if this dispute froze the profile and nothing else holds it.
    if dispute.get("froze_profile"):
        others_active = any(
            d["state"] == DisputeState.UNDER_REVIEW.value and d.get("froze_profile")
            for d in gov["disputes"] if d["id"] != dispute_id
        )
        if not others_active and gov["lifecycle_state"] == LifecycleState.SUSPENDED.value:
            gov["lifecycle_state"] = LifecycleState.ACTIVE.value
    _touch(profile)
    append_event(profile, "dispute.resolved", actor_did,
                 {"dispute_id": dispute_id, "upheld": upheld})


def _find_dispute(gov: Dict[str, Any], dispute_id: str) -> Dict[str, Any]:
    for d in gov.get("disputes", []):
        if d["id"] == dispute_id:
            return d
    raise GovernanceError(f"Dispute {dispute_id} not found.")



# ---------------------------------------------------------------------------
# Retirement (v1 release policy: Echoes retire on death)
# ---------------------------------------------------------------------------

def retire_echo(profile: dict, actor_did: str,
                evidence_ref: str | None = None) -> None:
    """Permanently retire an Echo on the principal's death.

    Sets lifecycle_state → DECEASED_PENDING then immediately → POSTHUMOUS with
    mode=DORMANT. When retire_on_death=True (the v1 default), can_operate()
    will return admin-only for all subsequent calls — no inference or
    transaction is possible.

    This is a one-way transition: retirement cannot be reversed.
    """
    gov = profile.get("governance") or init_governance(profile)
    if gov["lifecycle_state"] == LifecycleState.DELETED.value:
        raise GovernanceError("Cannot retire a deleted profile.")
    if gov["lifecycle_state"] == LifecycleState.POSTHUMOUS.value:
        raise GovernanceError("Profile is already retired.")
    if not _actor_has_scope(profile, actor_did, "lifecycle"):
        raise GovernanceError("Actor lacks 'lifecycle' scope to retire the Echo.")

    gov["lifecycle_state"] = LifecycleState.DECEASED_PENDING.value
    append_event(profile, "lifecycle.death_asserted", actor_did,
                 {"evidence_ref": evidence_ref, "method": "retire_echo"})

    gov["posthumous"]["mode"] = PosthumousMode.DORMANT.value
    gov["posthumous"]["confirmed_at"] = now_iso()
    gov["posthumous"]["effective_reason"] = "retire_on_death_v1"
    gov["lifecycle_state"] = LifecycleState.POSTHUMOUS.value
    _touch(profile)
    append_event(profile, "lifecycle.retired", actor_did,
                 {"retire_on_death": gov.get("retire_on_death", True),
                  "evidence_ref": evidence_ref})


# ---------------------------------------------------------------------------
# Permission gate — the single question the rest of the system asks
# ---------------------------------------------------------------------------

def can_operate(profile: Dict[str, Any],
                action: str = "infer",
                ref_time: Optional[datetime] = None) -> Dict[str, Any]:
    """The central gate. Given a profile and a requested action, return a
    decision the EchoNet runtime can enforce.

    action one of: "infer" (read-only inference), "transact" (commercial /
    representational), "admin" (export, manage).

    Returns {allowed: bool, reason: str, disclosure: str|None, state: str}.
    """
    gov = profile.get("governance") or init_governance(profile)
    state = gov["lifecycle_state"]
    label = disclosure_label(profile)

    def decision(allowed: bool, reason: str) -> Dict[str, Any]:
        return {"allowed": allowed, "reason": reason,
                "disclosure": label, "state": state, "action": action}

    if state == LifecycleState.DELETED.value:
        return decision(False, "profile_deleted")
    if state == LifecycleState.SUSPENDED.value:
        return decision(action == "admin", "profile_suspended")
    if state == LifecycleState.DECEASED_PENDING.value:
        return decision(action == "admin", "death_pending_confirmation")
    if state == LifecycleState.ACTIVE.value:
        return decision(True, "live_principal")

    # POSTHUMOUS
    if state == LifecycleState.POSTHUMOUS.value:
        # v1 release policy: retire_on_death collapses all posthumous states
        # to admin-only, regardless of mode. Stage 6 lifts this gate.
        if gov.get("retire_on_death", RETIRE_ON_DEATH_DEFAULT):
            return decision(action == "admin", "echo_retired_admin_only")
        # --- Stage 6+ paths (unreachable in v1 release) ---
        mode = gov["posthumous"]["mode"]
        if action == "admin":
            return decision(True, "posthumous_admin")
        if mode == PosthumousMode.DORMANT.value:
            return decision(False, "posthumous_dormant")
        if mode == PosthumousMode.MEMORIAL.value:
            return decision(action == "infer",
                            "posthumous_memorial_readonly")
        if mode == PosthumousMode.ACTIVE.value:
            return decision(True, "posthumous_active")
    return decision(False, "unknown_state")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _save(profile: Dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(profile, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="UCS Governance v1 CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Attach a governance block.")
    p_init.add_argument("--profile", required=True)
    p_init.add_argument("--owner-did")
    p_init.add_argument("--out")

    p_status = sub.add_parser("status", help="Show governance status + gate.")
    p_status.add_argument("--profile", required=True)
    p_status.add_argument("--action", default="infer",
                          choices=["infer", "transact", "admin"])

    p_verify = sub.add_parser("verify", help="Verify the event hash chain.")
    p_verify.add_argument("--profile", required=True)

    args = parser.parse_args()
    profile = _load(Path(args.profile))

    if args.cmd == "init":
        init_governance(profile, args.owner_did)
        out = Path(args.out or args.profile)
        _save(profile, out)
        print(json.dumps({"status": "initialised",
                          "owner": profile["governance"]["ownership"]["owner_did"],
                          "output": str(out)}, indent=2))

    elif args.cmd == "status":
        gov = profile.get("governance") or init_governance(profile)
        gate = can_operate(profile, args.action)
        print(json.dumps({
            "lifecycle_state": gov["lifecycle_state"],
            "posthumous_mode": gov["posthumous"]["mode"],
            "owner": gov["ownership"]["owner_did"],
            "open_disputes": sum(1 for d in gov.get("disputes", [])
                                 if d["state"] in ("open", "under_review")),
            "gate": gate,
        }, indent=2))

    elif args.cmd == "verify":
        ok = verify_event_chain(profile)
        print(json.dumps({"event_chain_valid": ok,
                          "events": len((profile.get("governance", {})
                                         or {}).get("event_log", []))}, indent=2))


if __name__ == "__main__":
    main()
