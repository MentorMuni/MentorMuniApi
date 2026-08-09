"""Pre-authored MVP seed content (no AI question generation)."""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from alembic import op


def seed_mvp_coding_content() -> None:
    conn = op.get_bind()

    languages = sa.table(
        "coding_languages",
        sa.column("code", sa.String),
        sa.column("display_name", sa.String),
        sa.column("judge0_language_id", sa.Integer),
        sa.column("version_label", sa.String),
        sa.column("file_extension", sa.String),
        sa.column("time_multiplier", sa.Float),
        sa.column("default_memory_limit_kb", sa.Integer),
        sa.column("starter_template", sa.Text),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        languages,
        [
            {
                "code": "python",
                "display_name": "Python 3",
                "judge0_language_id": 71,
                "version_label": "3.8.1",
                "file_extension": ".py",
                "time_multiplier": 1.0,
                "default_memory_limit_kb": 128000,
                "starter_template": (
                    "import sys\n\ndef solve():\n"
                    "    # Write your solution\n    pass\n\n"
                    "if __name__ == '__main__':\n    solve()\n"
                ),
                "is_active": True,
            },
            {
                "code": "cpp",
                "display_name": "C++",
                "judge0_language_id": 54,
                "version_label": "GCC 9.2.0",
                "file_extension": ".cpp",
                "time_multiplier": 1.0,
                "default_memory_limit_kb": 128000,
                "starter_template": (
                    "#include <bits/stdc++.h>\nusing namespace std;\n\n"
                    "int main() {\n    ios::sync_with_stdio(false);\n"
                    "    cin.tie(nullptr);\n    // Write your solution\n"
                    "    return 0;\n}\n"
                ),
                "is_active": True,
            },
            {
                "code": "java",
                "display_name": "Java",
                "judge0_language_id": 62,
                "version_label": "OpenJDK 13",
                "file_extension": ".java",
                "time_multiplier": 1.5,
                "default_memory_limit_kb": 128000,
                "starter_template": (
                    "import java.util.*;\n\npublic class Main {\n"
                    "    public static void main(String[] args) {\n"
                    "        Scanner sc = new Scanner(System.in);\n"
                    "        // Write your solution\n    }\n}\n"
                ),
                "is_active": True,
            },
        ],
    )

    problem_id = conn.execute(
        sa.text(
            """
            INSERT INTO coding_problems (
                slug, status, company_key, company_name, role_key, role_name,
                difficulty, topic, subtopic, pattern, evidence_confidence, evidence_notes
            ) VALUES (
                :slug, :status, :company_key, :company_name, :role_key, :role_name,
                :difficulty, :topic, :subtopic, :pattern, :evidence_confidence, :evidence_notes
            ) RETURNING id
            """
        ),
        {
            "slug": "two-sum",
            "status": "published",
            "company_key": "microsoft",
            "company_name": "Microsoft",
            "role_key": "software-engineer",
            "role_name": "Software Engineer",
            "difficulty": "easy",
            "topic": "Arrays",
            "subtopic": "Hashing",
            "pattern": "HashMap complement lookup",
            "evidence_confidence": 0.72,
            "evidence_notes": (
                "Commonly appears in early DSA screening rounds for SDE roles; "
                "evidence-based pattern match, not a guarantee of any specific interview."
            ),
        },
    ).scalar_one()

    starter: dict[str, str] = {
        "python": (
            "import sys\n\n"
            "def two_sum(nums, target):\n"
            "    # Return 1-based indices of two numbers that add to target\n"
            "    pass\n\n"
            "def main():\n"
            "    data = sys.stdin.read().strip().split()\n"
            "    if not data:\n"
            "        return\n"
            "    it = iter(data)\n"
            "    n = int(next(it))\n"
            "    nums = [int(next(it)) for _ in range(n)]\n"
            "    target = int(next(it))\n"
            "    i, j = two_sum(nums, target)\n"
            "    print(i, j)\n\n"
            "if __name__ == '__main__':\n"
            "    main()\n"
        ),
        "cpp": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n\n"
            "pair<int,int> twoSum(vector<int>& nums, int target) {\n"
            "    // Return 1-based indices\n"
            "    return {1, 2};\n"
            "}\n\n"
            "int main() {\n"
            "    ios::sync_with_stdio(false);\n"
            "    cin.tie(nullptr);\n"
            "    int n; cin >> n;\n"
            "    vector<int> nums(n);\n"
            "    for (int i = 0; i < n; i++) cin >> nums[i];\n"
            "    int target; cin >> target;\n"
            "    auto [a, b] = twoSum(nums, target);\n"
            "    cout << a << ' ' << b << '\\n';\n"
            "    return 0;\n"
            "}\n"
        ),
        "java": (
            "import java.util.*;\n\n"
            "public class Main {\n"
            "    static int[] twoSum(int[] nums, int target) {\n"
            "        // Return 1-based indices\n"
            "        return new int[]{1, 2};\n"
            "    }\n\n"
            "    public static void main(String[] args) {\n"
            "        Scanner sc = new Scanner(System.in);\n"
            "        int n = sc.nextInt();\n"
            "        int[] nums = new int[n];\n"
            "        for (int i = 0; i < n; i++) nums[i] = sc.nextInt();\n"
            "        int target = sc.nextInt();\n"
            "        int[] ans = twoSum(nums, target);\n"
            "        System.out.println(ans[0] + \" \" + ans[1]);\n"
            "    }\n"
            "}\n"
        ),
    }

    examples: list[dict[str, Any]] = [
        {
            "input": "4\n2 7 11 15\n9",
            "output": "1 2",
            "explanation": "nums[1] + nums[2] = 2 + 7 = 9 (1-based indices).",
        },
        {
            "input": "3\n3 2 4\n6",
            "output": "2 3",
            "explanation": "2 + 4 = 6.",
        },
    ]
    concepts = ["Arrays", "Hashing", "Problem Understanding", "Complexity Analysis"]

    version_id = conn.execute(
        sa.text(
            """
            INSERT INTO coding_problem_versions (
                problem_id, version_number, title, description, difficulty,
                topic, subtopic, pattern, constraints_text, input_format, output_format,
                examples_json, expected_time_complexity, expected_space_complexity,
                expected_approach, concepts_json, starter_code_by_language, weight_policy_json,
                time_limit_ms, memory_limit_kb
            ) VALUES (
                :problem_id, 1, :title, :description, :difficulty,
                :topic, :subtopic, :pattern, :constraints_text, :input_format, :output_format,
                CAST(:examples_json AS jsonb), :expected_time_complexity, :expected_space_complexity,
                :expected_approach, CAST(:concepts_json AS jsonb),
                CAST(:starter_code_by_language AS jsonb), CAST(:weight_policy_json AS jsonb),
                :time_limit_ms, :memory_limit_kb
            ) RETURNING id
            """
        ),
        {
            "problem_id": problem_id,
            "title": "Two Sum",
            "description": (
                "Given an array of integers nums and an integer target, return the "
                "1-based indices of the two numbers such that they add up to target.\n\n"
                "You may assume that each input has exactly one solution, and you may "
                "not use the same element twice.\n\n"
                "You can return the answer in any order (both indices on one line)."
            ),
            "difficulty": "easy",
            "topic": "Arrays",
            "subtopic": "Hashing",
            "pattern": "HashMap complement lookup",
            "constraints_text": (
                "2 <= n <= 100000\n"
                "-10^9 <= nums[i] <= 10^9\n"
                "-10^9 <= target <= 10^9\n"
                "Exactly one valid answer exists."
            ),
            "input_format": (
                "First line: n (array length)\n"
                "Second line: n integers (nums)\n"
                "Third line: target"
            ),
            "output_format": "Two 1-based indices separated by a space.",
            "examples_json": json.dumps(examples),
            "expected_time_complexity": "O(n)",
            "expected_space_complexity": "O(n)",
            "expected_approach": (
                "Single pass with a hash map from value -> index. For each number, "
                "check if target - num was already seen."
            ),
            "concepts_json": json.dumps(concepts),
            "starter_code_by_language": json.dumps(starter),
            "weight_policy_json": json.dumps({"public_share": 0.2, "hidden_share": 0.8}),
            "time_limit_ms": 2000,
            "memory_limit_kb": 128000,
        },
    ).scalar_one()

    conn.execute(
        sa.text("UPDATE coding_problems SET current_version_id = :vid WHERE id = :pid"),
        {"vid": version_id, "pid": problem_id},
    )

    # Public ~20% (2x10); hidden ~80% (4x20)
    cases = [
        ("4\n2 7 11 15\n9", "1 2", False, 10.0, 0),
        ("3\n3 2 4\n6", "2 3", False, 10.0, 1),
        ("2\n3 3\n6", "1 2", True, 20.0, 2),
        ("5\n1 5 3 7 9\n12", "2 5", True, 20.0, 3),
        ("4\n0 4 3 0\n0", "1 4", True, 20.0, 4),
        ("6\n-1 -2 -3 -4 -5 -6\n-8", "2 6", True, 20.0, 5),
    ]
    for inp, out, hidden, weight, order in cases:
        conn.execute(
            sa.text(
                """
                INSERT INTO coding_test_cases (
                    problem_version_id, input, expected_output, is_hidden, weight, order_index
                ) VALUES (
                    :vid, :input, :expected_output, :is_hidden, :weight, :order_index
                )
                """
            ),
            {
                "vid": version_id,
                "input": inp,
                "expected_output": out,
                "is_hidden": hidden,
                "weight": weight,
                "order_index": order,
            },
        )

    ref_py = (
        "import sys\n\n"
        "def two_sum(nums, target):\n"
        "    seen = {}\n"
        "    for i, x in enumerate(nums):\n"
        "        need = target - x\n"
        "        if need in seen:\n"
        "            return seen[need] + 1, i + 1\n"
        "        seen[x] = i\n"
        "    raise ValueError('no solution')\n\n"
        "def main():\n"
        "    data = sys.stdin.read().strip().split()\n"
        "    it = iter(data)\n"
        "    n = int(next(it))\n"
        "    nums = [int(next(it)) for _ in range(n)]\n"
        "    target = int(next(it))\n"
        "    i, j = two_sum(nums, target)\n"
        "    print(i, j)\n\n"
        "if __name__ == '__main__':\n"
        "    main()\n"
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO coding_reference_solutions
                (problem_version_id, language_code, source_code, notes)
            VALUES (:vid, 'python', :src, :notes)
            """
        ),
        {
            "vid": version_id,
            "src": ref_py,
            "notes": "Backend-only reference; never expose to students.",
        },
    )

    assessment_id = conn.execute(
        sa.text(
            """
            INSERT INTO coding_assessments (
                slug, title, organization_id, company_key, company_name,
                role_key, role_name, difficulty, duration_minutes, status,
                allowed_languages_json, evidence_confidence
            ) VALUES (
                :slug, :title, NULL, :company_key, :company_name,
                :role_key, :role_name, :difficulty, 45, 'active',
                CAST(:langs AS jsonb), :evidence_confidence
            ) RETURNING id
            """
        ),
        {
            "slug": "practice-two-sum",
            "title": "Practice Coding Round — Two Sum",
            "company_key": "microsoft",
            "company_name": "Microsoft",
            "role_key": "software-engineer",
            "role_name": "Software Engineer",
            "difficulty": "easy",
            "langs": json.dumps(["python", "cpp", "java"]),
            "evidence_confidence": 0.72,
        },
    ).scalar_one()

    conn.execute(
        sa.text(
            """
            INSERT INTO coding_assessment_problems
                (assessment_id, problem_id, order_index, points)
            VALUES (:aid, :pid, 0, 100)
            """
        ),
        {"aid": assessment_id, "pid": problem_id},
    )
