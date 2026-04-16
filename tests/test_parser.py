"""Tests for the ChatGPT export parser."""

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ucs_parser.parser import Parser, ParsedProfile

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "chatgpt_export_mock.json")


@pytest.fixture
def mock_conversations():
    with open(FIXTURE_PATH) as f:
        return json.load(f)


@pytest.fixture
def parsed(mock_conversations):
    parser = Parser(source="chatgpt")
    return parser.from_dict(mock_conversations)


# ---------------------------------------------------------------------------
# Parser initialisation
# ---------------------------------------------------------------------------

class TestParserInit:
    def test_valid_source_accepted(self):
        Parser(source="chatgpt")

    def test_invalid_source_raises(self):
        with pytest.raises(ValueError, match="Unsupported source"):
            Parser(source="gemini")

    def test_returns_parsed_profile(self, mock_conversations):
        parser = Parser(source="chatgpt")
        result = parser.from_dict(mock_conversations)
        assert isinstance(result, ParsedProfile)


# ---------------------------------------------------------------------------
# Profile structure
# ---------------------------------------------------------------------------

class TestProfileStructure:
    def test_profile_has_ucs_version(self, parsed):
        assert parsed.profile.ucs_version == "0.1.0"

    def test_profile_has_uuid(self, parsed):
        import uuid
        assert isinstance(parsed.profile.profile_id, uuid.UUID)

    def test_profile_has_timestamps(self, parsed):
        assert parsed.profile.created_at is not None
        assert parsed.profile.updated_at is not None

    def test_provenance_source_is_chatgpt(self, parsed):
        assert "chatgpt" in parsed.profile.provenance.source_platforms

    def test_provenance_extraction_method_is_export(self, parsed):
        assert parsed.profile.provenance.extraction_method.value == "export"

    def test_provenance_sanitised_is_true(self, parsed):
        assert parsed.profile.provenance.sanitised is True

    def test_provenance_sanitised_at_is_set(self, parsed):
        assert parsed.profile.provenance.sanitised_at is not None


# ---------------------------------------------------------------------------
# Persona inference
# ---------------------------------------------------------------------------

class TestPersonaInference:
    def test_persona_is_present(self, parsed):
        assert parsed.profile.persona is not None

    def test_communication_style_sums_near_1(self, parsed):
        cs = parsed.profile.persona.communication_style
        total = cs.direct + cs.collaborative + cs.socratic + cs.narrative
        assert 0.99 <= total <= 1.01, f"Communication style total: {total}"

    def test_formality_in_range(self, parsed):
        f = parsed.profile.persona.formality
        assert f is None or 0.0 <= f <= 1.0

    def test_verbosity_in_range(self, parsed):
        v = parsed.profile.persona.verbosity
        assert v is None or 0.0 <= v <= 1.0

    def test_language_primary_is_en(self, parsed):
        lp = parsed.profile.persona.language_preferences
        assert lp is not None
        assert lp.primary == "en"


# ---------------------------------------------------------------------------
# Expertise inference
# ---------------------------------------------------------------------------

class TestExpertiseInference:
    def test_expertise_map_is_present(self, parsed):
        assert parsed.profile.expertise_map is not None

    def test_at_least_one_domain_detected(self, parsed):
        domains = parsed.profile.expertise_map.domains
        assert len(domains) >= 1

    def test_software_engineering_detected(self, parsed):
        names = [d.name for d in parsed.profile.expertise_map.domains]
        assert any("software" in n.lower() or "python" in n.lower() for n in names)

    def test_all_depths_are_valid(self, parsed):
        valid_depths = {"aware", "functional", "proficient", "expert"}
        for domain in parsed.profile.expertise_map.domains:
            assert domain.depth.value in valid_depths


# ---------------------------------------------------------------------------
# Interaction pattern inference
# ---------------------------------------------------------------------------

class TestInteractionPatterns:
    def test_interaction_patterns_present(self, parsed):
        assert parsed.profile.interaction_patterns is not None

    def test_corrections_detected_from_fixture(self, parsed):
        """The fixture contains messages like 'Don't use bullet points'."""
        corrections = parsed.profile.interaction_patterns.common_corrections
        assert len(corrections) >= 1

    def test_rejected_opener_filler_detected(self, parsed):
        corrections = parsed.profile.interaction_patterns.common_corrections
        # "Please don't start with 'Great question'" should be caught
        assert any("filler" in c.lower() or "opener" in c.lower() for c in corrections)

    def test_prompt_style_is_present(self, parsed):
        assert parsed.profile.interaction_patterns.typical_prompt_style is not None


# ---------------------------------------------------------------------------
# Preference inference
# ---------------------------------------------------------------------------

class TestPreferenceInference:
    def test_preference_corpus_present(self, parsed):
        assert parsed.profile.preference_corpus is not None

    def test_response_length_is_valid(self, parsed):
        rl = parsed.profile.preference_corpus.response_length
        if rl is not None:
            assert rl.value in {"concise", "moderate", "thorough"}


# ---------------------------------------------------------------------------
# Fidelity
# ---------------------------------------------------------------------------

class TestFidelityReport:
    def test_fidelity_is_attached_to_profile(self, parsed):
        assert parsed.profile.fidelity is not None

    def test_fidelity_overall_in_range(self, parsed):
        score = parsed.profile.fidelity.overall.score
        assert 0.0 <= score <= 1.0

    def test_fidelity_report_string(self, parsed):
        report = parsed.fidelity_report()
        assert "Fidelity Report" in report
        assert "Persona" in report

    def test_all_dimension_scores_in_range(self, parsed):
        f = parsed.profile.fidelity
        for dim in [f.persona, f.expertise_map, f.project_graph,
                    f.preference_corpus, f.interaction_patterns,
                    f.trust_boundaries, f.temporal_context]:
            if dim is not None:
                assert 0.0 <= dim.score <= 1.0


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestValidation:
    def test_parsed_profile_is_valid(self, parsed):
        from ucs_parser.validator import Validator
        v = Validator()
        result = v.validate(parsed.to_dict())
        assert result.valid, f"Validation errors: {result.errors}"


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

class TestFileIO:
    def test_to_json_writes_file(self, parsed):
        with tempfile.NamedTemporaryFile(suffix=".ucs.json", delete=False) as f:
            path = f.name
        try:
            parsed.to_json(path)
            assert os.path.exists(path)
            with open(path) as f:
                data = json.load(f)
            assert data["ucs_version"] == "0.1.0"
        finally:
            os.unlink(path)

    def test_from_file_raises_on_missing_file(self):
        parser = Parser(source="chatgpt")
        with pytest.raises(FileNotFoundError):
            parser.from_file("/nonexistent/path/export.json")

    def test_from_file_raises_on_unsupported_type(self):
        parser = Parser(source="chatgpt")
        with pytest.raises(ValueError, match="Unsupported file type"):
            parser.from_file("/some/file.csv")
