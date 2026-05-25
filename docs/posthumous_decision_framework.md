# Posthumous Use — Decision Framework

**Status:** Open — to be resolved before Stage 6 (Inheritance Lite)
**Owner:** Roshan George Thomas
**Last updated:** 2026-05-25

---

## Why this document exists

For the first EchoNet release, all Echoes retire on death (`retire_on_death = True`
in the governance block). The runtime enforces this; no posthumous operation is
reachable by code.

Before Stage 6 ships, the `retire_on_death` flag must be deliberately set to
`False`, and the MEMORIAL and ACTIVE posthumous paths that are already coded must
be assigned real policy. This document captures the decisions that need to be
made — not what those decisions should be.

The right answers will come from the first Echo candidates: what they are
actually afraid of, who they would trust to steward their identity, and what
"operating after death" would mean to someone who knows them.

---

## The three questions

### 1. Whose yes is required before a dead person's Echo can transact?

"Transact" means: earn revenue, represent the person in a new context, make
statements attributed to them, be deployed by a third party.

**Option A — The dead person's, given while alive.**
The Echo cannot transact posthumously unless the principal signed a directive
before death. A directive is a signed JSON record (`register_posthumous_directive`)
tied to the principal's DID and key. If there is no directive, the Echo cannot
be set to ACTIVE — it stays at MEMORIAL (read-only) or DORMANT.

*The case for A:* The one party who can no longer object is the deceased. An
EchoNet Echo earns money and makes claims. The successor's interest and the
deceased's intent can diverge — commercially, legally, emotionally. Pre-mortem
consent is the only consent that's unambiguous.

*The case against A:* High friction. Most people will not fill in a form about
their death while alive. This could make the ACTIVE path practically unreachable
for most users.

**Option B — The family/heir's is enough.**
A designated successor can activate the Echo (including transacting) without a
pre-mortem directive from the principal. The heir inherits the right to operate
it, as with any other estate asset.

*The case for B:* Lower friction, culturally familiar (estate law), respects the
family's judgment. Aligns with how most inheritance works.

*The case against B:* Heir and deceased may have had different wishes. The deceased
cannot correct a misrepresentation. Creates regulatory exposure in jurisdictions
with post-mortem personality/publicity rights (California, Germany, others).

**Option C — Heir's yes, but with a minimum trust tier and a standing veto.**
The heir can activate, but only if the profile was verified to a real tier (≥ T2)
before death, a disclosure label is mandatory, and any named objector can force
DORMANT at any time. The deceased does not need a directive, but the *system*
requires that identity was real.

*The case for C:* Balances access with accountability. Makes it harder to
posthumously operate a low-quality or unverified Echo commercially. Objector veto
gives family members a brake without requiring legal action.

---

### 2. What should the minimum trust tier be for any posthumous operation?

The trust tier is computed at the time of death from the profile's provenance —
attestations, key anchors, drift score. It is not re-verified after death.

| Tier | Meaning | Implication for posthumous use |
|---|---|---|
| T0 (< 0.25) | Self-claimed only — no external verification | Allowing posthumous operation of an unverified identity is the highest impersonation risk. Should T0 Echoes be eligible for any posthumous mode? |
| T1 (0.25–0.50) | At least one named peer has signed | Low bar — a friend's attestation. |
| T2 (0.50–0.75) | Institutionally verified (LinkedIn, credential authority, ID) | The current coded default for ACTIVE. |
| T3+ (> 0.75) | Cryptographically anchored or better | Highest confidence the Echo was a real, verified person. |

**Decision needed:** What is the minimum tier for MEMORIAL? For ACTIVE?
Current code defaults: MEMORIAL has no tier floor; ACTIVE requires ≥ T2.

---

### 3. Who can object, and what does an objection do?

An objector is a named DID registered in `posthumous.objectors`. Currently:
- Any objector forces DORMANT immediately, even overriding an explicit directive.
- An objector added after activation immediately re-freezes the Echo.
- Objection grants no operating rights to the objector — it is only a brake.

**Decision needed:**

- Who should be eligible to register as an objector? (Anyone? Named relationships
  only? Only people the principal pre-registered?)
- Should an objection be permanent, or subject to a dispute/review process?
  (Currently: permanent and immediate. An objector could be a bad-faith actor.)
- Should an objector be able to force DORMANT even when the principal left a
  signed directive explicitly consenting to ACTIVE? (Currently: yes, objector
  always wins. This may be too strong if the deceased's explicit wish is
  overridden by a single family member.)

---

## Recommended sequence before Stage 6

1. **Talk to the first three Echo candidates** about death and their Echo.
   Ask: "If you died tomorrow, what should happen to it? Who would you trust?
   What would you be afraid of?" Do not lead with the options above.

2. **Talk to at least one lawyer** in a relevant jurisdiction (UAE, GCC, or
   wherever the first live users are) about post-mortem personality rights and
   what a "posthumous use directive" needs to look like to have any standing.

3. **Write a one-page policy** answering questions 1–3 above, and get the first
   Echo candidate to read and sign off on it before their Echo goes live.
   That policy becomes the `posthumous_consent_policy_v1.md` that RFC-0004 §14
   says is open work.

4. **Set `retire_on_death = False`** in a staging environment only, confirm
   Stage 6 mechanics work end-to-end, then release with the resolved policy.

---

## What is already built and will not change

Regardless of how questions 1–3 are answered:

- The MEMORIAL path (read-only, non-transacting, with a mandatory disclosure
  label) exists in code and is stable. It is the safe floor for any posthumous
  continuation.
- The objector veto mechanism exists. The *threshold* for who qualifies is the
  policy question; the *mechanism* is wired.
- The audit log is tamper-evident and logs every state transition. A dispute
  over posthumous use can be reconstructed in full.
- The disclosure label is hard-wired to any non-DORMANT posthumous state. It
  cannot be disabled by the governance block — only the label text is
  configurable.

---

*This document should be replaced by `posthumous_consent_policy_v1.md` before
Stage 6 ships. Until then, `retire_on_death = True` and this file is the
outstanding design debt.*
