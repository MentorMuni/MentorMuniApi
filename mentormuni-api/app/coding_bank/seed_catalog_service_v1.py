"""SERVICE-company OA style coding bank (v1).

Original campus-framed problems training TCS NQT / Infosys / Accenture /
Nagarro / Persistent / Dassault / Impetus skill patterns — not FAANG-hard,
not proprietary company wording.
Each entry validates as GeneratedProblemContract.
"""

from __future__ import annotations


def _starter_trio(py_body: str, cpp_body: str, java_body: str) -> list[dict]:
    return [
        {"language": "python", "code": py_body.strip() + "\n"},
        {"language": "cpp", "code": cpp_body.strip() + "\n"},
        {"language": "java", "code": java_body.strip() + "\n"},
    ]


def _tc(
    inp: str,
    out: str,
    *,
    is_hidden: bool = False,
    category: str = "normal",
    weight: float = 1.0,
    order_index: int | None = None,
) -> dict:
    d: dict = {
        "input": inp,
        "expected_output": out,
        "is_hidden": is_hidden,
        "weight": weight,
        "category": category,
    }
    if order_index is not None:
        d["order_index"] = order_index
    return d


_LANGS = ["python", "cpp", "java"]

_PY_STUB = '''
import sys

def solve():
    data = sys.stdin.read().split()
    # TODO: implement
    pass

if __name__ == "__main__":
    solve()
'''

_CPP_STUB = '''
#include <bits/stdc++.h>
using namespace std;
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    // TODO: implement
    return 0;
}
'''

_JAVA_STUB = '''
import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        // TODO: implement
    }
}
'''


SERVICE_BANK_V1: list[dict] = [
    # 1 — Reverse sentence tokens
    {
        "title": "Hostel Notice Word Flip",
        "slug": "hostel-notice-word-flip",
        "difficulty": "easy",
        "topics": ["strings"],
        "patterns": ["reverse", "tokenization"],
        "problem_statement": (
            "The hostel warden pasted a notice as a single line of words separated by spaces. "
            "For the evening display board, the mess committee needs the words printed in reverse "
            "order (last word first). Punctuation is not present; tokens are space-separated only. "
            "Preserve each word's characters; only reorder the tokens."
        ),
        "input_format": (
            "A single line containing one or more words separated by single spaces."
        ),
        "output_format": (
            "One line: the words in reverse order, separated by single spaces."
        ),
        "constraints": (
            "1 <= number of words <= 1000\n"
            "1 <= length of each word <= 50\n"
            "Words contain only lowercase and uppercase English letters.\n"
            "No leading/trailing spaces; words separated by exactly one space."
        ),
        "examples": [
            {
                "input": "mess closes early today",
                "output": "today early closes mess",
                "explanation": "Four words; reverse token order.",
            },
            {
                "input": "placement",
                "output": "placement",
                "explanation": "Single word stays unchanged.",
            },
        ],
        "explanation": (
            "Split the line on spaces into a list of tokens, reverse the list, "
            "then join with spaces. Time is linear in the total characters."
        ),
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(n)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(_PY_STUB, _CPP_STUB, _JAVA_STUB),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "words = sys.stdin.read().strip().split()\n"
                    "print(' '.join(reversed(words)))\n"
                ),
                "notes": "Split, reverse tokens, join.",
            }
        ],
        "candidate_test_cases": [
            _tc("mess closes early today", "today early closes mess", category="normal", order_index=0),
            _tc("placement", "placement", category="single", order_index=1),
            _tc("a b", "b a", category="minimum", order_index=2),
            _tc("Open Lab Door Now Please", "Please Now Door Lab Open", category="normal", is_hidden=True, order_index=3),
            _tc("x", "x", category="boundary", order_index=4),
            _tc("one two three four five", "five four three two one", category="normal", is_hidden=True, order_index=5),
            _tc("Campus Drive Round One", "One Round Drive Campus", category="normal", is_hidden=True, order_index=6),
            _tc("aa bb cc dd ee ff gg hh", "hh gg ff ee dd cc bb aa", category="maximum", is_hidden=True, order_index=7),
        ],
    },
    # 2 — Palindrome string
    {
        "title": "ID Badge Palindrome Check",
        "slug": "id-badge-palindrome-check",
        "difficulty": "easy",
        "topics": ["strings"],
        "patterns": ["palindrome", "two-pointers"],
        "problem_statement": (
            "At the campus gate, temporary visitor badges print a short alphanumeric code. "
            "Security wants a quick check: is the code a palindrome (reads the same forwards "
            "and backwards)? Comparison is case-sensitive and must use the full string as given."
        ),
        "input_format": "A single line containing the badge string S (no spaces).",
        "output_format": 'Print "YES" if S is a palindrome, otherwise "NO".',
        "constraints": (
            "1 <= |S| <= 1e5\n"
            "S contains only letters and digits."
        ),
        "examples": [
            {
                "input": "level",
                "output": "YES",
                "explanation": "Reads the same forwards and backwards.",
            },
            {
                "input": "Campus",
                "output": "NO",
                "explanation": "C vs s differ; case matters.",
            },
        ],
        "explanation": (
            "Compare characters from both ends moving inward, or compare the string "
            "with its reverse. Early exit on mismatch."
        ),
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(_PY_STUB, _CPP_STUB, _JAVA_STUB),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "s = sys.stdin.read().strip()\n"
                    "print('YES' if s == s[::-1] else 'NO')\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("level", "YES", category="normal", order_index=0),
            _tc("Campus", "NO", category="normal", order_index=1),
            _tc("a", "YES", category="single", order_index=2),
            _tc("aa", "YES", category="minimum", order_index=3),
            _tc("ab", "NO", category="minimum", is_hidden=True, order_index=4),
            _tc("12321", "YES", category="normal", is_hidden=True, order_index=5),
            _tc("AbA", "YES", category="boundary", order_index=6),
            _tc("AbcBA", "NO", category="boundary", is_hidden=True, order_index=7),
            _tc("zzzzzzzzzz", "YES", category="maximum", is_hidden=True, order_index=8),
        ],
    },
    # 3 — Character frequency
    {
        "title": "Lab Attendance Letter Tally",
        "slug": "lab-attendance-letter-tally",
        "difficulty": "easy",
        "topics": ["strings", "hashing"],
        "patterns": ["frequency-count"],
        "problem_statement": (
            "A lab coordinator logged today's attendance as one continuous lowercase string "
            "(each letter is a coded seat marker). Print the frequency of every distinct "
            "character that appears, in alphabetical order of the character."
        ),
        "input_format": "A single line: lowercase string S.",
        "output_format": (
            "For each distinct character in alphabetical order, one line:\n"
            "char count\n"
            "(space-separated char and integer count)."
        ),
        "constraints": (
            "1 <= |S| <= 1e5\n"
            "S contains only lowercase English letters a-z."
        ),
        "examples": [
            {
                "input": "banana",
                "output": "a 3\nb 1\nn 2",
                "explanation": "a appears 3 times, b once, n twice.",
            },
            {
                "input": "zzz",
                "output": "z 3",
                "explanation": "Only z appears.",
            },
        ],
        "explanation": (
            "Count with an array of size 26 or a hash map, then emit non-zero counts "
            "from 'a' to 'z'."
        ),
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(_PY_STUB, _CPP_STUB, _JAVA_STUB),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "from collections import Counter\n"
                    "s = sys.stdin.read().strip()\n"
                    "c = Counter(s)\n"
                    "for ch in sorted(c):\n"
                    "    print(ch, c[ch])\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("banana", "a 3\nb 1\nn 2", category="normal", order_index=0),
            _tc("zzz", "z 3", category="single", order_index=1),
            _tc("a", "a 1", category="minimum", order_index=2),
            _tc("abcabc", "a 2\nb 2\nc 2", category="normal", is_hidden=True, order_index=3),
            _tc("aabbcc", "a 2\nb 2\nc 2", category="duplicates", order_index=4),
            _tc("zyxzyx", "x 2\ny 2\nz 2", category="boundary", is_hidden=True, order_index=5),
            _tc("mississippi", "i 4\nm 1\np 2\ns 4", category="normal", is_hidden=True, order_index=6),
            _tc("aaaaaaaaaa", "a 10", category="maximum", is_hidden=True, order_index=7),
        ],
    },
    # 4 — Max occurring character
    {
        "title": "Feedback Form Dominant Letter",
        "slug": "feedback-form-dominant-letter",
        "difficulty": "easy",
        "topics": ["strings", "hashing"],
        "patterns": ["frequency-count", "max-frequency"],
        "problem_statement": (
            "After a guest lecture, students typed free-text feedback as one lowercase string. "
            "The analytics desk needs the character that occurs most often. If several characters "
            "share the maximum frequency, choose the one that is smallest alphabetically."
        ),
        "input_format": "A single line: lowercase string S.",
        "output_format": "One line: the dominant character.",
        "constraints": (
            "1 <= |S| <= 1e5\n"
            "S contains only lowercase English letters."
        ),
        "examples": [
            {
                "input": "abracadabra",
                "output": "a",
                "explanation": "a appears 5 times, more than any other letter.",
            },
            {
                "input": "xyz",
                "output": "x",
                "explanation": "All frequency 1; pick lexicographically smallest.",
            },
        ],
        "explanation": (
            "Count frequencies, track the max count, and among characters with that count "
            "pick the smallest letter."
        ),
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(_PY_STUB, _CPP_STUB, _JAVA_STUB),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "from collections import Counter\n"
                    "s = sys.stdin.read().strip()\n"
                    "c = Counter(s)\n"
                    "best = min((-c[ch], ch) for ch in c)\n"
                    "print(best[1])\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("abracadabra", "a", category="normal", order_index=0),
            _tc("xyz", "x", category="boundary", order_index=1),
            _tc("b", "b", category="single", order_index=2),
            _tc("zzzz", "z", category="minimum", order_index=3),
            _tc("aabb", "a", category="duplicates", is_hidden=True, order_index=4),
            _tc("ccccbbbbaaaa", "a", category="normal", is_hidden=True, order_index=5),
            _tc("hello", "l", category="normal", is_hidden=True, order_index=6),
            _tc("mnopq", "m", category="boundary", is_hidden=True, order_index=7),
        ],
    },
    # 5 — Reverse array
    {
        "title": "Queue Token Reverse Order",
        "slug": "queue-token-reverse-order",
        "difficulty": "easy",
        "topics": ["arrays"],
        "patterns": ["reverse"],
        "problem_statement": (
            "Students lined up for the placement portal with integer token numbers. "
            "The volunteer mistakenly wrote them front-to-back. Reverse the sequence "
            "of tokens and print the corrected order."
        ),
        "input_format": (
            "First line: integer n\n"
            "Second line: n space-separated integers"
        ),
        "output_format": "One line: n integers in reversed order, space-separated.",
        "constraints": (
            "1 <= n <= 1e5\n"
            "-1e9 <= a[i] <= 1e9"
        ),
        "examples": [
            {
                "input": "4\n10 20 30 40",
                "output": "40 30 20 10",
                "explanation": "Array reversed end to start.",
            },
            {
                "input": "1\n7",
                "output": "7",
                "explanation": "Single element unchanged.",
            },
        ],
        "explanation": "Two-pointer swap from ends, or use a reverse utility, then print.",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(_PY_STUB, _CPP_STUB, _JAVA_STUB),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "data = list(map(int, sys.stdin.read().split()))\n"
                    "n = data[0]\n"
                    "a = data[1:1+n]\n"
                    "print(' '.join(map(str, reversed(a))))\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("4\n10 20 30 40", "40 30 20 10", category="normal", order_index=0),
            _tc("1\n7", "7", category="single", order_index=1),
            _tc("2\n1 2", "2 1", category="minimum", order_index=2),
            _tc("5\n-1 -2 -3 -4 -5", "-5 -4 -3 -2 -1", category="negative", is_hidden=True, order_index=3),
            _tc("3\n0 0 0", "0 0 0", category="duplicates", order_index=4),
            _tc("6\n9 8 7 6 5 4", "4 5 6 7 8 9", category="normal", is_hidden=True, order_index=5),
            _tc("5\n1000000000 -1000000000 0 1 -1", "-1 1 0 -1000000000 1000000000", category="boundary", is_hidden=True, order_index=6),
            _tc("3\n5 1 9", "9 1 5", category="normal", is_hidden=True, order_index=7),
        ],
    },
    # 6 — Sort array ascending
    {
        "title": "Club Points Ascending Sort",
        "slug": "club-points-ascending-sort",
        "difficulty": "easy",
        "topics": ["arrays"],
        "patterns": ["sorting"],
        "problem_statement": (
            "The cultural club collected event points for each volunteer as integers. "
            "Before publishing the leaderboard draft, sort the points in non-decreasing "
            "(ascending) order and print them."
        ),
        "input_format": (
            "First line: integer n\n"
            "Second line: n space-separated integers"
        ),
        "output_format": "One line: n integers sorted ascending, space-separated.",
        "constraints": (
            "1 <= n <= 1e5\n"
            "-1e9 <= a[i] <= 1e9"
        ),
        "examples": [
            {
                "input": "5\n3 1 4 1 5",
                "output": "1 1 3 4 5",
                "explanation": "Sorted non-decreasing.",
            },
            {
                "input": "3\n10 9 8",
                "output": "8 9 10",
                "explanation": "Reverse-sorted input becomes ascending.",
            },
        ],
        "explanation": "Use an efficient sort (library sort is fine for this OA skill check).",
        "expected_time_complexity": "O(n log n)",
        "expected_space_complexity": "O(n)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(_PY_STUB, _CPP_STUB, _JAVA_STUB),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "data = list(map(int, sys.stdin.read().split()))\n"
                    "n = data[0]\n"
                    "a = sorted(data[1:1+n])\n"
                    "print(' '.join(map(str, a)))\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("5\n3 1 4 1 5", "1 1 3 4 5", category="normal", order_index=0),
            _tc("3\n10 9 8", "8 9 10", category="normal", order_index=1),
            _tc("1\n42", "42", category="single", order_index=2),
            _tc("4\n-5 -1 -3 -2", "-5 -3 -2 -1", category="negative", is_hidden=True, order_index=3),
            _tc("4\n2 2 2 2", "2 2 2 2", category="duplicates", order_index=4),
            _tc("6\n0 -1 5 3 -2 4", "-2 -1 0 3 4 5", category="boundary", is_hidden=True, order_index=5),
            _tc("2\n100 -100", "-100 100", category="minimum", is_hidden=True, order_index=6),
            _tc("5\n9 7 5 3 1", "1 3 5 7 9", category="maximum", is_hidden=True, order_index=7),
        ],
    },
    # 7 — Min and max
    {
        "title": "Temperature Logger Extremes",
        "slug": "temperature-logger-extremes",
        "difficulty": "easy",
        "topics": ["arrays"],
        "patterns": ["linear-scan", "min-max"],
        "problem_statement": (
            "The IoT lab recorded n temperature readings for the day. Report the minimum "
            "and maximum values from the list."
        ),
        "input_format": (
            "First line: integer n\n"
            "Second line: n space-separated integers"
        ),
        "output_format": "One line: min max (space-separated).",
        "constraints": (
            "1 <= n <= 1e5\n"
            "-1e9 <= a[i] <= 1e9"
        ),
        "examples": [
            {
                "input": "5\n3 -1 7 0 4",
                "output": "-1 7",
                "explanation": "Smallest is -1, largest is 7.",
            },
            {
                "input": "1\n9",
                "output": "9 9",
                "explanation": "Only one value is both min and max.",
            },
        ],
        "explanation": "Single pass tracking running min and max.",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(_PY_STUB, _CPP_STUB, _JAVA_STUB),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "data = list(map(int, sys.stdin.read().split()))\n"
                    "n = data[0]\n"
                    "a = data[1:1+n]\n"
                    "print(min(a), max(a))\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("5\n3 -1 7 0 4", "-1 7", category="normal", order_index=0),
            _tc("1\n9", "9 9", category="single", order_index=1),
            _tc("2\n5 5", "5 5", category="duplicates", order_index=2),
            _tc("4\n-10 -20 -5 -1", "-20 -1", category="negative", is_hidden=True, order_index=3),
            _tc("3\n0 0 1", "0 1", category="boundary", order_index=4),
            _tc("6\n100 1 50 99 2 50", "1 100", category="normal", is_hidden=True, order_index=5),
            _tc("2\n-1000000000 1000000000", "-1000000000 1000000000", category="maximum", is_hidden=True, order_index=6),
            _tc("3\n8 3 8", "3 8", category="minimum", is_hidden=True, order_index=7),
        ],
    },
    # 8 — Sum of array
    {
        "title": "Canteen Bill Total",
        "slug": "canteen-bill-total",
        "difficulty": "easy",
        "topics": ["arrays", "math"],
        "patterns": ["prefix-sum", "aggregation"],
        "problem_statement": (
            "A student group ordered n items at the canteen; each item has an integer price. "
            "Compute the total bill (sum of all prices)."
        ),
        "input_format": (
            "First line: integer n\n"
            "Second line: n space-separated integers"
        ),
        "output_format": "One line: the sum as a single integer.",
        "constraints": (
            "1 <= n <= 1e5\n"
            "-1e6 <= a[i] <= 1e6\n"
            "Use a 64-bit integer for the sum."
        ),
        "examples": [
            {
                "input": "4\n10 20 5 15",
                "output": "50",
                "explanation": "10+20+5+15=50.",
            },
            {
                "input": "3\n-2 5 -1",
                "output": "2",
                "explanation": "Negative prices allowed in the mock data.",
            },
        ],
        "explanation": "Accumulate into a long integer while scanning the array once.",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(_PY_STUB, _CPP_STUB, _JAVA_STUB),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "data = list(map(int, sys.stdin.read().split()))\n"
                    "n = data[0]\n"
                    "print(sum(data[1:1+n]))\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("4\n10 20 5 15", "50", category="normal", order_index=0),
            _tc("3\n-2 5 -1", "2", category="negative", order_index=1),
            _tc("1\n0", "0", category="single", order_index=2),
            _tc("2\n1000000 1000000", "2000000", category="maximum", is_hidden=True, order_index=3),
            _tc("5\n1 1 1 1 1", "5", category="duplicates", order_index=4),
            _tc("3\n-5 -5 -5", "-15", category="boundary", is_hidden=True, order_index=5),
            _tc("6\n7 0 -3 4 2 -1", "9", category="normal", is_hidden=True, order_index=6),
            _tc("2\n9 -9", "0", category="minimum", is_hidden=True, order_index=7),
        ],
    },
    # 9 — Matrix addition
    {
        "title": "Two Lab Grid Merge",
        "slug": "two-lab-grid-merge",
        "difficulty": "easy",
        "topics": ["arrays", "math"],
        "patterns": ["matrix-traversal", "elementwise-add"],
        "problem_statement": (
            "Two identical-size grids of sensor counts (matrices A and B of size r x c) "
            "must be merged by adding corresponding cells. Print the resulting matrix."
        ),
        "input_format": (
            "First line: integers r c\n"
            "Next r lines: c integers each (matrix A)\n"
            "Next r lines: c integers each (matrix B)"
        ),
        "output_format": (
            "r lines with c space-separated integers each: matrix A+B."
        ),
        "constraints": (
            "1 <= r, c <= 100\n"
            "-1000 <= A[i][j], B[i][j] <= 1000"
        ),
        "examples": [
            {
                "input": "2 2\n1 2\n3 4\n5 6\n7 8",
                "output": "6 8\n10 12",
                "explanation": "Element-wise sums.",
            },
            {
                "input": "1 3\n1 0 -1\n2 3 4",
                "output": "3 3 3",
                "explanation": "Single-row matrices.",
            },
        ],
        "explanation": "Nested loops over rows and columns adding A[i][j]+B[i][j].",
        "expected_time_complexity": "O(r*c)",
        "expected_space_complexity": "O(r*c)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(_PY_STUB, _CPP_STUB, _JAVA_STUB),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "data = list(map(int, sys.stdin.read().split()))\n"
                    "r, c = data[0], data[1]\n"
                    "idx = 2\n"
                    "A = []\n"
                    "for _ in range(r):\n"
                    "    A.append(data[idx:idx+c]); idx += c\n"
                    "B = []\n"
                    "for _ in range(r):\n"
                    "    B.append(data[idx:idx+c]); idx += c\n"
                    "for i in range(r):\n"
                    "    print(' '.join(str(A[i][j] + B[i][j]) for j in range(c)))\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("2 2\n1 2\n3 4\n5 6\n7 8", "6 8\n10 12", category="normal", order_index=0),
            _tc("1 3\n1 0 -1\n2 3 4", "3 3 3", category="boundary", order_index=1),
            _tc("1 1\n5\n7", "12", category="minimum", order_index=2),
            _tc("2 1\n1\n2\n3\n4", "4\n6", category="single", is_hidden=True, order_index=3),
            _tc("2 2\n-1 -2\n-3 -4\n1 2\n3 4", "0 0\n0 0", category="negative", order_index=4),
            _tc("3 3\n1 1 1\n1 1 1\n1 1 1\n2 2 2\n2 2 2\n2 2 2", "3 3 3\n3 3 3\n3 3 3", category="duplicates", is_hidden=True, order_index=5),
            _tc("2 3\n0 0 0\n0 0 0\n9 8 7\n6 5 4", "9 8 7\n6 5 4", category="normal", is_hidden=True, order_index=6),
            _tc("1 2\n1000 -1000\n-1000 1000", "0 0", category="maximum", is_hidden=True, order_index=7),
        ],
    },
    # 10 — Sliding window fixed k sum max/min
    {
        "title": "Study Streak Window Scores",
        "slug": "study-streak-window-scores",
        "difficulty": "medium",
        "topics": ["arrays"],
        "patterns": ["sliding-window-fixed"],
        "problem_statement": (
            "A mentor tracked daily practice scores as an array of n integers. For a fixed "
            "window length k (k consecutive days), find both the maximum and the minimum "
            "sum among all contiguous windows of size k. Print max_sum and min_sum."
        ),
        "input_format": (
            "First line: integers n k\n"
            "Second line: n space-separated integers"
        ),
        "output_format": "One line: max_sum min_sum (space-separated).",
        "constraints": (
            "1 <= k <= n <= 1e5\n"
            "-1e6 <= a[i] <= 1e6"
        ),
        "examples": [
            {
                "input": "5 3\n1 2 3 4 5",
                "output": "12 6",
                "explanation": "Windows: 1+2+3=6, 2+3+4=9, 3+4+5=12 → max 12 min 6.",
            },
            {
                "input": "4 2\n-1 4 -2 3",
                "output": "3 1",
                "explanation": "Windows: -1+4=3, 4+-2=2, -2+3=1 → max 3 min 1.",
            },
        ],
        "explanation": (
            "Compute the first window sum of k elements, then slide: add next, subtract "
            "leaving element; track max and min of these sums."
        ),
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(_PY_STUB, _CPP_STUB, _JAVA_STUB),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "data = list(map(int, sys.stdin.read().split()))\n"
                    "n, k = data[0], data[1]\n"
                    "a = data[2:2+n]\n"
                    "s = sum(a[:k])\n"
                    "mx = mn = s\n"
                    "for i in range(k, n):\n"
                    "    s += a[i] - a[i-k]\n"
                    "    if s > mx: mx = s\n"
                    "    if s < mn: mn = s\n"
                    "print(mx, mn)\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("5 3\n1 2 3 4 5", "12 6", category="normal", order_index=0),
            _tc("4 2\n-1 4 -2 3", "3 1", category="negative", order_index=1),
            _tc("3 3\n1 2 3", "6 6", category="boundary", order_index=2),
            _tc("1 1\n5", "5 5", category="minimum", order_index=3),
            _tc("6 1\n9 1 8 2 7 3", "9 1", category="single", is_hidden=True, order_index=4),
            _tc("5 2\n0 0 0 0 0", "0 0", category="duplicates", order_index=5),
            _tc("7 4\n2 -1 3 5 -2 4 1", "10 5", category="normal", is_hidden=True, order_index=6),
            _tc("5 5\n-5 -4 -3 -2 -1", "-15 -15", category="maximum", is_hidden=True, order_index=7),
        ],
    },
    # 11 — Remove duplicate characters order preserved
    {
        "title": "Unique Club Initials Strip",
        "slug": "unique-club-initials-strip",
        "difficulty": "easy",
        "topics": ["strings", "hashing"],
        "patterns": ["deduplicate", "order-preserve"],
        "problem_statement": (
            "Club registration codes are lowercase strings that may repeat letters. "
            "Build a cleaned code by removing duplicate characters while keeping the "
            "first occurrence of each character (order preserved)."
        ),
        "input_format": "A single line: lowercase string S.",
        "output_format": "One line: the string after removing later duplicates.",
        "constraints": (
            "1 <= |S| <= 1e5\n"
            "S contains only lowercase English letters."
        ),
        "examples": [
            {
                "input": "aabbcc",
                "output": "abc",
                "explanation": "Keep first a, first b, first c.",
            },
            {
                "input": "bacbac",
                "output": "bac",
                "explanation": "Order of first appearances: b, a, c.",
            },
        ],
        "explanation": (
            "Scan left to right; append a character only if not seen before; "
            "track seen with a set or boolean array."
        ),
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(_PY_STUB, _CPP_STUB, _JAVA_STUB),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "s = sys.stdin.read().strip()\n"
                    "seen = set()\n"
                    "out = []\n"
                    "for ch in s:\n"
                    "    if ch not in seen:\n"
                    "        seen.add(ch)\n"
                    "        out.append(ch)\n"
                    "print(''.join(out))\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("aabbcc", "abc", category="normal", order_index=0),
            _tc("bacbac", "bac", category="normal", order_index=1),
            _tc("a", "a", category="single", order_index=2),
            _tc("aaaa", "a", category="duplicates", order_index=3),
            _tc("abc", "abc", category="boundary", is_hidden=True, order_index=4),
            _tc("zzzzzyyyyyxxxxx", "zyx", category="maximum", is_hidden=True, order_index=5),
            _tc("mississippi", "misp", category="normal", is_hidden=True, order_index=6),
            _tc("abababab", "ab", category="minimum", is_hidden=True, order_index=7),
        ],
    },
    # 12 — Anagram check
    {
        "title": "Team Name Anagram Match",
        "slug": "team-name-anagram-match",
        "difficulty": "easy",
        "topics": ["strings", "hashing"],
        "patterns": ["anagram", "frequency-count"],
        "problem_statement": (
            "Two project teams proposed names as lowercase strings A and B. "
            "Decide whether one name is an anagram of the other (same letters with "
            "the same frequencies, possibly different order)."
        ),
        "input_format": (
            "First line: string A\n"
            "Second line: string B"
        ),
        "output_format": 'Print "YES" if they are anagrams, otherwise "NO".',
        "constraints": (
            "1 <= |A|, |B| <= 1e5\n"
            "A and B contain only lowercase English letters."
        ),
        "examples": [
            {
                "input": "listen\nsilent",
                "output": "YES",
                "explanation": "Same multiset of letters.",
            },
            {
                "input": "apple\npaper",
                "output": "NO",
                "explanation": "Different letter counts.",
            },
        ],
        "explanation": (
            "If lengths differ, answer NO. Otherwise compare character frequency maps "
            "(or sort both strings and compare)."
        ),
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(_PY_STUB, _CPP_STUB, _JAVA_STUB),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "from collections import Counter\n"
                    "lines = sys.stdin.read().strip().splitlines()\n"
                    "a, b = lines[0].strip(), lines[1].strip()\n"
                    "print('YES' if Counter(a) == Counter(b) else 'NO')\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("listen\nsilent", "YES", category="normal", order_index=0),
            _tc("apple\npaper", "NO", category="normal", order_index=1),
            _tc("a\na", "YES", category="single", order_index=2),
            _tc("a\nb", "NO", category="minimum", order_index=3),
            _tc("aabb\nbaba", "YES", category="duplicates", is_hidden=True, order_index=4),
            _tc("abc\nab", "NO", category="boundary", is_hidden=True, order_index=5),
            _tc("zzzz\nzzzz", "YES", category="maximum", is_hidden=True, order_index=6),
            _tc("campus\nsumpac", "YES", category="normal", is_hidden=True, order_index=7),
        ],
    },
    # 13 — Digit sum and reverse digits
    {
        "title": "Roll Number Digit Drill",
        "slug": "roll-number-digit-drill",
        "difficulty": "easy",
        "topics": ["math"],
        "patterns": ["digit-sum", "digit-reverse"],
        "problem_statement": (
            "Given a non-negative integer N from a mock roll-number generator, print two values: "
            "the sum of its decimal digits, and the integer formed by reversing its digits "
            "(ignore leading zeros in the reversed number; if N is 0, reversed is 0)."
        ),
        "input_format": "A single integer N.",
        "output_format": "One line: digit_sum reversed_number (space-separated).",
        "constraints": "0 <= N <= 1e18",
        "examples": [
            {
                "input": "1234",
                "output": "10 4321",
                "explanation": "1+2+3+4=10; reverse is 4321.",
            },
            {
                "input": "100",
                "output": "1 1",
                "explanation": "Digit sum 1; reverse of 001 as integer is 1.",
            },
        ],
        "explanation": (
            "Repeatedly take N % 10 to accumulate digit sum and build the reverse, "
            "then divide N by 10 until zero. Handle N=0 as a special case."
        ),
        "expected_time_complexity": "O(log N)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(_PY_STUB, _CPP_STUB, _JAVA_STUB),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "n = int(sys.stdin.read().strip())\n"
                    "orig = n\n"
                    "s = 0\n"
                    "rev = 0\n"
                    "if n == 0:\n"
                    "    print(0, 0)\n"
                    "else:\n"
                    "    while n:\n"
                    "        d = n % 10\n"
                    "        s += d\n"
                    "        rev = rev * 10 + d\n"
                    "        n //= 10\n"
                    "    print(s, rev)\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("1234", "10 4321", category="normal", order_index=0),
            _tc("100", "1 1", category="boundary", order_index=1),
            _tc("0", "0 0", category="minimum", order_index=2),
            _tc("5", "5 5", category="single", order_index=3),
            _tc("999", "27 999", category="duplicates", is_hidden=True, order_index=4),
            _tc("1000000000000000000", "1 1", category="maximum", is_hidden=True, order_index=5),
            _tc("9876543210", "45 123456789", category="normal", is_hidden=True, order_index=6),
            _tc("10", "1 1", category="boundary", is_hidden=True, order_index=7),
        ],
    },
    # 14 — Vowels and consonants
    {
        "title": "Essay Draft Vowel Count",
        "slug": "essay-draft-vowel-count",
        "difficulty": "easy",
        "topics": ["strings"],
        "patterns": ["classification", "frequency-count"],
        "problem_statement": (
            "An SOP draft is given as a single string of letters (mixed case allowed). "
            "Count vowels (a,e,i,o,u case-insensitive) and consonants (other letters). "
            "Ignore any non-letter characters if present; only letters contribute."
        ),
        "input_format": "A single line string S.",
        "output_format": "One line: vowels consonants (two integers).",
        "constraints": (
            "1 <= |S| <= 1e5\n"
            "S may contain letters, digits, and spaces."
        ),
        "examples": [
            {
                "input": "Campus Drive",
                "output": "4 7",
                "explanation": "Vowels: a,u,i,e (4); consonants: C,m,p,s,D,r,v (7); space ignored.",
            },
            {
                "input": "xyz",
                "output": "0 3",
                "explanation": "No vowels.",
            },
        ],
        "explanation": (
            "Scan each character; if alphabetic, classify as vowel or consonant using "
            "a lowercase check against aeiou."
        ),
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(_PY_STUB, _CPP_STUB, _JAVA_STUB),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "s = sys.stdin.read()\n"
                    "if s.endswith('\\n'):\n"
                    "    s = s[:-1]\n"
                    "vow = cons = 0\n"
                    "for ch in s:\n"
                    "    if ch.isalpha():\n"
                    "        if ch.lower() in 'aeiou':\n"
                    "            vow += 1\n"
                    "        else:\n"
                    "            cons += 1\n"
                    "print(vow, cons)\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("Campus Drive", "4 7", category="normal", order_index=0),
            _tc("xyz", "0 3", category="boundary", order_index=1),
            _tc("a", "1 0", category="single", order_index=2),
            _tc("AEIOU", "5 0", category="minimum", order_index=3),
            _tc("bcdfg", "0 5", category="normal", is_hidden=True, order_index=4),
            _tc("Hello World 123", "3 7", category="adversarial", is_hidden=True, order_index=5),
            _tc("rhythm", "0 6", category="boundary", is_hidden=True, order_index=6),
            _tc("Placement", "3 6", category="normal", is_hidden=True, order_index=7),
        ],
    },
    # 15 — Rotate array left by k
    {
        "title": "Lab Shift Left Rotate",
        "slug": "lab-shift-left-rotate",
        "difficulty": "easy",
        "topics": ["arrays"],
        "patterns": ["rotation"],
        "problem_statement": (
            "Machine IDs in a lab queue are stored as an array of n integers. "
            "Rotate the array left by k positions (each left rotate moves the first "
            "element to the end). Print the array after rotation. k may be larger than n; "
            "use k modulo n."
        ),
        "input_format": (
            "First line: integers n k\n"
            "Second line: n space-separated integers"
        ),
        "output_format": "One line: n integers after left rotation by k.",
        "constraints": (
            "1 <= n <= 1e5\n"
            "0 <= k <= 1e9\n"
            "-1e9 <= a[i] <= 1e9"
        ),
        "examples": [
            {
                "input": "5 2\n1 2 3 4 5",
                "output": "3 4 5 1 2",
                "explanation": "Left by 2: 1,2 move to the end.",
            },
            {
                "input": "4 0\n7 8 9 10",
                "output": "7 8 9 10",
                "explanation": "k=0 means no change.",
            },
        ],
        "explanation": (
            "Let r = k % n. The result is a[r:] + a[:r]. Handle r=0 carefully."
        ),
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(n)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(_PY_STUB, _CPP_STUB, _JAVA_STUB),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "data = list(map(int, sys.stdin.read().split()))\n"
                    "n, k = data[0], data[1]\n"
                    "a = data[2:2+n]\n"
                    "r = k % n\n"
                    "b = a[r:] + a[:r]\n"
                    "print(' '.join(map(str, b)))\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("5 2\n1 2 3 4 5", "3 4 5 1 2", category="normal", order_index=0),
            _tc("4 0\n7 8 9 10", "7 8 9 10", category="boundary", order_index=1),
            _tc("1 5\n9", "9", category="single", order_index=2),
            _tc("3 3\n1 2 3", "1 2 3", category="minimum", order_index=3),
            _tc("6 7\n1 2 3 4 5 6", "2 3 4 5 6 1", category="normal", is_hidden=True, order_index=4),
            _tc("4 100\n-1 -2 -3 -4", "-1 -2 -3 -4", category="negative", is_hidden=True, order_index=5),
            _tc("5 1\n5 4 3 2 1", "4 3 2 1 5", category="normal", is_hidden=True, order_index=6),
            _tc("2 1\n10 20", "20 10", category="maximum", is_hidden=True, order_index=7),
        ],
    },
    # 16 — Second largest
    {
        "title": "Runner Up Placement Score",
        "slug": "runner-up-placement-score",
        "difficulty": "easy",
        "topics": ["arrays"],
        "patterns": ["linear-scan", "second-largest"],
        "problem_statement": (
            "n students have distinct? Not necessarily — scores may repeat. "
            "Find the second largest distinct score in the array. "
            "It is guaranteed that at least two distinct values exist."
        ),
        "input_format": (
            "First line: integer n\n"
            "Second line: n space-separated integers"
        ),
        "output_format": "One line: the second largest distinct value.",
        "constraints": (
            "2 <= n <= 1e5\n"
            "-1e9 <= a[i] <= 1e9\n"
            "At least two distinct values are present."
        ),
        "examples": [
            {
                "input": "5\n2 5 3 5 4",
                "output": "4",
                "explanation": "Distinct sorted descending: 5,4,3,2 → second is 4.",
            },
            {
                "input": "3\n10 10 9",
                "output": "9",
                "explanation": "Largest distinct 10, second 9.",
            },
        ],
        "explanation": (
            "Track largest and second-largest distinct while scanning, or use a set "
            "and pick the second max."
        ),
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(_PY_STUB, _CPP_STUB, _JAVA_STUB),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "data = list(map(int, sys.stdin.read().split()))\n"
                    "n = data[0]\n"
                    "a = data[1:1+n]\n"
                    "first = second = None\n"
                    "for x in a:\n"
                    "    if first is None or x > first:\n"
                    "        second = first\n"
                    "        first = x\n"
                    "    elif x != first and (second is None or x > second):\n"
                    "        second = x\n"
                    "print(second)\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("5\n2 5 3 5 4", "4", category="normal", order_index=0),
            _tc("3\n10 10 9", "9", category="duplicates", order_index=1),
            _tc("2\n1 2", "1", category="minimum", order_index=2),
            _tc("4\n-1 -5 -3 -2", "-2", category="negative", is_hidden=True, order_index=3),
            _tc("5\n7 7 7 7 6", "6", category="boundary", order_index=4),
            _tc("6\n100 50 100 50 99 1", "99", category="normal", is_hidden=True, order_index=5),
            _tc("4\n0 -1 0 -2", "-1", category="boundary", is_hidden=True, order_index=6),
            _tc("5\n9 8 7 6 5", "8", category="maximum", is_hidden=True, order_index=7),
        ],
    },
    # 17 — Prime check
    {
        "title": "Prime Badge Number Test",
        "slug": "prime-badge-number-test",
        "difficulty": "easy",
        "topics": ["math"],
        "patterns": ["primality"],
        "problem_statement": (
            "A workshop stamps each attendee with an integer badge number N. "
            "Determine whether N is a prime number (greater than 1 with no positive "
            "divisors other than 1 and itself)."
        ),
        "input_format": "A single integer N.",
        "output_format": 'Print "YES" if N is prime, otherwise "NO".',
        "constraints": "1 <= N <= 1e12",
        "examples": [
            {
                "input": "17",
                "output": "YES",
                "explanation": "17 has no divisors other than 1 and 17.",
            },
            {
                "input": "1",
                "output": "NO",
                "explanation": "1 is not prime.",
            },
        ],
        "explanation": (
            "Handle N < 2 as non-prime. Check divisibility up to sqrt(N); skip even "
            "checks after testing 2 for speed on large N."
        ),
        "expected_time_complexity": "O(sqrt(N))",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(_PY_STUB, _CPP_STUB, _JAVA_STUB),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "import math\n"
                    "n = int(sys.stdin.read().strip())\n"
                    "def is_prime(x):\n"
                    "    if x < 2: return False\n"
                    "    if x % 2 == 0: return x == 2\n"
                    "    r = int(math.isqrt(x))\n"
                    "    for i in range(3, r + 1, 2):\n"
                    "        if x % i == 0: return False\n"
                    "    return True\n"
                    "print('YES' if is_prime(n) else 'NO')\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("17", "YES", category="normal", order_index=0),
            _tc("1", "NO", category="minimum", order_index=1),
            _tc("2", "YES", category="boundary", order_index=2),
            _tc("4", "NO", category="normal", order_index=3),
            _tc("97", "YES", category="normal", is_hidden=True, order_index=4),
            _tc("1000000007", "YES", category="maximum", is_hidden=True, order_index=5),
            _tc("9", "NO", category="single", is_hidden=True, order_index=6),
            _tc("1", "NO", category="boundary", is_hidden=True, order_index=7),
            _tc("49", "NO", category="adversarial", is_hidden=True, order_index=8),
        ],
    },
    # 18 — GCD of array
    {
        "title": "Batch Size Common Measure",
        "slug": "batch-size-common-measure",
        "difficulty": "easy",
        "topics": ["math", "arrays"],
        "patterns": ["gcd", "euclidean"],
        "problem_statement": (
            "Training batch sizes are given as n positive integers. Find the greatest "
            "common divisor (GCD / HCF) of all numbers in the list."
        ),
        "input_format": (
            "First line: integer n\n"
            "Second line: n space-separated positive integers"
        ),
        "output_format": "One line: the GCD of all elements.",
        "constraints": (
            "1 <= n <= 1e5\n"
            "1 <= a[i] <= 1e9"
        ),
        "examples": [
            {
                "input": "4\n12 18 24 30",
                "output": "6",
                "explanation": "GCD of all four is 6.",
            },
            {
                "input": "2\n7 9",
                "output": "1",
                "explanation": "Coprime pair.",
            },
        ],
        "explanation": (
            "Fold Euclidean GCD across the array: g = a[0]; for each next x, g = gcd(g, x)."
        ),
        "expected_time_complexity": "O(n log A)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(_PY_STUB, _CPP_STUB, _JAVA_STUB),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "import math\n"
                    "data = list(map(int, sys.stdin.read().split()))\n"
                    "n = data[0]\n"
                    "a = data[1:1+n]\n"
                    "g = a[0]\n"
                    "for x in a[1:]:\n"
                    "    g = math.gcd(g, x)\n"
                    "print(g)\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("4\n12 18 24 30", "6", category="normal", order_index=0),
            _tc("2\n7 9", "1", category="normal", order_index=1),
            _tc("1\n42", "42", category="single", order_index=2),
            _tc("3\n8 8 8", "8", category="duplicates", order_index=3),
            _tc("5\n10 15 20 25 35", "5", category="normal", is_hidden=True, order_index=4),
            _tc("2\n1000000000 500000000", "500000000", category="maximum", is_hidden=True, order_index=5),
            _tc("3\n9 27 81", "9", category="boundary", is_hidden=True, order_index=6),
            _tc("4\n3 5 7 11", "1", category="minimum", is_hidden=True, order_index=7),
        ],
    },
    # 19 — Count target occurrences
    {
        "title": "Attendance Mark Frequency",
        "slug": "attendance-mark-frequency",
        "difficulty": "easy",
        "topics": ["arrays"],
        "patterns": ["linear-scan", "counting"],
        "problem_statement": (
            "Daily attendance codes are stored as n integers. Given a target code T, "
            "count how many times T appears in the array."
        ),
        "input_format": (
            "First line: integer n\n"
            "Second line: n space-separated integers\n"
            "Third line: integer T"
        ),
        "output_format": "One line: the count of T.",
        "constraints": (
            "1 <= n <= 1e5\n"
            "-1e9 <= a[i], T <= 1e9"
        ),
        "examples": [
            {
                "input": "6\n1 2 1 3 1 4\n1",
                "output": "3",
                "explanation": "1 appears three times.",
            },
            {
                "input": "3\n5 5 5\n7",
                "output": "0",
                "explanation": "Target absent.",
            },
        ],
        "explanation": "Single linear scan incrementing a counter when a[i] equals T.",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(_PY_STUB, _CPP_STUB, _JAVA_STUB),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "data = list(map(int, sys.stdin.read().split()))\n"
                    "n = data[0]\n"
                    "a = data[1:1+n]\n"
                    "T = data[1+n]\n"
                    "print(sum(1 for x in a if x == T))\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("6\n1 2 1 3 1 4\n1", "3", category="normal", order_index=0),
            _tc("3\n5 5 5\n7", "0", category="boundary", order_index=1),
            _tc("1\n9\n9", "1", category="single", order_index=2),
            _tc("4\n2 2 2 2\n2", "4", category="duplicates", order_index=3),
            _tc("5\n-1 0 -1 0 -1\n-1", "3", category="negative", is_hidden=True, order_index=4),
            _tc("5\n1 2 3 4 5\n3", "1", category="minimum", is_hidden=True, order_index=5),
            _tc("7\n0 0 0 0 0 0 1\n0", "6", category="maximum", is_hidden=True, order_index=6),
            _tc("4\n8 1 8 8\n8", "3", category="normal", is_hidden=True, order_index=7),
        ],
    },
    # 20 — Run-length compress
    {
        "title": "Sensor Run Length Encode",
        "slug": "sensor-run-length-encode",
        "difficulty": "easy",
        "topics": ["strings"],
        "patterns": ["run-length-encoding", "compression"],
        "problem_statement": (
            "A hallway sensor emits a string of lowercase letters where consecutive equal "
            "characters form runs (e.g. aabbbc). Compress it to character + count for each "
            "run: aabbbc → a2b3c1. Always print the count even when it is 1."
        ),
        "input_format": "A single line: lowercase string S (non-empty).",
        "output_format": "One line: the compressed string.",
        "constraints": (
            "1 <= |S| <= 1e5\n"
            "S contains only lowercase English letters."
        ),
        "examples": [
            {
                "input": "aabbbc",
                "output": "a2b3c1",
                "explanation": "Two a's, three b's, one c.",
            },
            {
                "input": "xyz",
                "output": "x1y1z1",
                "explanation": "All runs length 1.",
            },
        ],
        "explanation": (
            "Walk the string counting consecutive equal characters; append char and "
            "count when the run ends."
        ),
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(n)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(_PY_STUB, _CPP_STUB, _JAVA_STUB),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "s = sys.stdin.read().strip()\n"
                    "parts = []\n"
                    "i = 0\n"
                    "n = len(s)\n"
                    "while i < n:\n"
                    "    j = i\n"
                    "    while j < n and s[j] == s[i]:\n"
                    "        j += 1\n"
                    "    parts.append(s[i] + str(j - i))\n"
                    "    i = j\n"
                    "print(''.join(parts))\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("aabbbc", "a2b3c1", category="normal", order_index=0),
            _tc("xyz", "x1y1z1", category="normal", order_index=1),
            _tc("a", "a1", category="single", order_index=2),
            _tc("aaaa", "a4", category="duplicates", order_index=3),
            _tc("abba", "a1b2a1", category="boundary", is_hidden=True, order_index=4),
            _tc("wwxxxyyz", "w2x3y2z1", category="normal", is_hidden=True, order_index=5),
            _tc("zzzzzzzzzz", "z10", category="maximum", is_hidden=True, order_index=6),
            _tc("aabb", "a2b2", category="minimum", is_hidden=True, order_index=7),
        ],
    },
    # 21 — Valid parentheses
    {
        "title": "Bracket Balance Lab Script",
        "slug": "bracket-balance-lab-script",
        "difficulty": "medium",
        "topics": ["strings"],
        "patterns": ["stack", "parentheses"],
        "problem_statement": (
            "A lab automation script uses only the characters '(', ')', '{', '}', '[' and ']'. "
            "Decide whether the bracket sequence is valid: every opening bracket must be "
            "closed by the same type in the correct order, and every close must match."
        ),
        "input_format": "A single line string S consisting only of brackets (may be empty).",
        "output_format": 'Print "YES" if valid, otherwise "NO".',
        "constraints": (
            "0 <= |S| <= 1e5\n"
            "S contains only (){}[]"
        ),
        "examples": [
            {
                "input": "()[]{}",
                "output": "YES",
                "explanation": "Each pair closes correctly.",
            },
            {
                "input": "(]",
                "output": "NO",
                "explanation": "Mismatched types.",
            },
        ],
        "explanation": (
            "Use a stack: push opens; on close, pop and verify matching type. "
            "Valid iff stack empty at end and never mismatched."
        ),
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(n)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(_PY_STUB, _CPP_STUB, _JAVA_STUB),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "s = sys.stdin.read().strip()\n"
                    "mp = {')': '(', '}': '{', ']': '['}\n"
                    "st = []\n"
                    "ok = True\n"
                    "for ch in s:\n"
                    "    if ch in '({[':\n"
                    "        st.append(ch)\n"
                    "    else:\n"
                    "        if not st or st[-1] != mp[ch]:\n"
                    "            ok = False\n"
                    "            break\n"
                    "        st.pop()\n"
                    "print('YES' if ok and not st else 'NO')\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("()[]{}", "YES", category="normal", order_index=0),
            _tc("(]", "NO", category="normal", order_index=1),
            _tc("", "YES", category="empty", order_index=2),
            _tc("(", "NO", category="single", order_index=3),
            _tc("{[]}", "YES", category="boundary", is_hidden=True, order_index=4),
            _tc("([)]", "NO", category="adversarial", is_hidden=True, order_index=5),
            _tc("(((())))", "YES", category="maximum", is_hidden=True, order_index=6),
            _tc("]]", "NO", category="minimum", is_hidden=True, order_index=7),
            _tc("{[()()]}", "YES", category="normal", is_hidden=True, order_index=8),
        ],
    },
    # 22 — Merge two sorted arrays
    {
        "title": "Merged Merit Lists Easy",
        "slug": "merged-merit-lists-easy",
        "difficulty": "medium",
        "topics": ["arrays"],
        "patterns": ["two-pointers", "merge"],
        "problem_statement": (
            "Two departments produced already-sorted ascending merit lists A (n scores) "
            "and B (m scores). Merge them into one sorted ascending list and print it."
        ),
        "input_format": (
            "First line: integers n m\n"
            "Second line: n space-separated integers (sorted ascending; n may be 0 → empty line ok as no numbers)\n"
            "Third line: m space-separated integers (sorted ascending; m may be 0)"
        ),
        "output_format": (
            "One line: n+m integers sorted ascending, space-separated. "
            "If n+m=0, print an empty line."
        ),
        "constraints": (
            "0 <= n, m <= 1e5\n"
            "n + m >= 1 for non-empty output cases in tests; 0+0 allowed\n"
            "-1e9 <= values <= 1e9\n"
            "Each input list is sorted non-decreasing."
        ),
        "examples": [
            {
                "input": "3 3\n1 3 5\n2 4 6",
                "output": "1 2 3 4 5 6",
                "explanation": "Classic two-pointer merge.",
            },
            {
                "input": "2 3\n1 1\n1 2 3",
                "output": "1 1 1 2 3",
                "explanation": "Duplicates preserved.",
            },
        ],
        "explanation": (
            "Two pointers from the starts of A and B; always take the smaller head. "
            "Append remaining tail when one list is exhausted."
        ),
        "expected_time_complexity": "O(n+m)",
        "expected_space_complexity": "O(n+m)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(_PY_STUB, _CPP_STUB, _JAVA_STUB),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "data = list(map(int, sys.stdin.read().split()))\n"
                    "n, m = data[0], data[1]\n"
                    "a = data[2:2+n]\n"
                    "b = data[2+n:2+n+m]\n"
                    "i = j = 0\n"
                    "out = []\n"
                    "while i < n and j < m:\n"
                    "    if a[i] <= b[j]:\n"
                    "        out.append(a[i]); i += 1\n"
                    "    else:\n"
                    "        out.append(b[j]); j += 1\n"
                    "out.extend(a[i:])\n"
                    "out.extend(b[j:])\n"
                    "print(' '.join(map(str, out)))\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("3 3\n1 3 5\n2 4 6", "1 2 3 4 5 6", category="normal", order_index=0),
            _tc("2 3\n1 1\n1 2 3", "1 1 1 2 3", category="duplicates", order_index=1),
            _tc("1 0\n5\n", "5", category="boundary", order_index=2),
            _tc("0 1\n\n7", "7", category="minimum", order_index=3),
            _tc("3 2\n-5 -1 0\n-3 2", "-5 -3 -1 0 2", category="negative", is_hidden=True, order_index=4),
            _tc("4 4\n1 2 3 4\n5 6 7 8", "1 2 3 4 5 6 7 8", category="normal", is_hidden=True, order_index=5),
            _tc("2 2\n10 20\n10 20", "10 10 20 20", category="boundary", is_hidden=True, order_index=6),
            _tc("5 1\n1 2 3 4 5\n3", "1 2 3 3 4 5", category="maximum", is_hidden=True, order_index=7),
        ],
    },
]


def catalog_as_contracts():
    from app.coding_bank.schemas import GeneratedProblemContract

    return [GeneratedProblemContract.model_validate(x) for x in SERVICE_BANK_V1]
