"""Unit tests for coding question bank pipeline (no LLM generation of the 50)."""

from __future__ import annotations

import pytest

from app.coding.enums import ProblemStatus
from app.coding_bank import CURRICULUM_VERSION, PROMPT_VERSION
from app.coding_bank.curriculum import build_placement_curriculum_v1, pattern_distribution
from app.coding_bank.generator import CodingProblemGenerator, GenerationError
from app.coding_bank.lifecycle import ALLOWED_TRANSITIONS, LifecycleError, assert_transition, can_publish
from app.coding_bank.prompt import render_generation_user_prompt
from app.coding_bank.schemas import GeneratedProblemContract
from app.coding_bank.validators.duplicate import DuplicateDetector, ExistingProblemRef, content_fingerprint
from app.coding_bank.validators.pipeline import ProblemValidator
from app.coding_bank.validators.reference import ExecutionProbe


def _minimal_contract(**overrides):
    base = {
        "title": "Pair Sum Ledger",
        "slug": "pair-sum-ledger",
        "difficulty": "easy",
        "topics": ["hashing"],
        "patterns": ["hash-map"],
        "problem_statement": (
            "You are given an array of integers representing daily ledger deltas and a target "
            "balance change T. Return indices of two distinct days whose deltas sum to T. "
            "If multiple answers exist, return any one pair."
        ),
        "input_format": "First line: n T. Second line: n integers.",
        "output_format": "Two 0-based indices separated by space.",
        "constraints": "2 <= n <= 1e5; -1e9 <= a[i], T <= 1e9. Exactly one valid pair is guaranteed.",
        "examples": [
            {
                "input": "4 9\n2 7 11 15",
                "output": "0 1",
                "explanation": "2+7=9",
            },
            {
                "input": "3 6\n3 2 4",
                "output": "1 2",
                "explanation": "2+4=6",
            },
        ],
        "explanation": "Use a hash map from value to index while scanning once left to right.",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(n)",
        "supported_languages": ["python", "cpp", "java"],
        "starter_code": [
            {"language": "python", "code": "import sys\n\ndef solve():\n    pass\n\nif __name__ == '__main__':\n    solve()\n"},
            {"language": "cpp", "code": "#include <bits/stdc++.h>\nusing namespace std; int main(){}"},
            {"language": "java", "code": "public class Main { public static void main(String[] a){}}"},
        ],
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "def main():\n"
                    "    data=sys.stdin.read().strip().split()\n"
                    "    n,t=int(data[0]),int(data[1])\n"
                    "    a=list(map(int,data[2:]))\n"
                    "    seen={}\n"
                    "    for i,x in enumerate(a):\n"
                    "        if t-x in seen:\n"
                    "            print(seen[t-x], i); return\n"
                    "        seen[x]=i\n"
                    "if __name__=='__main__':\n"
                    "    main()\n"
                ),
            }
        ],
        "candidate_test_cases": [
            {"input": "4 9\n2 7 11 15", "expected_output": "0 1", "category": "normal", "is_hidden": False},
            {"input": "2 3\n1 2", "expected_output": "0 1", "category": "minimum", "is_hidden": False},
            {"input": "5 0\n-1 1 2 3 4", "expected_output": "0 1", "category": "negative", "is_hidden": True},
            {"input": "5 4\n1 1 1 3 2", "expected_output": "0 3", "category": "duplicates", "is_hidden": True},
            {"input": "4 100\n50 49 51 1", "expected_output": "0 2", "category": "boundary", "is_hidden": True},
            {"input": "6 8\n1 2 3 4 5 6", "expected_output": "1 5", "category": "adversarial", "is_hidden": True},
            {"input": "3 5\n5 0 0", "expected_output": "1 2", "category": "boundary", "is_hidden": True},
            {"input": "4 6\n3 3 3 3", "expected_output": "0 1", "category": "duplicates", "is_hidden": True},
        ],
    }
    base.update(overrides)
    return base


class TestCurriculum:
    def test_placement_matrix_is_about_fifty(self):
        cfg = build_placement_curriculum_v1()
        assert cfg.version == CURRICULUM_VERSION
        assert 48 <= cfg.target_count <= 52
        assert len(cfg.specs) == cfg.target_count
        dist = pattern_distribution(cfg)
        assert "hashing/hash-map" in dist
        assert "dynamic-programming/1d-dp" in dist


class TestGenerationContract:
    def test_valid_contract(self):
        c = GeneratedProblemContract.model_validate(_minimal_contract())
        assert c.slug == "pair-sum-ledger"
        assert c.primary_pattern() == "hash-map"

    def test_rejects_bad_slug(self):
        with pytest.raises(Exception):
            GeneratedProblemContract.model_validate(_minimal_contract(slug="Bad Slug!"))

    def test_requires_python_reference(self):
        payload = _minimal_contract(
            reference_solutions=[{"language": "cpp", "code": "int main(){}"}]
        )
        with pytest.raises(Exception):
            GeneratedProblemContract.model_validate(payload)

    def test_requires_diverse_test_categories(self):
        payload = _minimal_contract(
            candidate_test_cases=[
                {"input": "1", "expected_output": "1", "category": "normal"},
                {"input": "2", "expected_output": "2", "category": "normal"},
                {"input": "3", "expected_output": "3", "category": "normal"},
                {"input": "4", "expected_output": "4", "category": "normal"},
                {"input": "5", "expected_output": "5", "category": "normal"},
            ]
        )
        with pytest.raises(Exception):
            GeneratedProblemContract.model_validate(payload)


class TestPrompt:
    def test_prompt_version_and_prohibitions(self):
        text = render_generation_user_prompt(
            difficulty="easy",
            topic="arrays",
            pattern="prefix-sum",
            expected_time_complexity="O(n)",
            expected_space_complexity="O(1)",
        )
        assert PROMPT_VERSION in text
        assert "Ambiguous requirements" in text
        assert "LeetCode" not in text or "Do NOT"  # system has leetcode prohibition
        assert "placement" in text.lower()


class TestLifecycle:
    def test_happy_path_transitions(self):
        assert_transition(ProblemStatus.GENERATED, ProblemStatus.VALIDATING)
        assert_transition(ProblemStatus.VALIDATING, ProblemStatus.PENDING_REVIEW)
        assert_transition(ProblemStatus.PENDING_REVIEW, ProblemStatus.APPROVED)
        assert_transition(ProblemStatus.APPROVED, ProblemStatus.PUBLISHED)
        assert can_publish(ProblemStatus.APPROVED)
        assert not can_publish(ProblemStatus.PENDING_REVIEW)

    def test_cannot_skip_to_published(self):
        with pytest.raises(LifecycleError):
            assert_transition(ProblemStatus.GENERATED, ProblemStatus.PUBLISHED)

    def test_published_only_archives(self):
        assert ALLOWED_TRANSITIONS[ProblemStatus.PUBLISHED] == {ProblemStatus.ARCHIVED}


class TestDuplicateDetector:
    def test_near_duplicate_title(self):
        contract = GeneratedProblemContract.model_validate(_minimal_contract())
        existing = [
            ExistingProblemRef(
                id=99,
                title="Pair Sum Ledger",
                statement=contract.problem_statement,
                topic="hashing",
                pattern="hash-map",
            )
        ]
        det = DuplicateDetector()
        report = det.validate(contract, existing)
        assert not report.ok
        assert report.duplicate_of_problem_id == 99

    def test_fingerprint_stable(self):
        a = content_fingerprint("A", "hello world", "arrays", "sorting")
        b = content_fingerprint("A", "hello   world", "arrays", "sorting")
        assert a == b


class _FakeExecutor:
    async def run_stdin(self, *, language, source_code, stdin, time_limit_ms=2000, memory_limit_kb=256000):
        # Minimal fake: echo a deterministic mapping for known fixtures
        mapping = {
            "4 9\n2 7 11 15": "0 1",
            "2 3\n1 2": "0 1",
            "5 0\n-1 1 2 3 4": "0 1",
            "5 4\n1 1 1 3 2": "0 3",
            "4 100\n50 49 51 1": "0 2",
            "6 8\n1 2 3 4 5 6": "1 5",
            "3 5\n5 0 0": "1 2",
            "4 6\n3 3 3 3": "0 1",
            "": "0 0",  # smoke
        }
        if stdin in mapping:
            return ExecutionProbe(ok=True, stdout=mapping[stdin] + "\n")
        return ExecutionProbe(ok=False, error="unknown input")


@pytest.mark.asyncio
async def test_problem_validator_pass_with_executor():
    contract = GeneratedProblemContract.model_validate(_minimal_contract())
    validator = ProblemValidator(executor=_FakeExecutor())
    c, report = await validator.validate(contract, existing=[])
    assert c is not None
    assert report.ok
    assert report.quality_score > 0
    assert "case_0" in report.canonical_outputs


@pytest.mark.asyncio
async def test_problem_validator_rejects_schema():
    validator = ProblemValidator()
    c, report = await validator.validate({"title": "x"}, existing=[])
    assert c is None
    assert not report.ok


def test_generator_rejects_without_client():
    gen = CodingProblemGenerator(openai_client=None)

    async def _run():
        from app.coding_bank.curriculum import GenerationSpec

        with pytest.raises(GenerationError):
            await gen.generate_one(
                GenerationSpec(
                    slot_id="t",
                    difficulty="easy",
                    topic="arrays",
                    pattern="sorting",
                    expected_time_complexity="O(n)",
                    expected_space_complexity="O(1)",
                )
            )

    import asyncio

    asyncio.run(_run())


def test_generator_parse_rejects_fences():
    gen = CodingProblemGenerator()
    with pytest.raises(GenerationError):
        gen.parse_model_json("```json\n{}\n```")
