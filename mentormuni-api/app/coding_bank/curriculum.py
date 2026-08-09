"""Configurable ~50 problem generation matrix (placement_v1).

Does not hardcode 50 LLM prompts — each cell is a GenerationSpec.
Distribution is approximate and editable via override JSON.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from app.coding_bank import CURRICULUM_VERSION

Difficulty = Literal["easy", "medium", "hard"]


@dataclass(frozen=True)
class GenerationSpec:
    slot_id: str
    difficulty: Difficulty
    topic: str
    pattern: str
    expected_time_complexity: str
    expected_space_complexity: str
    notes: str = ""


@dataclass
class CurriculumConfig:
    version: str = CURRICULUM_VERSION
    target_count: int = 50
    specs: list[GenerationSpec] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "target_count": self.target_count,
            "specs": [asdict(s) for s in self.specs],
        }


# Placement-weighted distribution (~50). Counts are intentional but not sacred.
_MATRIX: list[tuple[str, str, Difficulty, str, str, int]] = [
    # topic, pattern, difficulty, time, space, count
    ("arrays", "prefix-sum", "easy", "O(n)", "O(1)", 1),
    ("arrays", "prefix-sum", "medium", "O(n)", "O(n)", 1),
    ("arrays", "sorting", "easy", "O(n log n)", "O(1)", 1),
    ("arrays", "kadane", "medium", "O(n)", "O(1)", 1),
    ("arrays", "two-pointers", "medium", "O(n)", "O(1)", 1),
    ("strings", "frequency", "easy", "O(n)", "O(1)", 1),
    ("strings", "two-pointers", "easy", "O(n)", "O(1)", 1),
    ("strings", "sliding-window", "medium", "O(n)", "O(k)", 1),
    ("strings", "string-matching", "medium", "O(n)", "O(1)", 1),
    ("hashing", "hash-map", "easy", "O(n)", "O(n)", 2),
    ("hashing", "hash-set", "easy", "O(n)", "O(n)", 1),
    ("hashing", "counting", "medium", "O(n)", "O(n)", 1),
    ("hashing", "anagram", "easy", "O(n)", "O(1)", 1),
    ("two-pointers", "pair-sum", "easy", "O(n)", "O(1)", 1),
    ("two-pointers", "opposite-ends", "easy", "O(n)", "O(1)", 1),
    ("two-pointers", "fast-slow", "medium", "O(n)", "O(1)", 1),
    ("sliding-window", "fixed-window", "easy", "O(n)", "O(1)", 1),
    ("sliding-window", "variable-window", "medium", "O(n)", "O(k)", 2),
    ("binary-search", "classic", "easy", "O(log n)", "O(1)", 1),
    ("binary-search", "answer-space", "medium", "O(n log m)", "O(1)", 1),
    ("binary-search", "rotated-array", "medium", "O(log n)", "O(1)", 1),
    ("stack", "monotonic-stack", "medium", "O(n)", "O(n)", 1),
    ("stack", "next-greater", "medium", "O(n)", "O(n)", 1),
    ("stack", "parentheses", "easy", "O(n)", "O(n)", 1),
    ("queue", "bfs-queue", "medium", "O(n)", "O(n)", 1),
    ("queue", "sliding-window-max", "hard", "O(n)", "O(k)", 1),
    ("linked-list", "reversal", "easy", "O(n)", "O(1)", 1),
    ("linked-list", "two-pointers", "medium", "O(n)", "O(1)", 1),
    ("linked-list", "merge", "medium", "O(n)", "O(1)", 1),
    ("trees", "dfs", "easy", "O(n)", "O(h)", 1),
    ("trees", "bfs", "easy", "O(n)", "O(n)", 1),
    ("trees", "bst", "medium", "O(n)", "O(h)", 1),
    ("trees", "path-sum", "medium", "O(n)", "O(h)", 1),
    ("graphs", "bfs", "medium", "O(V+E)", "O(V)", 1),
    ("graphs", "dfs", "medium", "O(V+E)", "O(V)", 1),
    ("graphs", "topo-sort", "hard", "O(V+E)", "O(V)", 1),
    ("graphs", "shortest-path", "hard", "O((V+E) log V)", "O(V)", 1),
    ("greedy", "interval", "medium", "O(n log n)", "O(1)", 1),
    ("greedy", "selection", "easy", "O(n log n)", "O(1)", 1),
    ("recursion", "divide-conquer", "medium", "O(n log n)", "O(log n)", 1),
    ("backtracking", "permutations", "medium", "O(n!)", "O(n)", 1),
    ("backtracking", "subsets", "medium", "O(2^n)", "O(n)", 1),
    ("backtracking", "constraint-search", "hard", "O(k^n)", "O(n)", 1),
    ("dynamic-programming", "1d-dp", "easy", "O(n)", "O(n)", 1),
    ("dynamic-programming", "1d-dp", "medium", "O(n)", "O(1)", 1),
    ("dynamic-programming", "knapsack", "medium", "O(nW)", "O(nW)", 1),
    ("dynamic-programming", "grid-dp", "medium", "O(nm)", "O(nm)", 1),
    ("dynamic-programming", "lis", "hard", "O(n log n)", "O(n)", 1),
]


def build_placement_curriculum_v1() -> CurriculumConfig:
    specs: list[GenerationSpec] = []
    seq = 0
    for topic, pattern, difficulty, t_c, s_c, count in _MATRIX:
        for i in range(count):
            seq += 1
            specs.append(
                GenerationSpec(
                    slot_id=f"{CURRICULUM_VERSION}-{seq:02d}-{topic}-{pattern}-{difficulty}"
                    + (f"-{i+1}" if count > 1 else ""),
                    difficulty=difficulty,  # type: ignore[arg-type]
                    topic=topic,
                    pattern=pattern,
                    expected_time_complexity=t_c,
                    expected_space_complexity=s_c,
                    notes=f"Canonical placement slot; do not company-specialize.",
                )
            )
    return CurriculumConfig(version=CURRICULUM_VERSION, target_count=len(specs), specs=specs)


def curriculum_from_override(data: dict[str, Any] | None) -> CurriculumConfig:
    """Load curriculum from config_json override, else default matrix."""
    if not data or not data.get("specs"):
        return build_placement_curriculum_v1()
    specs = [
        GenerationSpec(
            slot_id=str(s["slot_id"]),
            difficulty=s["difficulty"],
            topic=str(s["topic"]),
            pattern=str(s["pattern"]),
            expected_time_complexity=str(s["expected_time_complexity"]),
            expected_space_complexity=str(s["expected_space_complexity"]),
            notes=str(s.get("notes") or ""),
        )
        for s in data["specs"]
    ]
    return CurriculumConfig(
        version=str(data.get("version") or CURRICULUM_VERSION),
        target_count=int(data.get("target_count") or len(specs)),
        specs=specs,
    )


def pattern_distribution(cfg: CurriculumConfig | None = None) -> dict[str, int]:
    cfg = cfg or build_placement_curriculum_v1()
    out: dict[str, int] = {}
    for s in cfg.specs:
        key = f"{s.topic}/{s.pattern}"
        out[key] = out.get(key, 0) + 1
    return out
