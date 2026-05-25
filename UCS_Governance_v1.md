# UCS Governance v1

> Open policy specification for ownership, lifecycle, posthumous use, and dispute
> resolution of portable cognitive profiles.

---

## 1. Purpose

The Trust Fabric (v3) answers *"is this profile under the same human control over
time?"* Governance v1 answers the questions that follow once the answer is yes
and the profile becomes valuable: **who controls it, how it ends, what happens
after death, and what happens when people disagree about it.**

Governance is a **witness and a gate, not an owner.** It records facts, evaluates
permissions, and emits an auditable decision. It never silently rewrites a
person's cognitive content.

---

## 2. Where Governance Sits

```
┌──────────────────────────────────────────────────────────┐
│  EchoNet runtime / Jarvis / external integrators          │
│                  │  asks one question                      │
│                  ▼                                          │
│        can_operate(profile, action) ──► allow? + disclosure │
└──────────────────────────────────────────────────────────┘
                   │ reads
   ┌───────────────┼───────────────────────────────┐
   ▼               ▼                                 ▼
governance     trust_score                      provenance
(this doc)     (tiers T0–T5)                    (RFC-0003)
ownership      ↑ gates posthumous "active"      keys, attestations
lifecycle      on tier ≥ T2                     drift, risk
disputes
posthumous
```

Governance v1 is **additive**. It does not modify `provenance`,
`trust_boundaries`, or `inheritance`. It reads the trust tier from
`trust_score.py` and the inheritance intent from the existing `inheritance`
field.

---

## 3. The Five Lifecycle States

| State | One-line meaning | `infer` | `transact` | `admin` |
|---|---|:--:|:--:|:--:|
| `active` | Living principal in control | ✅ | ✅ | ✅ |
| `suspended` | Frozen (pending delete / dispute) | ❌ | ❌ | ✅ |
| `deceased_pending` | Death asserted, not confirmed | ❌ | ❌ | ✅ |
| `posthumous` | Death confirmed — mode governs | mode | mode | ✅ |
| `deleted` | Tombstoned, content erased | ❌ | ❌ | ❌ |

Death assertion and death confirmation are **two separate steps** by design.
A single false assertion cannot move a living person's Echo into posthumous use.

---

## 4. Ownership Model

- The **principal owns by default.**
- The owner can appoint **controllers** with explicit **scopes**:
  - `lifecycle` — assert/confirm death, manage posthumous mode
  - `delete` — request deletion
  - `admin` — export, manage, operate under suspension
  - `infer` — read-only operation
  - `*` — all scopes
- Controllers act on the owner's behalf **within their scopes** and can never
  change ownership.
- **Ownership transfer is locked by default.** Unlocking requires the current
  owner and an explicit token, and is forbidden while suspended or posthumous.

Example — appointing a digital executor:

```python
add_controller(profile, actor_did=owner,
               controller_did="did:ucs:executor",
               role="executor", scopes=["lifecycle"])
```

---

## 5. Posthumous Use — three modes

This is the ethically loaded surface of the system, because an EchoNet Echo can
earn revenue and make representations. The party who can no longer object — the
deceased — must opt in **explicitly** before the commercial path opens.

| Mode | What it can do | What it needs |
|---|---|---|
| **Dormant** *(default)* | Nothing. Administer-only. | Nothing. This is the floor. |
| **Memorial** | Answer (read-only). **Cannot transact.** Carries a disclosure label. Successor-revocable. | `inheritable = true` + a named successor. |
| **Active** | Transact and make new representations. | Everything Memorial needs **+** a signed pre-mortem directive **+** trust tier ≥ T2 at death. |

### Resolution logic

1. **Objector present → Dormant.** A named objector (e.g. a spouse) can force
   Dormant, overriding any directive. Objection is a brake, never a claim to
   operate the Echo themselves.
2. **Memorial without inheritability → downgraded to Dormant.**
3. **Active without a directive, or below T2 → downgraded to Memorial** (not
   denied — the principal's wish to leave something behind is honoured at the
   safe level).
4. **Objection after activation → immediate re-freeze to Dormant.**

### The disclosure label

Every Memorial or Active Echo surfaces:

> *This Echo operates posthumously and does not represent the live intentions of
> {name}. Mode: {memorial|active}.*

This is a hard requirement, not a courtesy. It is the engineering control that
addresses impersonation/deception concerns; it is **not** a substitute for
jurisdiction-specific legal review (post-mortem publicity rights differ widely).

### Worked example

```python
# Principal, while alive, records consent:
register_posthumous_directive(profile, owner,
    {"requested_mode": "active", "text": "I consent to active operation."})
profile["inheritance"] = {"inheritable": True, "successor_id": "did:ucs:heir"}

# Later, the executor handles the estate:
assert_death(profile, executor_did, evidence_ref="death-cert-ref")
mode = confirm_posthumous(profile, executor_did, requested_mode="active")
# → ACTIVE only if tier ≥ T2 and the directive is present; else MEMORIAL.
```

---

## 6. Deletion

| Mode | Reversible? | Keeps audit log? | Who can |
|---|:--:|:--:|---|
| **Soft** | ✅ within grace window (default 30 days) | ✅ | `delete` scope |
| **Hard** | ❌ | ✅ (tombstone + log) | `delete` scope |
| **Purge** | ❌ | ❌ (minimal tombstone only) | owner, or `legal_order` |

Hard deletion erases cognitive content (`persona`, `expertise_map`,
`project_graph`, `preference_corpus`, `interaction_patterns`, …) but keeps
identity roots and a tombstone, so a deleted DID can't be silently re-registered
as if brand new. Purge is the regulatory "right to erasure" path and removes even
the audit log.

---

## 7. Disputes

Categories: `impersonation`, `ownership`, `accuracy`, `posthumous_objection`,
`data_rights`, `other`.

```
file ─► open ─► escalate ─► under_review ─► resolve ─► upheld / rejected
                                          └────────► withdrawn
```

- **Filing** does not freeze the profile — frivolous claims can't weaponise
  suspension.
- **Escalation** can suspend the profile while it is adjudicated.
- **Resolution** unfreezes only if no other escalated dispute still holds the
  freeze.

---

## 8. Tamper-Evident Audit Log

Every transition appends a hash-chained event:

```
event_n.prev_event_hash = SHA3-512(canonical_json(event_{n-1}))
```

`verify_event_chain(profile)` detects any retroactive edit. This is what lets a
dispute be reconstructed months later and lets an integrator prove the
governance history wasn't altered.

---

## 9. The One Function That Matters

```python
decision = can_operate(profile, action="transact")
# {"allowed": False, "reason": "posthumous_memorial_readonly",
#  "disclosure": "This Echo operates posthumously …", "state": "posthumous"}
```

Everything in this document collapses into this single call. EchoNet, Jarvis, and
external developers enforce governance by asking it before every operation and
honouring the returned `disclosure` label.

---

## 10. Quick Start

```bash
# Attach a default governance block (owner = profile DID)
python governance.py init --profile echo.json --out echo.json

# Check whether the Echo may transact right now
python governance.py status --profile echo.json --action transact

# Verify the audit chain has not been tampered with
python governance.py verify --profile echo.json

# Compute the trust tier the posthumous "active" gate depends on
python trust_score.py --profile echo.json
```

---

## 11. What v1 Does NOT Do

- It does not **execute** inheritance (operating a successor Echo) — that is
  Stage 6.
- It does not **verify** the directive's signature yet — it trusts upstream
  signing and stores the hash (Stage 3.1).
- It does not provide a **distributed revocation registry** — the pointer is
  defined, resolution is future work.
- It is not **legal advice** or a legally binding instrument. It is an
  engineering control layer that makes legal compliance *possible*, not
  automatic.

Acceptable language: *witness, gate, revocable, tamper-evident, fail-closed.*
Not acceptable: *legally binding, permanent ownership, guaranteed consent,
immune to disputes.*

---

## 12. Related Documents

| Document | Location |
|---|---|
| RFC-0004 — Governance v1 RFC | `rfcs/RFC-0004.md` |
| Trust Fabric v3 spec | `docs/UCS_Trust_Fabric_v3.md` |
| Trust score engine | `trust_score.py` |
| Governance engine + CLI | `governance.py` |
| Governance tests | `tests/test_governance.py` |
| Roadmap (Stage 3) | `universal_cognitive_schema_roadmap.md` |

---

## 13. Revision History

| Version | Date | Change |
|---|---|---|
| v1.0 | 2026-05-25 | Initial Governance v1 specification. |
