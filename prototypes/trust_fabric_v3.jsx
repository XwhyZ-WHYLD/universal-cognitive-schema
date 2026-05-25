import { useMemo, useState } from "react";
import { motion } from "framer-motion";

// ─── Math helpers ────────────────────────────────────────────────────────────
const clamp01 = (x) => Math.max(0, Math.min(1, Number.isFinite(x) ? x : 0));
const pct = (x) => `${Math.round(clamp01(x) * 1000) / 10}%`;
const score100 = (x) => Math.round(clamp01(x) * 1000) / 10;

function trustAggregate(proofs) {
  return clamp01(1 - proofs.reduce((acc, q) => acc * (1 - clamp01(q)), 1));
}
function decay(q, lambda, ageYears) {
  return clamp01(q * Math.exp(-lambda * ageYears));
}
function syntheticRisk(risks) {
  return clamp01(1 - risks.reduce((acc, r) => acc * (1 - clamp01(r)), 1));
}
function witnessFactor(drift, lambda) {
  return clamp01(Math.exp(-lambda * clamp01(drift)));
}

function tier(score) {
  if (score >= 0.99) return { id: "T5", label: "Multi-domain continuity verified", color: "#34d399" };
  if (score >= 0.92) return { id: "T4", label: "Quantum-ready verified", color: "#4ade80" };
  if (score >= 0.75) return { id: "T3", label: "Cryptographically anchored", color: "#60a5fa" };
  if (score >= 0.5)  return { id: "T2", label: "Institutionally verified", color: "#fbbf24" };
  if (score >= 0.25) return { id: "T1", label: "Socially attested", color: "#fb923c" };
  return { id: "T0", label: "Self-claimed", color: "#f87171" };
}

function readinessBand(x) {
  if (x >= 0.95) return "High assurance";
  if (x >= 0.85) return "Strong prototype";
  if (x >= 0.7)  return "Needs hardening";
  return "Fragile";
}

// ─── Default state ────────────────────────────────────────────────────────────
const defaultState = {
  peer: 0.68, institution: 0.86, cryptoAnchor: 0.96, hardware: 0.92,
  behavior: 0.94, interaction: 0.96, lambdaProof: 0.12, proofAge: 0.35,
  deepfake: 0.04, voiceClone: 0.05, aiText: 0.08, geoAnomaly: 0.02,
  credentialAnomaly: 0.03, cyber: 0.03, replay: 0.02, collusion: 0.04,
  driftBehavior: 0.03, driftClaims: 0.02, driftValues: 0.03,
  driftSecurity: 0.02, driftAttestation: 0.02, lambdaWitness: 1.0,
  graphDistance: 1, lambdaGraph: 0.25, liveness: 0.97, revocationFreshness: 0.98,
};

// ─── Sub-components ───────────────────────────────────────────────────────────
function Slider({ label, value, onChange, min = 0, max = 1, step = 0.01, hint }) {
  const pctVal = min === 0 && max === 1
    ? `${Math.round(value * 100)}%`
    : value.toFixed(2);
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ fontSize: 12, color: "#94a3b8", fontFamily: "monospace" }}>{label}</span>
        <span style={{ fontSize: 12, color: "#e2e8f0", fontFamily: "monospace", fontWeight: 700 }}>{pctVal}</span>
      </div>
      <input
        type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ width: "100%", accentColor: "#38bdf8", cursor: "pointer" }}
      />
      {hint && <p style={{ fontSize: 11, color: "#64748b", marginTop: 3, fontFamily: "monospace" }}>{hint}</p>}
    </div>
  );
}

function LayerBar({ label, value }) {
  const t = tier(value);
  return (
    <div style={{ background: "#0f172a", borderRadius: 10, padding: "10px 14px", marginBottom: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
        <span style={{ fontSize: 12, color: "#94a3b8", fontFamily: "monospace" }}>{label}</span>
        <span style={{ fontSize: 13, fontWeight: 700, color: "#f1f5f9", fontFamily: "monospace" }}>{pct(value)}</span>
      </div>
      <div style={{ height: 4, background: "#1e293b", borderRadius: 4, overflow: "hidden" }}>
        <div style={{ height: "100%", width: pct(value), background: t.color, borderRadius: 4, transition: "width 0.3s ease" }} />
      </div>
    </div>
  );
}

function Card({ children, style = {} }) {
  return (
    <div style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 16, padding: 20, ...style }}>
      {children}
    </div>
  );
}

function SectionTitle({ children }) {
  return (
    <div style={{ fontSize: 13, fontWeight: 700, color: "#38bdf8", fontFamily: "monospace", textTransform: "uppercase", letterSpacing: 2, marginBottom: 16 }}>
      {children}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function UCSTrustFabricPrototype() {
  const [s, setS] = useState(defaultState);
  const set = (k) => (v) => setS((prev) => ({ ...prev, [k]: v }));

  const result = useMemo(() => {
    const decayedProofs = [
      decay(s.peer, s.lambdaProof, s.proofAge),
      decay(s.institution, s.lambdaProof, s.proofAge),
      decay(s.cryptoAnchor, s.lambdaProof, s.proofAge),
      decay(s.hardware, s.lambdaProof, s.proofAge),
    ];
    const T_identity = trustAggregate(decayedProofs);
    const T_behavior = trustAggregate([s.behavior, s.interaction, s.liveness]);
    const T_crypto   = trustAggregate([s.cryptoAnchor, s.hardware, s.revocationFreshness]);
    const T_system   = trustAggregate([1 - s.cyber, 1 - s.replay, 1 - s.collusion]);
    const R_synthetic = syntheticRisk([s.deepfake, s.voiceClone, s.aiText, s.geoAnomaly, s.credentialAnomaly]);
    const R_cyber     = syntheticRisk([s.cyber, s.replay]);
    const R_collusion = clamp01(s.collusion * Math.exp(-0.15 * s.graphDistance));
    const D_t = clamp01(
      0.24 * s.driftBehavior + 0.18 * s.driftClaims +
      0.18 * s.driftValues  + 0.22 * s.driftSecurity + 0.18 * s.driftAttestation
    );
    const W = witnessFactor(D_t, s.lambdaWitness);
    const graphDecay = clamp01(Math.exp(-s.lambdaGraph * s.graphDistance));
    const final = clamp01(
      T_identity * T_crypto * T_behavior * T_system *
      (1 - R_synthetic) * (1 - R_cyber) * (1 - R_collusion) * W * graphDecay
    );
    return { T_identity, T_behavior, T_crypto, T_system, R_synthetic, R_cyber, R_collusion, D_t, W, graphDecay, final, tier: tier(final) };
  }, [s]);

  const schema = useMemo(() => ({
    provenance: {
      version: "3.0",
      trust_model: "UCS-TF-v3-TSSI",
      identity_roots: {
        did: "did:ucs:8fa91b1d2",
        classical_public_key: "ed25519:...",
        pq_public_key: "mldsa:...",
        hardware_key_id: "hwk:secure-enclave-or-token",
        recovery_key_hash: "sha3-512:...",
      },
      attestations: [{
        id: "att-001", type: "institutional_vc", format: "W3C-VC-2.0",
        issuer: "did:example:institution", claims: ["identity", "employment"],
        signature_classical: "...", signature_pq: "...",
        created_at: "2026-05-24T00:00:00Z", expires_at: "2027-05-24T00:00:00Z",
        revocation_pointer: "rev://att-001",
      }],
      computed: {
        final_trust_score: score100(result.final),
        tier: result.tier.id,
        tier_label: result.tier.label,
        temporal_witness_score: score100(result.W),
        synthetic_risk: score100(result.R_synthetic),
        cyber_risk: score100(result.R_cyber),
        collusion_risk: score100(result.R_collusion),
      },
    },
  }), [result]);

  const finalColor = result.tier.color;

  return (
    <div style={{ background: "#020817", minHeight: "100vh", padding: "24px 16px", fontFamily: "monospace", color: "#e2e8f0" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>

        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
          <div style={{ background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)", border: "1px solid #38bdf830", borderRadius: 20, padding: "28px 32px", marginBottom: 24 }}>
            <div style={{ display: "inline-flex", alignItems: "center", gap: 8, background: "#38bdf815", border: "1px solid #38bdf830", borderRadius: 999, padding: "5px 14px", marginBottom: 16 }}>
              <span style={{ color: "#38bdf8", fontSize: 12, fontWeight: 700, letterSpacing: 1 }}>UCS TRUST FABRIC v3 + TSSI PROTOTYPE</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 16 }}>
              <div>
                <h1 style={{ fontSize: 28, fontWeight: 900, color: "#f1f5f9", margin: 0, letterSpacing: -1 }}>
                  Quantum-ready identity continuity engine
                </h1>
                <p style={{ color: "#64748b", fontSize: 13, margin: "8px 0 0", maxWidth: 600 }}>
                  Live calculator — cryptographic continuity · behavioral continuity · temporal witness integrity · Sybil decay · cyber risk · synthetic identity risk
                </p>
              </div>
              <button
                onClick={() => setS(defaultState)}
                style={{ background: "#1e293b", border: "1px solid #334155", color: "#94a3b8", borderRadius: 10, padding: "8px 18px", fontSize: 12, cursor: "pointer", fontFamily: "monospace", fontWeight: 700 }}
              >
                ↺ Reset model
              </button>
            </div>
          </div>
        </motion.div>

        {/* Score hero */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.15, duration: 0.5 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12, marginBottom: 24 }}>
            {[
              { label: "FINAL TRUST SCORE", value: `${score100(result.final)} / 100`, sub: `${result.tier.id} · ${result.tier.label}`, accent: finalColor },
              { label: "SYNTHETIC RISK", value: pct(result.R_synthetic), sub: "Deepfake · voice · text · geo · credential", accent: result.R_synthetic > 0.15 ? "#f87171" : "#fbbf24" },
              { label: "WITNESS FACTOR", value: pct(result.W), sub: "Temporal drift suppression", accent: "#60a5fa" },
              { label: "READINESS", value: readinessBand(result.final), sub: "Architecture-level assessment", accent: "#a78bfa" },
            ].map((m, i) => (
              <div key={i} style={{ background: "#0f172a", border: `1px solid ${m.accent}30`, borderRadius: 14, padding: "18px 20px", borderTop: `3px solid ${m.accent}` }}>
                <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, letterSpacing: 2, marginBottom: 8 }}>{m.label}</div>
                <div style={{ fontSize: 22, fontWeight: 900, color: m.accent, marginBottom: 4 }}>{m.value}</div>
                <div style={{ fontSize: 11, color: "#64748b" }}>{m.sub}</div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Main grid */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, marginBottom: 16 }}>

          {/* Evidence proofs */}
          <Card>
            <SectionTitle>Evidence Proofs</SectionTitle>
            <Slider label="Peer attestation" value={s.peer} onChange={set("peer")} />
            <Slider label="Institutional VC" value={s.institution} onChange={set("institution")} />
            <Slider label="Crypto anchor" value={s.cryptoAnchor} onChange={set("cryptoAnchor")} />
            <Slider label="Hardware-backed key" value={s.hardware} onChange={set("hardware")} />
            <Slider label="Proof age (years)" value={s.proofAge} onChange={set("proofAge")} hint="q(t) = q · e^−λt" />
          </Card>

          {/* Continuity */}
          <Card>
            <SectionTitle>Continuity + Liveness</SectionTitle>
            <Slider label="Behavioral continuity" value={s.behavior} onChange={set("behavior")} />
            <Slider label="Interaction history" value={s.interaction} onChange={set("interaction")} />
            <Slider label="Live challenge-response" value={s.liveness} onChange={set("liveness")} />
            <Slider label="Revocation freshness" value={s.revocationFreshness} onChange={set("revocationFreshness")} />
            <Slider label="Graph distance" value={s.graphDistance} onChange={set("graphDistance")} min={0} max={5} step={0.1} hint="Higher distance → weaker propagated trust" />
          </Card>

          {/* Adversarial risks */}
          <Card>
            <SectionTitle>Adversarial Risks</SectionTitle>
            <Slider label="Deepfake risk" value={s.deepfake} onChange={set("deepfake")} />
            <Slider label="Voice clone risk" value={s.voiceClone} onChange={set("voiceClone")} />
            <Slider label="AI-text mimicry" value={s.aiText} onChange={set("aiText")} />
            <Slider label="Geo anomaly" value={s.geoAnomaly} onChange={set("geoAnomaly")} />
            <Slider label="Credential anomaly" value={s.credentialAnomaly} onChange={set("credentialAnomaly")} />
            <Slider label="Cyber compromise" value={s.cyber} onChange={set("cyber")} />
            <Slider label="Replay risk" value={s.replay} onChange={set("replay")} />
            <Slider label="Collusion risk" value={s.collusion} onChange={set("collusion")} />
          </Card>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 16, marginBottom: 16 }}>

          {/* TSSI Drift */}
          <Card>
            <SectionTitle>TSSI Drift Monitor</SectionTitle>
            <Slider label="Behavior drift" value={s.driftBehavior} onChange={set("driftBehavior")} />
            <Slider label="Claims drift" value={s.driftClaims} onChange={set("driftClaims")} />
            <Slider label="Values drift" value={s.driftValues} onChange={set("driftValues")} />
            <Slider label="Security drift" value={s.driftSecurity} onChange={set("driftSecurity")} />
            <Slider label="Attestation drift" value={s.driftAttestation} onChange={set("driftAttestation")} />
            <div style={{ marginTop: 16, background: "#020817", borderRadius: 10, padding: "10px 14px" }}>
              <div style={{ fontSize: 10, color: "#475569", letterSpacing: 2, marginBottom: 4 }}>WITNESS FACTOR W</div>
              <div style={{ fontSize: 20, fontWeight: 900, color: result.W > 0.9 ? "#34d399" : result.W > 0.7 ? "#fbbf24" : "#f87171" }}>
                {pct(result.W)}
              </div>
              <div style={{ fontSize: 10, color: "#475569", marginTop: 2 }}>W = e^(−λ · D_t)</div>
            </div>
          </Card>

          {/* Computed layers */}
          <Card>
            <SectionTitle>Computed Trust Layers</SectionTitle>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 16 }}>
              <LayerBar label="Identity trust" value={result.T_identity} />
              <LayerBar label="Crypto trust" value={result.T_crypto} />
              <LayerBar label="Behavior trust" value={result.T_behavior} />
              <LayerBar label="System trust" value={result.T_system} />
              <LayerBar label="Graph decay" value={result.graphDecay} />
              <LayerBar label="Drift-adjusted" value={1 - result.D_t} />
            </div>
            <div style={{ background: "#020817", borderRadius: 12, padding: "14px 16px" }}>
              <div style={{ fontSize: 10, color: "#475569", letterSpacing: 2, marginBottom: 8 }}>FINAL EQUATION</div>
              <div style={{ fontSize: 11, color: "#38bdf8", lineHeight: 1.8, wordBreak: "break-word" }}>
                T_final = T_identity × T_crypto × T_behavior × T_system<br />
                × (1 − R_synthetic) × (1 − R_cyber) × (1 − R_collusion)<br />
                × W × graph_decay
              </div>
              <div style={{ marginTop: 12, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span style={{ fontSize: 11, color: "#64748b" }}>Current result</span>
                <span style={{ fontSize: 24, fontWeight: 900, color: finalColor }}>{score100(result.final)} / 100</span>
              </div>
              <div style={{ marginTop: 8, height: 6, background: "#1e293b", borderRadius: 6, overflow: "hidden" }}>
                <motion.div
                  style={{ height: "100%", background: finalColor, borderRadius: 6 }}
                  animate={{ width: pct(result.final) }}
                  transition={{ duration: 0.4, ease: "easeOut" }}
                />
              </div>
              <div style={{ marginTop: 8, fontSize: 12, fontWeight: 700, color: finalColor }}>
                {result.tier.id} · {result.tier.label}
              </div>
            </div>
          </Card>
        </div>

        {/* Provenance JSON */}
        <Card style={{ marginBottom: 16 }}>
          <SectionTitle>Generated Provenance Output — ucs.schema.json v3</SectionTitle>
          <pre style={{ background: "#020817", borderRadius: 12, padding: 16, fontSize: 11, color: "#94a3b8", overflow: "auto", maxHeight: 400, lineHeight: 1.7, margin: 0 }}>
            {JSON.stringify(schema, null, 2)}
          </pre>
        </Card>

        {/* Footer cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
          {[
            { title: "Crypto-ready", body: "Ed25519 + ML-DSA signatures, ML-KEM key establishment, SHA3/SHAKE hashing. Dual-sign every critical interaction.", accent: "#34d399" },
            { title: "Synthetic-aware", body: "Synthetic risk actively suppresses the final trust score rather than triggering a passive warning flag.", accent: "#60a5fa" },
            { title: "Witness not authority", body: "The temporal layer records longitudinal drift without becoming a central controller. Decentralized integrity.", accent: "#fbbf24" },
          ].map((c, i) => (
            <div key={i} style={{ background: "#0f172a", border: `1px solid ${c.accent}20`, borderRadius: 14, padding: 18, borderLeft: `3px solid ${c.accent}` }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: c.accent, marginBottom: 8 }}>{c.title}</div>
              <div style={{ fontSize: 12, color: "#64748b", lineHeight: 1.6 }}>{c.body}</div>
            </div>
          ))}
        </div>

      </div>
    </div>
  );
}
