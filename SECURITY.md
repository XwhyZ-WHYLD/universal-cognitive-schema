# Security Policy

Universal Cognitive Schema handles some of the most sensitive personal data that exists — a structured representation of how a person thinks, communicates, and works. This document explains our security commitments, what we expect from implementations, and how to report vulnerabilities.

---

## Our core security commitment

**We are architecturally incapable of reading your cognitive profile.**

This is not a policy promise. It is a design requirement. Any UCS-compliant implementation must be built so that no central party — including the authors of this standard — ever holds a decrypted cognitive profile without the explicit, per-session consent of the profile owner.

If an implementation cannot make this guarantee, it is not UCS-compliant.

---

## Zero-knowledge architecture requirements

All UCS-compliant tools and platforms must adhere to the following:

### Encryption
- Profiles must be encrypted at rest using AES-256 or equivalent
- Profiles must be encrypted in transit using TLS 1.3 or higher
- Encryption and decryption must occur on the user's device, not on a server
- Encryption keys must never be transmitted to or stored by a third party

### Storage
- No UCS implementation may store a decrypted profile on a server it controls
- Profile storage must be under the direct control of the profile owner — on their device, in their chosen cloud storage, or in their enterprise vault
- Implementations act as routing and translation layers only — not data warehouses

### Transmission
- A profile may only be transmitted to a destination platform with explicit, per-dimension user consent
- Consent must be granted immediately before each transmission — not stored as a blanket permission
- Implementations must transmit only the dimensions the user has chosen to share, never the full profile by default

### Sanitisation
- Every profile must pass sanitisation before the `provenance.sanitised` field is set to `true`
- Sanitisation must strip: prompt-injection patterns, executable instructions, role-override syntax, and any content designed to manipulate a destination model's behaviour
- The `sanitised_at` timestamp must reflect when sanitisation actually occurred
- Setting `sanitised: true` without running sanitisation is a critical violation of this standard

---

## Sensitive data classification

Cognitive profiles are classified as **highly sensitive personal data** — equivalent to biometric or medical data in terms of the potential for harm if compromised.

A cognitive profile breach does not just expose names and email addresses. It exposes:
- Communication patterns and psychological tendencies
- Professional expertise and knowledge gaps
- Project history and business context
- Decision-making frameworks and risk tolerances
- Trust boundaries and autonomy preferences

Treat cognitive profile data accordingly in every implementation decision.

---

## Supported versions

| Version | Supported |
|---|---|
| 0.1.0-alpha | ✓ Active |

As the standard is in alpha, all security fixes apply to the current version only. Once v1.0.0 is released, a formal long-term support policy will be defined.

---

## Reporting a vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

If you discover a vulnerability in the UCS schema specification, a reference implementation, or any official tooling in this repository, report it privately so it can be addressed before public disclosure.

### How to report

**Email:** security@ucs-standard.org

Include in your report:
- A clear description of the vulnerability
- The component affected (schema spec, parser, validator, documentation)
- Steps to reproduce or a proof of concept
- The potential impact if exploited
- Your suggested fix, if you have one

### What to expect

| Timeframe | What happens |
|---|---|
| Within 48 hours | Acknowledgement of your report |
| Within 7 days | Initial assessment and severity classification |
| Within 30 days | Fix developed and tested |
| Within 45 days | Fix released and vulnerability disclosed publicly |

We will credit you in the security advisory unless you request otherwise.

We will not take legal action against researchers who report vulnerabilities in good faith and follow this policy.

---

## Known threat model

Building on UCS means building on a system that handles sensitive data at scale. The following threats are explicitly part of our threat model — implementations must account for all of them.

### Poisoned profile attack
A malicious actor crafts conversations designed to embed prompt-injection payloads into a platform's memory export. When the user migrates this profile, the injected instructions execute on the destination platform.

**Mitigation required:** Sanitisation layer that detects and strips instruction-like content from all profile fields before storage or transmission.

### Profile theft and impersonation
A stolen cognitive profile can be used to impersonate the profile owner with high fidelity — generating communications, making decisions, or manipulating AI agents in their name.

**Mitigation required:** Biometric or strong second-factor binding at profile creation. Usage anomaly detection. Cryptographic provenance chain on every profile use.

### Man-in-the-middle profile manipulation
An attacker intercepts a profile in transit and modifies dimensions before it reaches the destination platform — altering trust boundaries, injecting false expertise, or changing communication preferences to manipulate the AI's behaviour toward the user.

**Mitigation required:** End-to-end encryption with integrity verification. TLS 1.3 minimum. Profile hash verification at destination before injection.

### Centralisation attack
A UCS implementation that centralises decrypted profiles becomes the highest-value target in the AI identity ecosystem. A single breach could expose the cognitive profiles of millions of people simultaneously.

**Mitigation required:** Federated, user-controlled storage. No central decryption. Zero-knowledge routing architecture.

### Scope creep by destination platforms
A destination platform receives a cognitive profile for personalisation but uses it for manipulation, profiling, advertising targeting, or training data without the user's knowledge.

**Mitigation required:** Binding platform usage agreements as a condition of API access. Selective disclosure so users control which dimensions travel to which platform. Audit logging of profile access at the platform level.

---

## Security requirements for contributors

If you are contributing a parser, validator, or other tooling to this repository:

- Never log profile content — log only metadata (profile ID, timestamp, dimension names)
- Never include real user profiles in test fixtures — use synthesised or fully anonymised data only
- Never store API keys, tokens, or credentials in code — use environment variables and ensure `.env` is in `.gitignore`
- All test profiles in the repository must have `provenance.extraction_method` set to `"synthesised"`
- Any contribution that weakens the sanitisation requirements will not be merged

---

## Disclosure policy

We follow coordinated disclosure. We ask that:

- You give us 45 days to fix a vulnerability before public disclosure
- You do not exploit the vulnerability beyond what is necessary to demonstrate it
- You do not access, modify, or delete data belonging to other users
- You report in good faith with the intention of improving security

In return, we commit to responding promptly, fixing issues seriously, and crediting researchers publicly.

---

## Security hall of fame

Researchers who responsibly disclose valid security vulnerabilities will be listed here with their permission.

*No entries yet — be the first.*

---

## Further reading

- [Zero-knowledge proof systems](https://en.wikipedia.org/wiki/Zero-knowledge_proof)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Coordinated vulnerability disclosure](https://cheatsheetseries.owasp.org/cheatsheets/Vulnerability_Disclosure_Cheat_Sheet.html)
- [GDPR Article 17 — Right to erasure](https://gdpr-info.eu/art-17-gdpr/)
- [EU AI Act portability provisions](https://artificialintelligenceact.eu/)
