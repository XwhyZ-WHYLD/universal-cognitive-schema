"""
Tests for UCS Stage 3 — trust_score.py and governance.py.

Run from repo root: pytest tests/test_governance.py -v
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# Make repo-root modules importable when pytest runs from tests/.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import trust_score as ts  # noqa: E402
import governance as gov  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _base_profile(did="did:ucs:abc123"):
    return {
        "ucs_version": "0.1.0",
        "did": did,
        "persona": {"summary": "test"},
        "expertise_map": {"python": "proficient"},
        "provenance": {
            "version": "3.0",
            "identity_roots": {
                "did": did,
                "classical_public_key": "pk_b64",
                "classical_algorithm": "Ed25519",
                "pq_public_key": None,
                "hardware_key_id": None,
                "key_epoch": 1,
            },
            "attestations": [],
            "risk": {
                "synthetic_risk": None,
                "cyber_compromise_risk": None,
                "collusion_risk": None,
            },
            "temporal_stewardship": {"drift_score": 0.0},
        },
    }


def _peer_attestation(created_days_ago=10, expires_days=355, valid=True):
    now = datetime.now(timezone.utc)
    return {
        "type": "peer",
        "signature": "sig_b64" if valid else "",
        "created_at": (now - timedelta(days=created_days_ago)).isoformat().replace("+00:00", "Z"),
        "expires_at": (now + timedelta(days=expires_days)).isoformat().replace("+00:00", "Z"),
        "attestation_hash": "deadbeef" * 8,
    }


# ---------------------------------------------------------------------------
# trust_score tests
# ---------------------------------------------------------------------------

class TestTrustScore:
    def test_self_claimed_is_t0(self):
        p = _base_profile()
        p["provenance"]["identity_roots"]["classical_public_key"] = None
        result = ts.compute_trust(p)
        assert result.tier == "T0"
        assert result.trust_final < 0.25

    def test_crypto_anchor_raises_tier(self):
        p = _base_profile()
        result = ts.compute_trust(p)
        # Classical key alone => cryptographic root proof present.
        assert result.trust_final > 0.25
        assert any(pr.proof_type == "cryptographic" for pr in result.proofs)

    def test_peer_attestation_adds_trust(self):
        p = _base_profile()
        before = ts.compute_trust(p).trust_final
        p["provenance"]["attestations"].append(_peer_attestation())
        after = ts.compute_trust(p).trust_final
        assert after > before

    def test_expired_attestation_contributes_zero(self):
        p = _base_profile()
        p["provenance"]["attestations"].append(
            _peer_attestation(created_days_ago=400, expires_days=-10))
        result = ts.compute_trust(p)
        peer = [pr for pr in result.proofs if pr.proof_type == "peer"][0]
        assert peer.expired is True
        assert peer.q == 0.0

    def test_unsigned_attestation_zero_beta(self):
        p = _base_profile()
        p["provenance"]["attestations"].append(_peer_attestation(valid=False))
        result = ts.compute_trust(p)
        peer = [pr for pr in result.proofs if pr.proof_type == "peer"][0]
        assert peer.beta == 0.0
        assert peer.q == 0.0

    def test_synthetic_risk_penalises(self):
        p = _base_profile()
        clean = ts.compute_trust(p).trust_final
        p["provenance"]["risk"]["synthetic_risk"] = 0.5
        risky = ts.compute_trust(p).trust_final
        assert risky < clean
        assert abs(risky - clean * 0.5) < 1e-6

    def test_drift_reduces_via_witness(self):
        p = _base_profile()
        no_drift = ts.compute_trust(p).trust_final
        p["provenance"]["temporal_stewardship"]["drift_score"] = 0.5
        drifted = ts.compute_trust(p).trust_final
        assert drifted < no_drift

    def test_pq_and_hardware_reach_high_tiers(self):
        p = _base_profile()
        p["provenance"]["identity_roots"]["pq_public_key"] = "pq_pk"
        p["provenance"]["identity_roots"]["hardware_key_id"] = "hw_1"
        # Add two fresh institutional + cryptographic attestations.
        p["provenance"]["attestations"] = [
            {**_peer_attestation(created_days_ago=1), "type": "institutional"},
            {**_peer_attestation(created_days_ago=1), "type": "cryptographic"},
        ]
        result = ts.compute_trust(p)
        assert result.tier in ("T3", "T4", "T5")

    def test_tier_at_least_helper(self):
        p = _base_profile()
        p["provenance"]["attestations"] = [
            {**_peer_attestation(created_days_ago=1), "type": "institutional"},
        ]
        assert ts.tier_at_least(p, "T1") is True
        assert ts.tier_at_least(p, "T5") is False


# ---------------------------------------------------------------------------
# governance: init + ownership
# ---------------------------------------------------------------------------

class TestGovernanceInit:
    def test_init_sets_owner_and_defaults(self):
        p = _base_profile()
        g = gov.init_governance(p)
        assert g["ownership"]["owner_did"] == "did:ucs:abc123"
        assert g["lifecycle_state"] == "active"
        assert g["posthumous"]["mode"] == "dormant"
        assert g["version"] == gov.GOVERNANCE_VERSION

    def test_init_is_idempotent(self):
        p = _base_profile()
        gov.init_governance(p)
        n_events = len(p["governance"]["event_log"])
        gov.init_governance(p)
        assert len(p["governance"]["event_log"]) == n_events

    def test_event_chain_valid_after_ops(self):
        p = _base_profile()
        gov.init_governance(p)
        gov.add_controller(p, "did:ucs:abc123", "did:ucs:ctrl",
                           role="executor", scopes=["lifecycle", "admin"])
        assert gov.verify_event_chain(p) is True

    def test_tampered_chain_detected(self):
        p = _base_profile()
        gov.init_governance(p)
        gov.add_controller(p, "did:ucs:abc123", "did:ucs:ctrl",
                           role="executor", scopes=["admin"])
        # Tamper with an earlier event.
        p["governance"]["event_log"][0]["detail"]["owner_did"] = "did:ucs:evil"
        assert gov.verify_event_chain(p) is False

    def test_non_owner_cannot_add_controller(self):
        p = _base_profile()
        gov.init_governance(p)
        with pytest.raises(gov.GovernanceError):
            gov.add_controller(p, "did:ucs:notowner", "did:ucs:x",
                               role="r", scopes=["admin"])

    def test_ownership_transfer_locked_by_default(self):
        p = _base_profile()
        gov.init_governance(p)
        with pytest.raises(gov.GovernanceError):
            gov.transfer_ownership(p, "did:ucs:abc123", "did:ucs:new")

    def test_ownership_transfer_with_unlock(self):
        p = _base_profile()
        gov.init_governance(p)
        gov.transfer_ownership(p, "did:ucs:abc123", "did:ucs:new",
                               unlock_token="ok")
        assert p["governance"]["ownership"]["owner_did"] == "did:ucs:new"


# ---------------------------------------------------------------------------
# governance: posthumous gate (the ethically loaded path)
# ---------------------------------------------------------------------------

class TestPosthumous:
    def _make_inheritable(self, p, successor="did:ucs:heir"):
        p["inheritance"] = {"inheritable": True, "successor_id": successor,
                            "release_condition": "post_mortem"}

    def test_default_posthumous_is_dormant(self):
        p = _base_profile()
        gov.init_governance(p)
        gov.add_controller(p, "did:ucs:abc123", "did:ucs:exec",
                           role="executor", scopes=["lifecycle"])
        gov.assert_death(p, "did:ucs:exec")
        mode = gov.confirm_posthumous(p, "did:ucs:exec", "dormant")
        assert mode == gov.PosthumousMode.DORMANT

    def test_memorial_requires_inheritable(self):
        p = _base_profile()
        gov.init_governance(p)
        gov.add_controller(p, "did:ucs:abc123", "did:ucs:exec",
                           role="executor", scopes=["lifecycle"])
        gov.assert_death(p, "did:ucs:exec")
        # No inheritance set -> request memorial -> downgraded to dormant.
        mode = gov.confirm_posthumous(p, "did:ucs:exec", "memorial")
        assert mode == gov.PosthumousMode.DORMANT

    def test_memorial_granted_when_inheritable(self):
        p = _base_profile()
        self._make_inheritable(p)
        gov.init_governance(p)
        gov.add_controller(p, "did:ucs:abc123", "did:ucs:exec",
                           role="executor", scopes=["lifecycle"])
        gov.assert_death(p, "did:ucs:exec")
        mode = gov.confirm_posthumous(p, "did:ucs:exec", "memorial")
        assert mode == gov.PosthumousMode.MEMORIAL

    def test_active_denied_without_directive(self):
        p = _base_profile()
        self._make_inheritable(p)
        # Strong trust so the only blocker is the missing directive.
        p["provenance"]["attestations"] = [
            {**_peer_attestation(created_days_ago=1), "type": "institutional"},
        ]
        gov.init_governance(p)
        gov.add_controller(p, "did:ucs:abc123", "did:ucs:exec",
                           role="executor", scopes=["lifecycle"])
        gov.assert_death(p, "did:ucs:exec")
        mode = gov.confirm_posthumous(p, "did:ucs:exec", "active")
        # Downgraded to memorial because no signed directive.
        assert mode == gov.PosthumousMode.MEMORIAL

    def test_active_granted_with_directive_and_tier(self):
        p = _base_profile()
        self._make_inheritable(p)
        p["provenance"]["attestations"] = [
            {**_peer_attestation(created_days_ago=1), "type": "institutional"},
        ]
        gov.init_governance(p)
        gov.register_posthumous_directive(
            p, "did:ucs:abc123",
            {"requested_mode": "active", "text": "I consent to active operation."})
        gov.add_controller(p, "did:ucs:abc123", "did:ucs:exec",
                           role="executor", scopes=["lifecycle"])
        gov.assert_death(p, "did:ucs:exec")
        mode = gov.confirm_posthumous(p, "did:ucs:exec", "active")
        assert mode == gov.PosthumousMode.ACTIVE

    def test_active_denied_below_tier_even_with_directive(self):
        p = _base_profile()
        # Self-claimed only -> T0, below T2.
        p["provenance"]["identity_roots"]["classical_public_key"] = None
        self._make_inheritable(p)
        gov.init_governance(p)
        gov.register_posthumous_directive(
            p, "did:ucs:abc123", {"requested_mode": "active"})
        gov.add_controller(p, "did:ucs:abc123", "did:ucs:exec",
                           role="executor", scopes=["lifecycle"])
        gov.assert_death(p, "did:ucs:exec")
        mode = gov.confirm_posthumous(p, "did:ucs:exec", "active")
        assert mode == gov.PosthumousMode.MEMORIAL  # downgraded

    def test_objector_forces_dormant(self):
        p = _base_profile()
        self._make_inheritable(p)
        p["provenance"]["attestations"] = [
            {**_peer_attestation(created_days_ago=1), "type": "institutional"},
        ]
        gov.init_governance(p)
        gov.register_posthumous_directive(
            p, "did:ucs:abc123", {"requested_mode": "active"})
        gov.add_objector(p, "did:ucs:family", relationship="spouse")
        gov.add_controller(p, "did:ucs:abc123", "did:ucs:exec",
                           role="executor", scopes=["lifecycle"])
        gov.assert_death(p, "did:ucs:exec")
        mode = gov.confirm_posthumous(p, "did:ucs:exec", "active")
        assert mode == gov.PosthumousMode.DORMANT

    def test_late_objector_freezes_active_echo(self):
        p = _base_profile()
        self._make_inheritable(p)
        p["provenance"]["attestations"] = [
            {**_peer_attestation(created_days_ago=1), "type": "institutional"},
        ]
        gov.init_governance(p)
        gov.register_posthumous_directive(
            p, "did:ucs:abc123", {"requested_mode": "active"})
        gov.add_controller(p, "did:ucs:abc123", "did:ucs:exec",
                           role="executor", scopes=["lifecycle"])
        gov.assert_death(p, "did:ucs:exec")
        gov.confirm_posthumous(p, "did:ucs:exec", "active")
        assert p["governance"]["posthumous"]["mode"] == "active"
        gov.add_objector(p, "did:ucs:family")
        assert p["governance"]["posthumous"]["mode"] == "dormant"

    def test_disclosure_label_required_for_memorial(self):
        p = _base_profile()
        self._make_inheritable(p)
        gov.init_governance(p)
        p["governance"]["ownership"]["owner_label"] = "Jane Doe"
        gov.add_controller(p, "did:ucs:abc123", "did:ucs:exec",
                           role="executor", scopes=["lifecycle"])
        gov.assert_death(p, "did:ucs:exec")
        gov.confirm_posthumous(p, "did:ucs:exec", "memorial")
        label = gov.disclosure_label(p)
        assert label is not None
        assert "posthumously" in label
        assert "Jane Doe" in label

    def test_death_must_be_asserted_before_confirm(self):
        p = _base_profile()
        gov.init_governance(p)
        gov.add_controller(p, "did:ucs:abc123", "did:ucs:exec",
                           role="executor", scopes=["lifecycle"])
        with pytest.raises(gov.GovernanceError):
            gov.confirm_posthumous(p, "did:ucs:exec", "memorial")


# ---------------------------------------------------------------------------
# governance: deletion
# ---------------------------------------------------------------------------

class TestDeletion:
    def test_soft_delete_is_reversible(self):
        p = _base_profile()
        gov.init_governance(p)
        r = gov.request_deletion(p, "did:ucs:abc123", mode="soft")
        assert r["status"] == "soft_pending"
        assert p["governance"]["lifecycle_state"] == "suspended"
        gov.cancel_soft_deletion(p, "did:ucs:abc123")
        assert p["governance"]["lifecycle_state"] == "active"

    def test_hard_delete_erases_content_keeps_log(self):
        p = _base_profile()
        gov.init_governance(p)
        r = gov.request_deletion(p, "did:ucs:abc123", mode="hard")
        assert r["status"] == "deleted"
        assert p["persona"] is None
        assert p["expertise_map"] is None
        assert len(p["governance"]["event_log"]) > 0  # log retained
        assert "tombstone" in p["governance"]["deletion"]

    def test_purge_removes_event_log(self):
        p = _base_profile()
        gov.init_governance(p)
        gov.request_deletion(p, "did:ucs:abc123", mode="purge")
        assert p["governance"]["event_log"] == []
        assert p["governance"]["deletion"]["tombstone"]["purged"] is True

    def test_purge_denied_for_nonowner_without_legal_order(self):
        p = _base_profile()
        gov.init_governance(p)
        gov.add_controller(p, "did:ucs:abc123", "did:ucs:ctrl",
                           role="custodian", scopes=["delete"])
        with pytest.raises(gov.GovernanceError):
            gov.request_deletion(p, "did:ucs:ctrl", mode="purge")

    def test_purge_allowed_with_legal_order(self):
        p = _base_profile()
        gov.init_governance(p)
        gov.add_controller(p, "did:ucs:abc123", "did:ucs:ctrl",
                           role="custodian", scopes=["delete"])
        r = gov.request_deletion(p, "did:ucs:ctrl", mode="purge",
                                 reason="legal_order")
        assert r["status"] == "deleted"

    def test_delete_requires_scope(self):
        p = _base_profile()
        gov.init_governance(p)
        gov.add_controller(p, "did:ucs:abc123", "did:ucs:ctrl",
                           role="viewer", scopes=["infer"])
        with pytest.raises(gov.GovernanceError):
            gov.request_deletion(p, "did:ucs:ctrl", mode="soft")


# ---------------------------------------------------------------------------
# governance: disputes
# ---------------------------------------------------------------------------

class TestDisputes:
    def test_file_dispute_does_not_freeze(self):
        p = _base_profile()
        gov.init_governance(p)
        d = gov.file_dispute(p, "did:ucs:claim", "impersonation",
                             "This Echo is not who it claims.")
        assert d["state"] == "open"
        assert p["governance"]["lifecycle_state"] == "active"

    def test_escalation_freezes(self):
        p = _base_profile()
        gov.init_governance(p)
        d = gov.file_dispute(p, "did:ucs:claim", "ownership", "Mine.")
        gov.escalate_dispute(p, "did:ucs:admin", d["id"], freeze=True)
        assert p["governance"]["lifecycle_state"] == "suspended"

    def test_resolution_unfreezes(self):
        p = _base_profile()
        gov.init_governance(p)
        d = gov.file_dispute(p, "did:ucs:claim", "ownership", "Mine.")
        gov.escalate_dispute(p, "did:ucs:admin", d["id"], freeze=True)
        gov.resolve_dispute(p, "did:ucs:admin", d["id"], upheld=False,
                            resolution_note="Insufficient evidence.")
        assert p["governance"]["lifecycle_state"] == "active"

    def test_two_disputes_one_resolved_stays_frozen(self):
        p = _base_profile()
        gov.init_governance(p)
        d1 = gov.file_dispute(p, "did:ucs:a", "ownership", "1")
        d2 = gov.file_dispute(p, "did:ucs:b", "accuracy", "2")
        gov.escalate_dispute(p, "did:ucs:admin", d1["id"], freeze=True)
        gov.escalate_dispute(p, "did:ucs:admin", d2["id"], freeze=True)
        gov.resolve_dispute(p, "did:ucs:admin", d1["id"], upheld=True, resolution_note="ok")
        assert p["governance"]["lifecycle_state"] == "suspended"


# ---------------------------------------------------------------------------
# governance: the central gate
# ---------------------------------------------------------------------------

class TestGate:
    def test_active_allows_all(self):
        p = _base_profile()
        gov.init_governance(p)
        assert gov.can_operate(p, "infer")["allowed"] is True
        assert gov.can_operate(p, "transact")["allowed"] is True

    def test_suspended_allows_only_admin(self):
        p = _base_profile()
        gov.init_governance(p)
        gov.request_deletion(p, "did:ucs:abc123", mode="soft")
        assert gov.can_operate(p, "infer")["allowed"] is False
        assert gov.can_operate(p, "admin")["allowed"] is True

    def test_memorial_allows_infer_not_transact(self):
        p = _base_profile()
        p["inheritance"] = {"inheritable": True, "successor_id": "did:ucs:heir"}
        gov.init_governance(p)
        p["governance"]["retire_on_death"] = False  # Stage 6 path — bypass v1 gate
        gov.add_controller(p, "did:ucs:abc123", "did:ucs:exec",
                           role="executor", scopes=["lifecycle"])
        gov.assert_death(p, "did:ucs:exec")
        gov.confirm_posthumous(p, "did:ucs:exec", "memorial")
        assert gov.can_operate(p, "infer")["allowed"] is True
        assert gov.can_operate(p, "transact")["allowed"] is False
        assert gov.can_operate(p, "infer")["disclosure"] is not None

    def test_deleted_blocks_everything(self):
        p = _base_profile()
        gov.init_governance(p)
        gov.request_deletion(p, "did:ucs:abc123", mode="hard")
        assert gov.can_operate(p, "admin")["allowed"] is False
        assert gov.can_operate(p, "infer")["allowed"] is False


# ---------------------------------------------------------------------------
# governance: retire_on_death (v1 release policy)
# ---------------------------------------------------------------------------

class TestRetireOnDeath:
    def _with_exec(self, p):
        gov.init_governance(p)
        gov.add_controller(p, "did:ucs:abc123", "did:ucs:exec",
                           role="executor", scopes=["lifecycle"])
        return p

    def test_retire_echo_moves_to_posthumous_dormant(self):
        p = _base_profile()
        self._with_exec(p)
        gov.retire_echo(p, "did:ucs:exec", evidence_ref="cert-001")
        assert p["governance"]["lifecycle_state"] == "posthumous"
        assert p["governance"]["posthumous"]["mode"] == "dormant"

    def test_retired_echo_blocks_infer_and_transact(self):
        p = _base_profile()
        self._with_exec(p)
        gov.retire_echo(p, "did:ucs:exec")
        for action in ("infer", "transact"):
            r = gov.can_operate(p, action)
            assert r["allowed"] is False, f"{action} should be blocked"
            assert r["reason"] == "echo_retired_admin_only"

    def test_retired_echo_allows_admin(self):
        p = _base_profile()
        self._with_exec(p)
        gov.retire_echo(p, "did:ucs:exec")
        r = gov.can_operate(p, "admin")
        assert r["allowed"] is True

    def test_retire_is_one_way(self):
        p = _base_profile()
        self._with_exec(p)
        gov.retire_echo(p, "did:ucs:exec")
        with pytest.raises(gov.GovernanceError):
            gov.retire_echo(p, "did:ucs:exec")

    def test_retire_requires_lifecycle_scope(self):
        p = _base_profile()
        gov.init_governance(p)
        gov.add_controller(p, "did:ucs:abc123", "did:ucs:viewer",
                           role="viewer", scopes=["infer"])
        with pytest.raises(gov.GovernanceError):
            gov.retire_echo(p, "did:ucs:viewer")

    def test_retire_on_death_false_restores_stage6_paths(self):
        """When retire_on_death is explicitly False, Stage 6 modal paths apply."""
        p = _base_profile()
        p["inheritance"] = {"inheritable": True, "successor_id": "did:ucs:heir"}
        gov.init_governance(p)
        p["governance"]["retire_on_death"] = False   # Stage 6 unlock
        gov.add_controller(p, "did:ucs:abc123", "did:ucs:exec",
                           role="executor", scopes=["lifecycle"])
        gov.assert_death(p, "did:ucs:exec")
        gov.confirm_posthumous(p, "did:ucs:exec", "memorial")
        r = gov.can_operate(p, "infer")
        assert r["allowed"] is True
        assert r["disclosure"] is not None

    def test_event_chain_valid_after_retirement(self):
        p = _base_profile()
        self._with_exec(p)
        gov.retire_echo(p, "did:ucs:exec", evidence_ref="cert-001")
        assert gov.verify_event_chain(p) is True

    def test_retired_echo_can_be_hard_deleted(self):
        """Retirement doesn't block the owner from erasing content."""
        p = _base_profile()
        self._with_exec(p)
        gov.retire_echo(p, "did:ucs:exec")
        # owner still has delete scope (is the owner)
        r = gov.request_deletion(p, "did:ucs:abc123", mode="hard")
        assert r["status"] == "deleted"


class TestCaptureProfileIntegration:
    """Governance auto-attach via capture_profile.build_profile flow."""

    def test_governance_auto_attached_on_profile_creation(self):
        import sys
        sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
        from capture_profile import build_profile, validate_profile
        from governance import init_governance, can_operate

        answers = {
            "name": "Integration Test Echo",
            "bio": "Test bio.",
            "domains": ["testing"],
            "communication_style": "direct",
            "formality": "neutral",
            "verbosity": "moderate",
            "tone_markers": ["precise", "clear"],
            "prefers_tables": False,
            "prefers_bullets": False,
            "expertise_map": {},
            "trust_boundaries": {},
        }
        profile = build_profile(answers)
        assert not validate_profile(profile)

        # Simulate what main() now does automatically
        init_governance(profile)

        gov = profile.get("governance", {})
        assert gov.get("version") == "1.0"
        assert gov.get("lifecycle_state") == "active"
        assert gov.get("retire_on_death") is True
        assert gov["ownership"]["owner_did"] is None  # no DID without trust fabric

    def test_governance_owner_set_from_did_when_trust_fabric_present(self):
        import sys
        sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
        from governance import init_governance, can_operate

        profile = {"did": "did:ucs:testecho123", "persona": {"summary": "test"}}
        init_governance(profile)

        gov = profile["governance"]
        assert gov["ownership"]["owner_did"] == "did:ucs:testecho123"
        assert can_operate(profile, "infer")["allowed"] is True
