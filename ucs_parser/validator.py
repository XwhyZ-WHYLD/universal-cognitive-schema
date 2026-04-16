"""
Validator: validates a dict or file against the UCS JSON Schema.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValidationResult:
    valid:  bool
    errors: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.valid


class Validator:
    """
    Validates a UCS profile dict against the bundled JSON Schema.

    Requires `jsonschema` (pip install jsonschema).
    Falls back to structural checks if jsonschema is not available.
    """

    SCHEMA_PATH = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "schema", "ucs.schema.json"
    )

    REQUIRED_TOP_LEVEL = {
        "ucs_version", "profile_id", "created_at", "updated_at",
        "schema_url", "persona", "provenance",
    }

    def __init__(self) -> None:
        self._schema: dict[str, Any] | None = None
        self._has_jsonschema = self._check_jsonschema()

    def _check_jsonschema(self) -> bool:
        try:
            import jsonschema  # noqa: F401
            return True
        except ImportError:
            return False

    def _load_schema(self) -> dict[str, Any]:
        if self._schema is None:
            if not os.path.exists(self.SCHEMA_PATH):
                raise FileNotFoundError(
                    f"Schema file not found at {self.SCHEMA_PATH}. "
                    "Ensure ucs.schema.json is present in the schema/ directory."
                )
            with open(self.SCHEMA_PATH, encoding="utf-8") as f:
                self._schema = json.load(f)
        return self._schema

    def validate(self, data: dict[str, Any]) -> ValidationResult:
        """Validate a profile dict. Returns a ValidationResult."""
        if self._has_jsonschema:
            return self._validate_with_jsonschema(data)
        return self._validate_structural(data)

    def validate_file(self, path: str) -> ValidationResult:
        """Load a .ucs.json file and validate it."""
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return ValidationResult(valid=False, errors=[f"Invalid JSON: {e}"])
        except OSError as e:
            return ValidationResult(valid=False, errors=[f"Cannot read file: {e}"])
        return self.validate(data)

    # ------------------------------------------------------------------

    def _validate_with_jsonschema(self, data: dict[str, Any]) -> ValidationResult:
        import jsonschema

        schema = self._load_schema()
        validator = jsonschema.Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))

        if not errors:
            return ValidationResult(valid=True)

        messages = []
        for err in errors:
            path = " -> ".join(str(p) for p in err.absolute_path) or "(root)"
            messages.append(f"{path}: {err.message}")
        return ValidationResult(valid=False, errors=messages)

    def _validate_structural(self, data: dict[str, Any]) -> ValidationResult:
        """Fallback structural check when jsonschema is unavailable."""
        errors: list[str] = []

        if not isinstance(data, dict):
            return ValidationResult(valid=False, errors=["Profile must be a JSON object."])

        missing = self.REQUIRED_TOP_LEVEL - set(data.keys())
        for key in sorted(missing):
            errors.append(f"Missing required field: '{key}'")

        version = data.get("ucs_version")
        if version and not isinstance(version, str):
            errors.append("'ucs_version' must be a string.")

        provenance = data.get("provenance")
        if provenance:
            if not isinstance(provenance.get("source_platforms"), list):
                errors.append("'provenance.source_platforms' must be an array.")
            if "sanitised" not in provenance:
                errors.append("'provenance.sanitised' is required.")

        return ValidationResult(valid=len(errors) == 0, errors=errors)
