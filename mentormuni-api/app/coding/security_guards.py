"""Guards to ensure student API payloads never leak evaluator secrets."""

from __future__ import annotations

from typing import Any

# Always forbidden in student-facing coding Phase 3 responses
ALWAYS_FORBIDDEN = frozenset(
    {
        "hidden_tests",
        "hidden_test_cases",
        "is_hidden",
        "expected_output",
        "reference_solution",
        "reference_solutions",
        "evidence_json",
        "evidence_notes",
        "evidence_confidence",
        "provider_submission_token",
        "execution_config",
        "weight_policy_json",
        "raw_response",
        "test_cases",
    }
)


def assert_no_forbidden_keys(
    payload: Any,
    *,
    allow_draft_source: bool = False,
    path: str = "$",
) -> None:
    """Recursively assert student-facing JSON does not contain evaluator secrets."""
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_s = str(key)
            if key_s in ALWAYS_FORBIDDEN:
                raise AssertionError(f"Forbidden key at {path}.{key_s}")
            if key_s == "source_code" and not allow_draft_source:
                raise AssertionError(f"Forbidden key at {path}.{key_s}")
            child_path = f"{path}.{key_s}"
            # Public examples may include input/output strings
            if key_s == "examples" and isinstance(value, list):
                for i, ex in enumerate(value):
                    if not isinstance(ex, dict):
                        continue
                    for ek in ex:
                        if ek in ALWAYS_FORBIDDEN or ek == "source_code":
                            raise AssertionError(f"Forbidden key at {child_path}[{i}].{ek}")
                continue
            assert_no_forbidden_keys(
                value,
                allow_draft_source=allow_draft_source,
                path=child_path,
            )
    elif isinstance(payload, list):
        for i, item in enumerate(payload):
            assert_no_forbidden_keys(
                item,
                allow_draft_source=allow_draft_source,
                path=f"{path}[{i}]",
            )
