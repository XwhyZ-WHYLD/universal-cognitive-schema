"""
FidelityScorer: computes per-dimension fidelity scores for a UCS profile.

Fidelity reflects how much usable signal was captured for each dimension,
not how accurate the profile is (accuracy is unknowable without ground truth).

Scores are 0.0–1.0. Each dimension has a set of heuristics that raise or
lower the score based on what was populated and how richly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class DimensionScore:
    score:             float
    note:              str
    interaction_count: int = 0


@dataclass
class FidelityReport:
    generated_at:         datetime
    overall:              DimensionScore
    persona:              DimensionScore
    expertise_map:        DimensionScore
    project_graph:        DimensionScore
    preference_corpus:    DimensionScore
    interaction_patterns: DimensionScore
    trust_boundaries:     DimensionScore
    temporal_context:     DimensionScore

    def to_dict(self) -> dict[str, Any]:
        def score_to_dict(s: DimensionScore) -> dict[str, Any]:
            return {
                "score": round(s.score, 2),
                "note": s.note,
                "interaction_count": s.interaction_count,
            }
        return {
            "generated_at": self.generated_at.isoformat(),
            "overall":              score_to_dict(self.overall),
            "persona":              score_to_dict(self.persona),
            "expertise_map":        score_to_dict(self.expertise_map),
            "project_graph":        score_to_dict(self.project_graph),
            "preference_corpus":    score_to_dict(self.preference_corpus),
            "interaction_patterns": score_to_dict(self.interaction_patterns),
            "trust_boundaries":     score_to_dict(self.trust_boundaries),
            "temporal_context":     score_to_dict(self.temporal_context),
        }

    def summary(self) -> str:
        lines = [f"Fidelity Report (generated {self.generated_at.strftime('%Y-%m-%d %H:%M UTC')})"]
        lines.append(f"  Overall:              {self.overall.score:.2f}  {self.overall.note}")
        for label, dim in [
            ("Persona",              self.persona),
            ("Expertise map",        self.expertise_map),
            ("Project graph",        self.project_graph),
            ("Preference corpus",    self.preference_corpus),
            ("Interaction patterns", self.interaction_patterns),
            ("Trust boundaries",     self.trust_boundaries),
            ("Temporal context",     self.temporal_context),
        ]:
            bar = "█" * int(dim.score * 10) + "░" * (10 - int(dim.score * 10))
            lines.append(f"  {label:<22} {bar}  {dim.score:.2f}  {dim.note}")
        return "\n".join(lines)


class FidelityScorer:
    """
    Scores a UCS profile dict for fidelity across all 7 dimensions.
    """

    def score(self, profile: dict[str, Any], interaction_count: int = 0) -> FidelityReport:
        n = interaction_count

        persona   = self._score_persona(profile.get("persona", {}), n)
        expertise = self._score_expertise_map(profile.get("expertise_map"), n)
        projects  = self._score_project_graph(profile.get("project_graph"), n)
        prefs     = self._score_preference_corpus(profile.get("preference_corpus"), n)
        patterns  = self._score_interaction_patterns(profile.get("interaction_patterns"), n)
        trust     = self._score_trust_boundaries(profile.get("trust_boundaries"), n)
        temporal  = self._score_temporal_context(profile.get("temporal_context"), n)

        dimension_scores = [
            persona.score, expertise.score, projects.score, prefs.score,
            patterns.score, trust.score, temporal.score,
        ]
        overall_score = sum(dimension_scores) / len(dimension_scores)

        populated = sum(1 for s in dimension_scores if s > 0.1)
        if populated < 3:
            overall_note = "Low coverage — fewer than 3 dimensions have meaningful signal."
        elif overall_score >= 0.80:
            overall_note = "High overall fidelity."
        elif overall_score >= 0.60:
            overall_note = "Good overall fidelity with some gaps."
        else:
            overall_note = "Moderate fidelity — profile would benefit from more interaction data."

        return FidelityReport(
            generated_at=datetime.now(timezone.utc),
            overall=DimensionScore(score=round(overall_score, 2), note=overall_note, interaction_count=n),
            persona=persona,
            expertise_map=expertise,
            project_graph=projects,
            preference_corpus=prefs,
            interaction_patterns=patterns,
            trust_boundaries=trust,
            temporal_context=temporal,
        )

    # ------------------------------------------------------------------
    # Dimension scorers
    # ------------------------------------------------------------------

    def _score_persona(self, p: dict | None, n: int) -> DimensionScore:
        if not p:
            return DimensionScore(0.0, "No persona data.", n)

        score = 0.2  # base for having the dimension at all

        cs = p.get("communication_style", {})
        nonzero = sum(1 for v in cs.values() if v > 0)
        if nonzero >= 2:
            score += 0.25  # blended style, more expressive
        elif nonzero == 1:
            score += 0.10

        if p.get("formality") is not None:   score += 0.10
        if p.get("verbosity") is not None:   score += 0.10
        if p.get("tone_markers"):            score += min(0.15, len(p["tone_markers"]) * 0.04)
        if p.get("language_preferences"):    score += 0.10

        # Interaction count bonus
        if n >= 500:  score += 0.10
        if n >= 2000: score += 0.10

        score = min(1.0, score)
        note = self._interaction_note(n, score, "persona")
        return DimensionScore(score=round(score, 2), note=note, interaction_count=n)

    def _score_expertise_map(self, em: dict | None, n: int) -> DimensionScore:
        if not em or not em.get("domains"):
            return DimensionScore(0.0, "No expertise domains.", n)

        domains = em["domains"]
        score = 0.2 + min(0.4, len(domains) * 0.04)

        # Reward depth variety
        depths = {d.get("depth") for d in domains}
        if len(depths) >= 3: score += 0.15
        elif len(depths) >= 2: score += 0.08

        # Reward domains with notes
        with_notes = sum(1 for d in domains if d.get("notes"))
        score += min(0.15, with_notes * 0.03)

        # Reward recency signals
        with_dates = sum(1 for d in domains if d.get("last_active"))
        score += min(0.10, with_dates * 0.02)

        score = min(1.0, score)
        note = f"{len(domains)} domain(s) identified; depth variety: {len(depths)} level(s)."
        return DimensionScore(score=round(score, 2), note=note, interaction_count=n)

    def _score_project_graph(self, pg: dict | None, n: int) -> DimensionScore:
        if not pg:
            return DimensionScore(0.0, "No project graph.", n)

        active   = pg.get("active", [])
        archived = pg.get("archived", [])
        total = len(active) + len(archived)

        if total == 0:
            return DimensionScore(0.05, "Project graph present but empty.", n)

        score = 0.15 + min(0.30, total * 0.08)

        # Reward richly described projects
        rich = sum(1 for p in active + archived if p.get("context_summary") and len(p["context_summary"]) > 50)
        score += min(0.30, rich * 0.10)

        # Reward tagged projects
        tagged = sum(1 for p in active + archived if p.get("tags"))
        score += min(0.15, tagged * 0.04)

        score = min(1.0, score)
        note = f"{len(active)} active, {len(archived)} archived project(s)."
        return DimensionScore(score=round(score, 2), note=note, interaction_count=n)

    def _score_preference_corpus(self, pc: dict | None, n: int) -> DimensionScore:
        if not pc:
            return DimensionScore(0.0, "No preference corpus.", n)

        score = 0.10
        if pc.get("output_format"):             score += 0.20
        if pc.get("response_length"):           score += 0.20
        if pc.get("code_language_preferences"): score += 0.15
        if pc.get("citation_style"):            score += 0.10
        custom = pc.get("custom", {})
        if custom:                              score += min(0.25, len(custom) * 0.06)

        score = min(1.0, score)
        note = self._interaction_note(n, score, "preference corpus")
        return DimensionScore(score=round(score, 2), note=note, interaction_count=n)

    def _score_interaction_patterns(self, ip: dict | None, n: int) -> DimensionScore:
        if not ip:
            return DimensionScore(0.0, "No interaction patterns.", n)

        score = 0.10
        ps = ip.get("typical_prompt_style") or {}
        if ps.get("opener"):    score += 0.10
        if ps.get("structure"): score += 0.10
        if ps.get("avg_length"):score += 0.05

        corrections = ip.get("common_corrections", [])
        reinforced  = ip.get("reinforced_behaviours", [])
        rejected    = ip.get("rejected_behaviours", [])

        score += min(0.25, len(corrections) * 0.06)
        score += min(0.20, len(reinforced)  * 0.05)
        score += min(0.20, len(rejected)    * 0.05)

        score = min(1.0, score)
        note  = (
            f"{len(corrections)} correction(s), {len(reinforced)} reinforced, "
            f"{len(rejected)} rejected behaviour(s)."
        )
        return DimensionScore(score=round(score, 2), note=note, interaction_count=n)

    def _score_trust_boundaries(self, tb: dict | None, n: int) -> DimensionScore:
        if not tb:
            return DimensionScore(0.0, "No trust boundary data.", n)

        score = 0.10
        if tb.get("autonomous_action_tolerance"):       score += 0.30
        if tb.get("preferred_confirmation_frequency"):  score += 0.25
        sensitive = tb.get("sensitive_domains", [])
        score += min(0.35, len(sensitive) * 0.08)

        score = min(1.0, score)
        note = f"{len(sensitive)} sensitive domain(s) specified."
        if score < 0.4:
            note += " Low signal — trust dimensions are rarely explicit in conversation data."
        return DimensionScore(score=round(score, 2), note=note, interaction_count=n)

    def _score_temporal_context(self, tc: dict | None, n: int) -> DimensionScore:
        if not tc:
            return DimensionScore(0.0, "No temporal context.", n)

        score = 0.10
        if tc.get("recency_weight") is not None: score += 0.25
        chapters = tc.get("life_chapters", [])
        score += min(0.50, len(chapters) * 0.15)

        # Reward chapters with notes
        with_notes = sum(1 for c in chapters if c.get("notes"))
        score += min(0.15, with_notes * 0.05)

        score = min(1.0, score)
        note = f"{len(chapters)} life chapter(s) defined."
        return DimensionScore(score=round(score, 2), note=note, interaction_count=n)

    # ------------------------------------------------------------------

    def _interaction_note(self, n: int, score: float, dimension: str) -> str:
        if n == 0:
            return f"{dimension.capitalize()} inferred from static data."
        confidence = "High" if score >= 0.80 else "Good" if score >= 0.60 else "Moderate" if score >= 0.40 else "Low"
        return f"{confidence} confidence — inferred from {n:,} interactions."
