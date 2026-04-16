"""Tests for UCS JSON Schema validation."""

import json
import os
import sys
import uuid
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ucs_parser.validator import Validator

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "schema", "ucs.schema.json")


def minimal_profile(**overrides) -> dict:
    """Return a minimal valid profile dict."""
    p = {
        "ucs_version": "0.1.0",
        "profile_id": str(uuid.uuid4()),
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "schema_url": "https://ucs-standard.org/schema/v0.1.0/ucs.schema.json",
        "persona": {
            "communication_style": {"direct": 1.0}
        },
        "provenance": {
            "source_platforms": ["chatgpt"],
            "extraction_method": "export",
            "sanitised": True,
            "sanitised_at": "2026-01-01T00:00:00Z",
            "attestation_signature": None,
        },
    }
    p.update(overrides)
    return p


@pytest.fixture
def validator():
    return Validator()


# ---------------------------------------------------------------------------
# Schema file presence
# ---------------------------------------------------------------------------

def test_schema_file_exists():
    assert os.path.exists(SCHEMA_PATH), f"Schema file not found at {SCHEMA_PATH}"


def test_schema_file_is_valid_json():
    with open(SCHEMA_PATH) as f:
        schema = json.load(f)
    assert "$schema" in schema
    assert "properties" in schema


# ---------------------------------------------------------------------------
# Valid profiles
# ---------------------------------------------------------------------------

class TestValidProfiles:
    def test_minimal_profile_is_valid(self, validator):
        result = validator.validate(minimal_profile())
        assert result.valid, f"Errors: {result.errors}"

    def test_full_example_file_is_valid(self, validator):
        path = os.path.join(os.path.dirname(__file__), "..", "schema", "examples", "full.ucs.json")
        result = validator.validate_file(path)
        assert result.valid, f"Errors: {result.errors}"

    def test_minimal_example_file_is_valid(self, validator):
        path = os.path.join(os.path.dirname(__file__), "..", "schema", "examples", "minimal.ucs.json")
        result = validator.validate_file(path)
        assert result.valid, f"Errors: {result.errors}"

    def test_profile_with_all_optional_dimensions(self, validator):
        p = minimal_profile()
        p["expertise_map"] = {
            "domains": [{"name": "Python", "depth": "expert"}]
        }
        p["project_graph"] = {
            "active": [{
                "id": str(uuid.uuid4()),
                "name": "Test project",
                "created_at": "2026-01-01T00:00:00Z",
            }],
            "archived": [],
        }
        p["preference_corpus"] = {
            "output_format": "prose",
            "response_length": "thorough",
        }
        p["interaction_patterns"] = {
            "common_corrections": ["Too many bullets"],
            "reinforced_behaviours": ["Concise answers"],
            "rejected_behaviours": ["Starting with 'Certainly!'"],
        }
        p["trust_boundaries"] = {
            "autonomous_action_tolerance": "medium",
            "preferred_confirmation_frequency": "sometimes",
            "sensitive_domains": ["legal", "financial"],
        }
        p["temporal_context"] = {
            "recency_weight": 0.7,
            "life_chapters": [{
                "label": "Current chapter",
                "from": "2024-01-01T00:00:00Z",
                "to": None,
                "active": True,
            }],
        }
        result = validator.validate(p)
        assert result.valid, f"Errors: {result.errors}"


# ---------------------------------------------------------------------------
# Invalid profiles — required fields
# ---------------------------------------------------------------------------

class TestMissingRequiredFields:
    @pytest.mark.parametrize("field", [
        "ucs_version", "profile_id", "created_at", "updated_at",
        "schema_url", "persona", "provenance",
    ])
    def test_missing_required_field_is_invalid(self, validator, field):
        p = minimal_profile()
        del p[field]
        result = validator.validate(p)
        assert not result.valid
        assert any(field in err for err in result.errors)

    def test_empty_source_platforms_is_invalid(self, validator):
        p = minimal_profile()
        p["provenance"]["source_platforms"] = []
        result = validator.validate(p)
        assert not result.valid

    def test_missing_sanitised_is_invalid(self, validator):
        p = minimal_profile()
        del p["provenance"]["sanitised"]
        result = validator.validate(p)
        assert not result.valid


# ---------------------------------------------------------------------------
# Type and value constraints
# ---------------------------------------------------------------------------

class TestTypeConstraints:
    def test_formality_above_1_is_invalid(self, validator):
        p = minimal_profile()
        p["persona"]["formality"] = 1.5
        result = validator.validate(p)
        assert not result.valid

    def test_formality_below_0_is_invalid(self, validator):
        p = minimal_profile()
        p["persona"]["formality"] = -0.1
        result = validator.validate(p)
        assert not result.valid

    def test_formality_at_boundaries_is_valid(self, validator):
        for v in [0.0, 0.5, 1.0]:
            p = minimal_profile()
            p["persona"]["formality"] = v
            result = validator.validate(p)
            assert result.valid, f"formality={v} should be valid. Errors: {result.errors}"

    def test_invalid_depth_enum_is_invalid(self, validator):
        p = minimal_profile()
        p["expertise_map"] = {"domains": [{"name": "Python", "depth": "genius"}]}
        result = validator.validate(p)
        assert not result.valid

    def test_valid_depth_enums(self, validator):
        for depth in ["aware", "functional", "proficient", "expert"]:
            p = minimal_profile()
            p["expertise_map"] = {"domains": [{"name": "Python", "depth": depth}]}
            result = validator.validate(p)
            assert result.valid, f"depth={depth} should be valid"

    def test_invalid_extraction_method_is_invalid(self, validator):
        p = minimal_profile()
        p["provenance"]["extraction_method"] = "scraped"
        result = validator.validate(p)
        assert not result.valid

    def test_recency_weight_out_of_range_is_invalid(self, validator):
        p = minimal_profile()
        p["temporal_context"] = {"recency_weight": 1.5}
        result = validator.validate(p)
        assert not result.valid

    def test_extension_namespace_must_be_dotted(self, validator):
        p = minimal_profile()
        p["extensions"] = {"INVALID_KEY": {"foo": "bar"}}
        result = validator.validate(p)
        assert not result.valid

    def test_extension_with_valid_namespace(self, validator):
        p = minimal_profile()
        p["extensions"] = {"com.example.myapp": {"foo": "bar"}}
        result = validator.validate(p)
        assert result.valid, f"Errors: {result.errors}"

    def test_additional_top_level_properties_rejected(self, validator):
        p = minimal_profile()
        p["unexpected_field"] = "surprise"
        result = validator.validate(p)
        assert not result.valid
