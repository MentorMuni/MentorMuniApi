"""Curated campus-placement coding bank (v1).

Original placement-oriented problems (not LeetCode titles/wording).
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


# ---------------------------------------------------------------------------
# Problem definitions
# ---------------------------------------------------------------------------

PLACEMENT_BANK_V1: list[dict] = [
    # 1 — Arrays / Hashing
    {
        "title": "Campus Pair Balance",
        "slug": "campus-pair-balance",
        "difficulty": "easy",
        "topics": ["arrays", "hashing"],
        "patterns": ["hashmap complement"],
        "problem_statement": (
            "During the placement coordination meet, each student has a skill score. "
            "Given n distinct skill scores and a target balance T, find two students "
            "whose scores add exactly to T. Return their 1-based positions in ascending order. "
            "Exactly one valid pair is guaranteed."
        ),
        "input_format": (
            "First line: integer n\n"
            "Second line: n space-separated integers (skill scores)\n"
            "Third line: integer T"
        ),
        "output_format": "Two 1-based indices i j (i < j) separated by a space.",
        "constraints": "2 <= n <= 1e5\n-1e9 <= scores[i], T <= 1e9\nAll scores are distinct.",
        "examples": [
            {
                "input": "4\n2 7 11 15\n9",
                "output": "1 2",
                "explanation": "2 + 7 = 9 at positions 1 and 2.",
            },
            {
                "input": "3\n3 2 4\n6",
                "output": "2 3",
                "explanation": "2 + 4 = 6.",
            },
        ],
        "explanation": (
            "Scan left to right while storing each value's index in a hash map. "
            "For value x, look up T - x; if present, emit the stored index and current index."
        ),
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(n)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(
            '''
import sys

def solve():
    data = list(map(int, sys.stdin.read().split()))
    # Find 1-based indices of two scores that sum to T
    pass

if __name__ == "__main__":
    solve()
''',
            '''
#include <bits/stdc++.h>
using namespace std;
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    // Read n, scores, T; print 1-based indices
    return 0;
}
''',
            '''
import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        // Read n, scores, T; print 1-based indices
    }
}
''',
        ),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "data = list(map(int, sys.stdin.read().split()))\n"
                    "n = data[0]\n"
                    "nums = data[1:1+n]\n"
                    "T = data[1+n]\n"
                    "seen = {}\n"
                    "for i, x in enumerate(nums):\n"
                    "    need = T - x\n"
                    "    if need in seen:\n"
                    "        print(seen[need] + 1, i + 1)\n"
                    "        raise SystemExit\n"
                    "    seen[x] = i\n"
                ),
                "notes": "Hash complement lookup.",
            }
        ],
        "candidate_test_cases": [
            _tc("4\n2 7 11 15\n9", "1 2", category="normal", order_index=0),
            _tc("3\n3 2 4\n6", "2 3", category="normal", is_hidden=True, order_index=1),
            _tc("2\n1 2\n3", "1 2", category="minimum", order_index=2),
            _tc("5\n0 -1 2 -3 5\n-4", "2 4", category="negative", is_hidden=True, order_index=3),
            _tc("4\n10 20 35 40\n50", "1 4", category="boundary", order_index=4),
            _tc("6\n5 1 9 3 8 2\n13", "1 5", category="normal", is_hidden=True, order_index=5),
            _tc("3\n1000000000 -1000000000 0\n0", "1 2", category="boundary", is_hidden=True, order_index=6),
            _tc("5\n8 1 4 6 3\n7", "2 4", category="normal", order_index=7),
        ],
    },
    # 2 — Arrays
    {
        "title": "Hostel Attendance Streak",
        "slug": "hostel-attendance-streak",
        "difficulty": "easy",
        "topics": ["arrays"],
        "patterns": ["linear scan"],
        "problem_statement": (
            "The hostel warden records daily attendance as 1 (present) or 0 (absent). "
            "Find the longest consecutive streak of present days in the record."
        ),
        "input_format": "First line: n\nSecond line: n integers each 0 or 1",
        "output_format": "A single integer — the maximum consecutive 1s.",
        "constraints": "1 <= n <= 1e5\nEach a[i] is 0 or 1.",
        "examples": [
            {
                "input": "6\n1 1 0 1 1 1",
                "output": "3",
                "explanation": "The last three days form the longest streak.",
            },
            {
                "input": "4\n0 0 0 0",
                "output": "0",
                "explanation": "No present day.",
            },
        ],
        "explanation": (
            "Walk the array once, incrementing a counter on 1 and resetting on 0, "
            "tracking the maximum counter value."
        ),
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(
            '''
import sys
def solve():
    data = list(map(int, sys.stdin.read().split()))
    # Return longest consecutive 1s
    pass
if __name__ == "__main__":
    solve()
''',
            '''
#include <bits/stdc++.h>
using namespace std;
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    // Longest consecutive 1s
    return 0;
}
''',
            '''
import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        // Longest consecutive 1s
    }
}
''',
        ),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "data = list(map(int, sys.stdin.read().split()))\n"
                    "n, a = data[0], data[1:]\n"
                    "best = cur = 0\n"
                    "for x in a:\n"
                    "    if x == 1:\n"
                    "        cur += 1\n"
                    "        best = max(best, cur)\n"
                    "    else:\n"
                    "        cur = 0\n"
                    "print(best)\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("6\n1 1 0 1 1 1", "3", category="normal"),
            _tc("4\n0 0 0 0", "0", category="empty"),
            _tc("1\n1", "1", category="single"),
            _tc("1\n0", "0", category="single", is_hidden=True),
            _tc("8\n1 1 1 1 0 1 1 0", "4", category="boundary", is_hidden=True),
            _tc("5\n1 0 1 0 1", "1", category="normal"),
            _tc("7\n0 1 1 1 1 1 0", "5", category="boundary", is_hidden=True),
            _tc("3\n1 1 1", "3", category="maximum", is_hidden=True),
        ],
    },
    # 3 — Strings / Hashing
    {
        "title": "Offer Letter Anagram Check",
        "slug": "offer-letter-anagram-check",
        "difficulty": "easy",
        "topics": ["strings", "hashing"],
        "patterns": ["frequency count"],
        "problem_statement": (
            "Two draft offer-letter templates are anagrams if they use the same letters "
            "with the same frequencies (case-sensitive, spaces matter). "
            "Given two strings S and T on separate lines, print YES if they are anagrams, else NO."
        ),
        "input_format": "Line 1: string S\nLine 2: string T",
        "output_format": "YES or NO",
        "constraints": "1 <= |S|, |T| <= 1e5\nStrings contain printable ASCII without newlines.",
        "examples": [
            {
                "input": "listen\nsilent",
                "output": "YES",
                "explanation": "Same letter multiset.",
            },
            {
                "input": "campus\nplace",
                "output": "NO",
                "explanation": "Different lengths and letters.",
            },
        ],
        "explanation": "Compare character frequency maps (or sorted strings) of S and T.",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(
            '''
import sys
def solve():
    lines = sys.stdin.read().splitlines()
    # Print YES if anagrams else NO
    pass
if __name__ == "__main__":
    solve()
''',
            '''
#include <bits/stdc++.h>
using namespace std;
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    // Anagram check YES/NO
    return 0;
}
''',
            '''
import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        // Anagram check YES/NO
    }
}
''',
        ),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "from collections import Counter\n"
                    "lines = sys.stdin.read().splitlines()\n"
                    "s, t = lines[0], lines[1]\n"
                    "print('YES' if Counter(s) == Counter(t) else 'NO')\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("listen\nsilent", "YES", category="normal"),
            _tc("campus\nplace", "NO", category="normal"),
            _tc("a\na", "YES", category="single"),
            _tc("a\nb", "NO", category="single", is_hidden=True),
            _tc("Aa\naA", "YES", category="boundary"),
            _tc("ab c\nc ba", "YES", category="duplicates", is_hidden=True),
            _tc("aaa\naaa", "YES", category="duplicates"),
            _tc("hello\nworld", "NO", category="adversarial", is_hidden=True),
        ],
    },
    # 4 — Strings
    {
        "title": "Badge Code Palindrome",
        "slug": "badge-code-palindrome",
        "difficulty": "easy",
        "topics": ["strings", "two pointers"],
        "patterns": ["two pointers"],
        "problem_statement": (
            "Student badge codes must read the same forwards and backwards after "
            "removing all non-alphanumeric characters and ignoring case. "
            "Given one line S, print YES if it is a valid badge palindrome, else NO."
        ),
        "input_format": "A single line string S (may contain spaces and punctuation).",
        "output_format": "YES or NO",
        "constraints": "1 <= |S| <= 1e5",
        "examples": [
            {
                "input": "A man, a plan, a canal: Panama",
                "output": "YES",
                "explanation": "Alphanumeric form is amanaplanacanalpanama.",
            },
            {
                "input": "race a car",
                "output": "NO",
                "explanation": "raceacar is not a palindrome.",
            },
        ],
        "explanation": "Filter to alphanumerics, lowercase, then compare with two pointers.",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(n)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(
            '''
import sys
def solve():
    s = sys.stdin.read()
    # Badge palindrome YES/NO
    pass
if __name__ == "__main__":
    solve()
''',
            '''
#include <bits/stdc++.h>
using namespace std;
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    // Badge palindrome
    return 0;
}
''',
            '''
import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        // Badge palindrome
    }
}
''',
        ),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "s = sys.stdin.read()\n"
                    "t = ''.join(c.lower() for c in s if c.isalnum())\n"
                    "print('YES' if t == t[::-1] else 'NO')\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("A man, a plan, a canal: Panama", "YES", category="normal"),
            _tc("race a car", "NO", category="normal"),
            _tc("a", "YES", category="single"),
            _tc("ab", "NO", category="minimum", is_hidden=True),
            _tc("No lemon, no melon", "YES", category="boundary"),
            _tc("12321", "YES", category="normal", is_hidden=True),
            _tc("12331", "NO", category="adversarial", is_hidden=True),
            _tc("!!!", "YES", category="empty", is_hidden=True),
        ],
    },
    # 5 — Two Pointers
    {
        "title": "Seminar Seat Distance",
        "slug": "seminar-seat-distance",
        "difficulty": "medium",
        "topics": ["arrays", "two pointers"],
        "patterns": ["two pointers on sorted array"],
        "problem_statement": (
            "Seminar seats are at strictly increasing positions along a hallway. "
            "Given positions and a required social distance D, determine whether "
            "any two seats are exactly D units apart. Print YES or NO."
        ),
        "input_format": (
            "First line: n D\n"
            "Second line: n strictly increasing integers (seat positions)"
        ),
        "output_format": "YES or NO",
        "constraints": "2 <= n <= 1e5\n1 <= D <= 1e9\nPositions are strictly increasing in [1, 1e9].",
        "examples": [
            {
                "input": "5 3\n1 2 4 7 11",
                "output": "YES",
                "explanation": "4 and 7 differ by 3.",
            },
            {
                "input": "4 5\n1 2 3 4",
                "output": "NO",
                "explanation": "No pair differs by 5.",
            },
        ],
        "explanation": (
            "Use two pointers on the sorted positions: advance the right pointer when "
            "difference is too small, left when too large, succeed on exact D."
        ),
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(
            '''
import sys
def solve():
    data = list(map(int, sys.stdin.read().split()))
    # YES if any pair distance equals D
    pass
if __name__ == "__main__":
    solve()
''',
            '''
#include <bits/stdc++.h>
using namespace std;
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    return 0;
}
''',
            '''
import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
    }
}
''',
        ),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "data = list(map(int, sys.stdin.read().split()))\n"
                    "n, D = data[0], data[1]\n"
                    "a = data[2:]\n"
                    "i = j = 0\n"
                    "ok = False\n"
                    "while j < n:\n"
                    "    if i == j:\n"
                    "        j += 1\n"
                    "        continue\n"
                    "    diff = a[j] - a[i]\n"
                    "    if diff == D:\n"
                    "        ok = True\n"
                    "        break\n"
                    "    elif diff < D:\n"
                    "        j += 1\n"
                    "    else:\n"
                    "        i += 1\n"
                    "print('YES' if ok else 'NO')\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("5 3\n1 2 4 7 11", "YES", category="normal"),
            _tc("4 5\n1 2 3 4", "NO", category="normal"),
            _tc("2 1\n1 2", "YES", category="minimum"),
            _tc("2 3\n1 2", "NO", category="minimum", is_hidden=True),
            _tc("6 10\n1 5 11 20 21 31", "YES", category="boundary", is_hidden=True),
            _tc("5 1\n1 3 5 7 9", "NO", category="adversarial"),
            _tc("7 4\n2 4 6 8 10 12 16", "YES", category="duplicates", is_hidden=True),
            _tc("3 100\n1 50 101", "YES", category="boundary", is_hidden=True),
        ],
    },
    # 6 — Sliding Window
    {
        "title": "Placement Drive Window",
        "slug": "placement-drive-window",
        "difficulty": "medium",
        "topics": ["arrays", "sliding window"],
        "patterns": ["fixed window sum"],
        "problem_statement": (
            "A company schedules interviews over n consecutive slots with scores. "
            "Find the maximum total score achievable in any contiguous block of exactly k slots."
        ),
        "input_format": "First line: n k\nSecond line: n integers (slot scores)",
        "output_format": "A single integer — the maximum window sum of length k.",
        "constraints": "1 <= k <= n <= 1e5\n-1e4 <= score[i] <= 1e4",
        "examples": [
            {
                "input": "5 3\n2 1 5 1 3",
                "output": "9",
                "explanation": "Window [5,1,3] sums to 9.",
            },
            {
                "input": "4 2\n-1 -2 -3 -4",
                "output": "-3",
                "explanation": "Best window is [-1,-2].",
            },
        ],
        "explanation": "Compute the first window sum, then slide by subtracting the leaving element and adding the entering one.",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(
            '''
import sys
def solve():
    data = list(map(int, sys.stdin.read().split()))
    # Max sum of contiguous k elements
    pass
if __name__ == "__main__":
    solve()
''',
            '''
#include <bits/stdc++.h>
using namespace std;
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    return 0;
}
''',
            '''
import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
    }
}
''',
        ),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "data = list(map(int, sys.stdin.read().split()))\n"
                    "n, k = data[0], data[1]\n"
                    "a = data[2:]\n"
                    "s = sum(a[:k])\n"
                    "best = s\n"
                    "for i in range(k, n):\n"
                    "    s += a[i] - a[i-k]\n"
                    "    if s > best:\n"
                    "        best = s\n"
                    "print(best)\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("5 3\n2 1 5 1 3", "9", category="normal"),
            _tc("4 2\n-1 -2 -3 -4", "-3", category="negative"),
            _tc("1 1\n42", "42", category="single"),
            _tc("6 6\n1 2 3 4 5 6", "21", category="maximum", is_hidden=True),
            _tc("6 1\n3 -5 7 0 2 -1", "7", category="boundary"),
            _tc("5 4\n1 1 1 1 100", "103", category="boundary", is_hidden=True),
            _tc("7 3\n4 2 -1 9 0 3 1", "12", category="normal", is_hidden=True),
            _tc("3 2\n0 0 0", "0", category="empty", is_hidden=True),
        ],
    },
    # 7 — Sliding Window / Hashing
    {
        "title": "Mentor Office Hours Span",
        "slug": "mentor-office-hours-span",
        "difficulty": "medium",
        "topics": ["strings", "sliding window", "hashing"],
        "patterns": ["variable window unique"],
        "problem_statement": (
            "Each character in a string is a mentor visit type. Find the length of the "
            "longest contiguous segment in which every character appears at most once "
            "(no repeated visit type inside the window)."
        ),
        "input_format": "A single line string S of lowercase letters.",
        "output_format": "A single integer — longest substring without repeating characters.",
        "constraints": "1 <= |S| <= 1e5\nS contains only lowercase English letters.",
        "examples": [
            {
                "input": "abcabcbb",
                "output": "3",
                "explanation": "abc is the longest unique span.",
            },
            {
                "input": "bbbbb",
                "output": "1",
                "explanation": "Only single letters are unique.",
            },
        ],
        "explanation": "Maintain a sliding window with last-seen indices; shrink the left when a duplicate enters.",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(
            '''
import sys
def solve():
    s = sys.stdin.read().strip()
    # Longest substring without repeats
    pass
if __name__ == "__main__":
    solve()
''',
            '''
#include <bits/stdc++.h>
using namespace std;
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    return 0;
}
''',
            '''
import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
    }
}
''',
        ),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "s = sys.stdin.read().strip()\n"
                    "last = {}\n"
                    "left = 0\n"
                    "best = 0\n"
                    "for i, c in enumerate(s):\n"
                    "    if c in last and last[c] >= left:\n"
                    "        left = last[c] + 1\n"
                    "    last[c] = i\n"
                    "    best = max(best, i - left + 1)\n"
                    "print(best)\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("abcabcbb", "3", category="normal"),
            _tc("bbbbb", "1", category="duplicates"),
            _tc("a", "1", category="single"),
            _tc("abcdef", "6", category="maximum", is_hidden=True),
            _tc("pwwkew", "3", category="normal"),
            _tc("abba", "2", category="boundary", is_hidden=True),
            _tc("dvdf", "3", category="adversarial", is_hidden=True),
            _tc("tmmzuxt", "5", category="boundary", is_hidden=True),
        ],
    },
    # 8 — Binary Search
    {
        "title": "Cutoff Marks Ladder",
        "slug": "cutoff-marks-ladder",
        "difficulty": "easy",
        "topics": ["arrays", "binary search"],
        "patterns": ["lower bound"],
        "problem_statement": (
            "Sorted ascending cutoff marks from previous years are given. "
            "For a student score X, find the smallest cutoff that is strictly greater than X. "
            "If none exists, print -1."
        ),
        "input_format": (
            "First line: n X\n"
            "Second line: n strictly increasing integers"
        ),
        "output_format": "A single integer — next greater cutoff, or -1.",
        "constraints": "1 <= n <= 1e5\n-1e9 <= values, X <= 1e9",
        "examples": [
            {
                "input": "5 7\n1 3 5 8 10",
                "output": "8",
                "explanation": "8 is the least value > 7.",
            },
            {
                "input": "4 10\n1 2 3 10",
                "output": "-1",
                "explanation": "Nothing exceeds 10.",
            },
        ],
        "explanation": "Binary search for the first index with a[i] > X (upper bound).",
        "expected_time_complexity": "O(log n)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(
            '''
import sys
def solve():
    data = list(map(int, sys.stdin.read().split()))
    # Next strictly greater value or -1
    pass
if __name__ == "__main__":
    solve()
''',
            '''
#include <bits/stdc++.h>
using namespace std;
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    return 0;
}
''',
            '''
import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
    }
}
''',
        ),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "import bisect\n"
                    "data = list(map(int, sys.stdin.read().split()))\n"
                    "n, X = data[0], data[1]\n"
                    "a = data[2:]\n"
                    "i = bisect.bisect_right(a, X)\n"
                    "print(a[i] if i < n else -1)\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("5 7\n1 3 5 8 10", "8", category="normal"),
            _tc("4 10\n1 2 3 10", "-1", category="boundary"),
            _tc("1 5\n5", "-1", category="single"),
            _tc("1 4\n5", "5", category="single", is_hidden=True),
            _tc("6 0\n-5 -2 0 1 4 9", "1", category="negative"),
            _tc("5 1\n2 3 4 5 6", "2", category="boundary", is_hidden=True),
            _tc("5 100\n1 2 3 4 5", "-1", category="maximum", is_hidden=True),
            _tc("7 4\n1 2 3 4 5 6 7", "5", category="normal", is_hidden=True),
        ],
    },
    # 9 — Binary Search (answer space)
    {
        "title": "Lab Printer Capacity",
        "slug": "lab-printer-capacity",
        "difficulty": "medium",
        "topics": ["binary search", "greedy"],
        "patterns": ["binary search on answer"],
        "problem_statement": (
            "There are m identical lab printers. Job i needs pages[i] pages and must run "
            "on a single printer without splitting. Printers run in parallel; each prints "
            "1 page per unit time. Find the minimum time T such that all jobs can be "
            "assigned without any printer exceeding T pages of work."
        ),
        "input_format": (
            "First line: n m\n"
            "Second line: n positive integers (pages per job)"
        ),
        "output_format": "A single integer — minimum completion time.",
        "constraints": "1 <= n <= 1e5\n1 <= m <= n\n1 <= pages[i] <= 1e9",
        "examples": [
            {
                "input": "4 2\n1 2 4 8",
                "output": "8",
                "explanation": "One printer takes 8; the other takes 1+2+4=7.",
            },
            {
                "input": "3 3\n5 5 5",
                "output": "5",
                "explanation": "Each printer takes one job.",
            },
        ],
        "explanation": (
            "Binary search T between max(pages) and sum(pages). For a mid value, "
            "greedily pack jobs left-to-right onto printers and check if m printers suffice."
        ),
        "expected_time_complexity": "O(n log S)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(
            '''
import sys
def solve():
    data = list(map(int, sys.stdin.read().split()))
    # Minimum time with m printers
    pass
if __name__ == "__main__":
    solve()
''',
            '''
#include <bits/stdc++.h>
using namespace std;
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    return 0;
}
''',
            '''
import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
    }
}
''',
        ),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "data = list(map(int, sys.stdin.read().split()))\n"
                    "n, m = data[0], data[1]\n"
                    "a = data[2:]\n"
                    "\n"
                    "def ok(T):\n"
                    "    used = 1\n"
                    "    cur = 0\n"
                    "    for x in a:\n"
                    "        if x > T:\n"
                    "            return False\n"
                    "        if cur + x <= T:\n"
                    "            cur += x\n"
                    "        else:\n"
                    "            used += 1\n"
                    "            cur = x\n"
                    "            if used > m:\n"
                    "                return False\n"
                    "    return True\n"
                    "\n"
                    "lo, hi = max(a), sum(a)\n"
                    "ans = hi\n"
                    "while lo <= hi:\n"
                    "    mid = (lo + hi) // 2\n"
                    "    if ok(mid):\n"
                    "        ans = mid\n"
                    "        hi = mid - 1\n"
                    "    else:\n"
                    "        lo = mid + 1\n"
                    "print(ans)\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("4 2\n1 2 4 8", "8", category="normal"),
            _tc("3 3\n5 5 5", "5", category="normal"),
            _tc("1 1\n10", "10", category="single"),
            _tc("5 1\n1 2 3 4 5", "15", category="maximum", is_hidden=True),
            _tc("5 5\n1 2 3 4 5", "5", category="boundary"),
            _tc("6 3\n7 2 5 10 8 3", "14", category="adversarial", is_hidden=True),
            _tc("4 3\n10 10 10 1", "11", category="boundary", is_hidden=True),
            _tc("2 2\n1000000000 1000000000", "1000000000", category="large", is_hidden=True),
        ],
    },
    # 10 — Stack
    {
        "title": "Lab Bracket Balance",
        "slug": "lab-bracket-balance",
        "difficulty": "easy",
        "topics": ["stack", "strings"],
        "patterns": ["stack matching"],
        "problem_statement": (
            "Expression snippets in the coding lab use (), [], and {}. "
            "A snippet is balanced if brackets nest and close correctly. "
            "Given a string S of only bracket characters, print YES if balanced, else NO."
        ),
        "input_format": "A single line string S consisting of ()[]{} only (possibly empty).",
        "output_format": "YES or NO",
        "constraints": "0 <= |S| <= 1e5",
        "examples": [
            {
                "input": "()[]{}",
                "output": "YES",
                "explanation": "Each pair closes immediately.",
            },
            {
                "input": "(]",
                "output": "NO",
                "explanation": "Mismatched types.",
            },
        ],
        "explanation": "Push opening brackets; on closing, pop and verify matching type. Stack must end empty.",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(n)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(
            '''
import sys
def solve():
    s = sys.stdin.read().strip()
    # Bracket balance YES/NO
    pass
if __name__ == "__main__":
    solve()
''',
            '''
#include <bits/stdc++.h>
using namespace std;
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    return 0;
}
''',
            '''
import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
    }
}
''',
        ),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "s = sys.stdin.read().strip()\n"
                    "pair = {')':'(', ']':'[', '}':'{'}\n"
                    "st = []\n"
                    "ok = True\n"
                    "for c in s:\n"
                    "    if c in '([{':\n"
                    "        st.append(c)\n"
                    "    else:\n"
                    "        if not st or st[-1] != pair[c]:\n"
                    "            ok = False\n"
                    "            break\n"
                    "        st.pop()\n"
                    "print('YES' if ok and not st else 'NO')\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("()[]{}", "YES", category="normal"),
            _tc("(]", "NO", category="adversarial"),
            _tc("", "YES", category="empty"),
            _tc("(", "NO", category="single", is_hidden=True),
            _tc("{[]}", "YES", category="normal"),
            _tc("([)]", "NO", category="adversarial", is_hidden=True),
            _tc("(((())))", "YES", category="boundary", is_hidden=True),
            _tc("((())", "NO", category="boundary", is_hidden=True),
        ],
    },
    # 11 — Queue
    {
        "title": "Canteen Token Queue",
        "slug": "canteen-token-queue",
        "difficulty": "easy",
        "topics": ["queue", "arrays"],
        "patterns": ["queue simulation"],
        "problem_statement": (
            "Students stand in a canteen queue with hunger values. Each minute the front "
            "student is served 1 unit. If still hungry, they go to the back of the queue; "
            "otherwise they leave. Given the initial queue and a target student's index "
            "(0-based), compute how many minutes until that student leaves fully served."
        ),
        "input_format": (
            "First line: n k\n"
            "Second line: n positive integers (hunger of students in order)"
        ),
        "output_format": "A single integer — minutes until student k finishes.",
        "constraints": "1 <= n <= 1000\n0 <= k < n\n1 <= hunger[i] <= 1000",
        "examples": [
            {
                "input": "4 2\n1 2 3 4",
                "output": "8",
                "explanation": "Student at index 2 finishes on the 8th minute under the rotate-to-back rule.",
            },
            {
                "input": "1 0\n5",
                "output": "5",
                "explanation": "Only one student; takes 5 minutes.",
            },
        ],
        "explanation": (
            "Simulate with a queue of (hunger, index). Each step decrement front; "
            "re-enqueue if remaining > 0. Stop when the dequeued student is k and remaining becomes 0."
        ),
        "expected_time_complexity": "O(n * max_hunger)",
        "expected_space_complexity": "O(n)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(
            '''
import sys
def solve():
    data = list(map(int, sys.stdin.read().split()))
    # Minutes until student k is done
    pass
if __name__ == "__main__":
    solve()
''',
            '''
#include <bits/stdc++.h>
using namespace std;
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    return 0;
}
''',
            '''
import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
    }
}
''',
        ),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "from collections import deque\n"
                    "data = list(map(int, sys.stdin.read().split()))\n"
                    "n, k = data[0], data[1]\n"
                    "a = data[2:]\n"
                    "q = deque((a[i], i) for i in range(n))\n"
                    "t = 0\n"
                    "while q:\n"
                    "    h, i = q.popleft()\n"
                    "    t += 1\n"
                    "    h -= 1\n"
                    "    if h > 0:\n"
                    "        q.append((h, i))\n"
                    "    elif i == k:\n"
                    "        break\n"
                    "print(t)\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("4 2\n1 2 3 4", "8", category="normal"),
            _tc("1 0\n5", "5", category="single"),
            _tc("3 0\n1 1 1", "1", category="minimum"),
            _tc("3 2\n1 1 1", "3", category="boundary", is_hidden=True),
            _tc("5 1\n2 2 2 2 2", "7", category="duplicates"),
            _tc("4 3\n4 3 2 1", "4", category="adversarial", is_hidden=True),
            _tc("2 0\n3 1", "4", category="normal", is_hidden=True),
            _tc("2 1\n3 1", "2", category="boundary", is_hidden=True),
        ],
    },
    # 12 — Linked List (array-simulated)
    {
        "title": "Club Roster Reverse",
        "slug": "club-roster-reverse",
        "difficulty": "medium",
        "topics": ["linked list", "arrays"],
        "patterns": ["in-place reverse"],
        "problem_statement": (
            "A club roster is stored as a singly linked list encoded by arrays: "
            "values[i] is the member id at node i, and next[i] is the index of the next node "
            "(-1 means end). Head index is given. Reverse the list and print the member ids "
            "from the new head to the end, space-separated. If the list is empty (head = -1), print nothing "
            "(empty line)."
        ),
        "input_format": (
            "First line: n head\n"
            "Second line: n integers values[0..n-1]\n"
            "Third line: n integers next[0..n-1]"
        ),
        "output_format": "Member ids from new head to tail, space-separated (or empty).",
        "constraints": "0 <= n <= 1e4\n-1 <= head < n\nnext[i] is -1 or a valid unused node forming a simple list from head.",
        "examples": [
            {
                "input": "3 0\n1 2 3\n1 2 -1",
                "output": "3 2 1",
                "explanation": "List 1->2->3 becomes 3->2->1.",
            },
            {
                "input": "1 0\n42\n-1",
                "output": "42",
                "explanation": "Single node unchanged.",
            },
        ],
        "explanation": "Iteratively reverse next pointers using prev/curr, then walk from new head printing values.",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(
            '''
import sys
def solve():
    data = list(map(int, sys.stdin.read().split()))
    # Reverse linked list encoded by values/next
    pass
if __name__ == "__main__":
    solve()
''',
            '''
#include <bits/stdc++.h>
using namespace std;
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    return 0;
}
''',
            '''
import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
    }
}
''',
        ),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "data = list(map(int, sys.stdin.read().split()))\n"
                    "if not data:\n"
                    "    print()\n"
                    "    raise SystemExit\n"
                    "n, head = data[0], data[1]\n"
                    "values = data[2:2+n]\n"
                    "nxt = data[2+n:2+2*n]\n"
                    "prev = -1\n"
                    "cur = head\n"
                    "while cur != -1:\n"
                    "    nxt_node = nxt[cur]\n"
                    "    nxt[cur] = prev\n"
                    "    prev = cur\n"
                    "    cur = nxt_node\n"
                    "head = prev\n"
                    "out = []\n"
                    "while head != -1:\n"
                    "    out.append(str(values[head]))\n"
                    "    head = nxt[head]\n"
                    "print(' '.join(out))\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("3 0\n1 2 3\n1 2 -1", "3 2 1", category="normal"),
            _tc("1 0\n42\n-1", "42", category="single"),
            _tc("0 -1\n\n", "", category="empty"),
            _tc("2 1\n10 20\n-1 0", "10 20", category="normal", is_hidden=True),
            _tc("4 0\n4 3 2 1\n1 2 3 -1", "1 2 3 4", category="boundary", is_hidden=True),
            _tc("5 0\n1 2 3 4 5\n1 2 3 4 -1", "5 4 3 2 1", category="adversarial", is_hidden=True),
            _tc("2 0\n1 2\n1 -1", "2 1", category="minimum"),
            _tc("3 2\n5 6 7\n-1 0 1", "5 6 7", category="boundary", is_hidden=True),
        ],
    },
    # 13 — Trees
    {
        "title": "Mentorship Tree Level Sum",
        "slug": "mentorship-tree-level-sum",
        "difficulty": "medium",
        "topics": ["trees", "graphs"],
        "patterns": ["bfs levels"],
        "problem_statement": (
            "A mentorship hierarchy is a binary tree given in level-order with -1 for nulls "
            "(array encoding). Compute the sum of node values on the deepest non-empty level."
        ),
        "input_format": (
            "First line: n (number of entries in the level-order array)\n"
            "Second line: n integers where -1 denotes null (root is index 0 and is never -1 if n>=1)"
        ),
        "output_format": "A single integer — sum of the last level.",
        "constraints": "1 <= n <= 1e4\n-1e4 <= value <= 1e4 for non-null nodes",
        "examples": [
            {
                "input": "7\n1 2 3 4 5 -1 6",
                "output": "15",
                "explanation": "Deepest level nodes are 4,5,6 summing to 15.",
            },
            {
                "input": "1\n10",
                "output": "10",
                "explanation": "Only root.",
            },
        ],
        "explanation": "BFS by levels using child indices 2*i+1 and 2*i+2 when within bounds and not -1; keep the last level sum.",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(n)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(
            '''
import sys
def solve():
    data = list(map(int, sys.stdin.read().split()))
    # Sum of deepest level
    pass
if __name__ == "__main__":
    solve()
''',
            '''
#include <bits/stdc++.h>
using namespace std;
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    return 0;
}
''',
            '''
import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
    }
}
''',
        ),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "from collections import deque\n"
                    "data = list(map(int, sys.stdin.read().split()))\n"
                    "n = data[0]\n"
                    "a = data[1:]\n"
                    "q = deque([0])\n"
                    "last = 0\n"
                    "while q:\n"
                    "    sz = len(q)\n"
                    "    s = 0\n"
                    "    for _ in range(sz):\n"
                    "        i = q.popleft()\n"
                    "        s += a[i]\n"
                    "        L, R = 2*i+1, 2*i+2\n"
                    "        if L < n and a[L] != -1:\n"
                    "            q.append(L)\n"
                    "        if R < n and a[R] != -1:\n"
                    "            q.append(R)\n"
                    "    last = s\n"
                    "print(last)\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("7\n1 2 3 4 5 -1 6", "15", category="normal"),
            _tc("1\n10", "10", category="single"),
            _tc("3\n1 2 3", "5", category="normal"),
            _tc("3\n5 -1 7", "7", category="boundary", is_hidden=True),
            _tc("15\n1 2 3 4 5 6 7 8 9 10 11 12 13 14 15", "92", category="maximum", is_hidden=True),
            _tc("5\n1 2 -1 3 4", "7", category="adversarial", is_hidden=True),
            _tc("7\n0 0 0 0 0 0 0", "0", category="duplicates"),
            _tc("9\n3 1 4 1 5 9 2 6 5", "11", category="normal", is_hidden=True),
        ],
    },
    # 14 — Graphs
    {
        "title": "Lab Network Reachability",
        "slug": "lab-network-reachability",
        "difficulty": "medium",
        "topics": ["graphs"],
        "patterns": ["bfs connectivity"],
        "problem_statement": (
            "Campus labs are nodes in an undirected network. Given n nodes (1..n), m edges, "
            "and a source lab s, print how many labs (including s) are reachable from s."
        ),
        "input_format": (
            "First line: n m s\n"
            "Next m lines: u v (undirected edge)"
        ),
        "output_format": "A single integer — number of reachable labs.",
        "constraints": "1 <= n <= 1e4\n0 <= m <= min(1e5, n*(n-1)/2)\n1 <= s,u,v <= n",
        "examples": [
            {
                "input": "4 3 1\n1 2\n2 3\n4 4",
                "output": "3",
                "explanation": "1-2-3 are connected; 4 is isolated (self-loop ignored for reach).",
            },
            {
                "input": "3 0 2",
                "output": "1",
                "explanation": "No edges; only source.",
            },
        ],
        "explanation": "Build adjacency list (ignore self-loops), BFS/DFS from s, count visited nodes.",
        "expected_time_complexity": "O(n + m)",
        "expected_space_complexity": "O(n + m)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(
            '''
import sys
def solve():
    data = list(map(int, sys.stdin.read().split()))
    # Count reachable nodes from s
    pass
if __name__ == "__main__":
    solve()
''',
            '''
#include <bits/stdc++.h>
using namespace std;
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    return 0;
}
''',
            '''
import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
    }
}
''',
        ),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "from collections import defaultdict, deque\n"
                    "data = list(map(int, sys.stdin.read().split()))\n"
                    "it = iter(data)\n"
                    "n, m, s = next(it), next(it), next(it)\n"
                    "g = defaultdict(list)\n"
                    "for _ in range(m):\n"
                    "    u, v = next(it), next(it)\n"
                    "    if u == v:\n"
                    "        continue\n"
                    "    g[u].append(v)\n"
                    "    g[v].append(u)\n"
                    "seen = {s}\n"
                    "q = deque([s])\n"
                    "while q:\n"
                    "    u = q.popleft()\n"
                    "    for v in g[u]:\n"
                    "        if v not in seen:\n"
                    "            seen.add(v)\n"
                    "            q.append(v)\n"
                    "print(len(seen))\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("4 3 1\n1 2\n2 3\n4 4", "3", category="normal"),
            _tc("3 0 2", "1", category="empty"),
            _tc("1 0 1", "1", category="single"),
            _tc("5 4 1\n1 2\n2 3\n3 4\n4 5", "5", category="maximum", is_hidden=True),
            _tc("4 2 1\n1 2\n3 4", "2", category="boundary"),
            _tc("6 5 6\n1 2\n2 3\n3 1\n4 5\n5 6", "3", category="adversarial", is_hidden=True),
            _tc("2 1 1\n1 2", "2", category="minimum"),
            _tc("5 1 3\n1 2", "1", category="boundary", is_hidden=True),
        ],
    },
    # 15 — Graphs (shortest path BFS)
    {
        "title": "Campus Hop Distance",
        "slug": "campus-hop-distance",
        "difficulty": "medium",
        "topics": ["graphs"],
        "patterns": ["bfs shortest path"],
        "problem_statement": (
            "Buildings form an undirected unweighted graph. Find the minimum number of hops "
            "from building A to building B. If unreachable, print -1."
        ),
        "input_format": (
            "First line: n m A B\n"
            "Next m lines: u v"
        ),
        "output_format": "A single integer — shortest hop count, or -1.",
        "constraints": "1 <= n <= 1e4\n0 <= m <= 1e5\n1 <= A,B,u,v <= n",
        "examples": [
            {
                "input": "4 4 1 4\n1 2\n2 3\n3 4\n1 3",
                "output": "2",
                "explanation": "1-3-4 is two hops.",
            },
            {
                "input": "3 1 1 3\n1 2",
                "output": "-1",
                "explanation": "3 is unreachable.",
            },
        ],
        "explanation": "Standard BFS from A; first time B is reached gives the distance.",
        "expected_time_complexity": "O(n + m)",
        "expected_space_complexity": "O(n + m)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(
            '''
import sys
def solve():
    data = list(map(int, sys.stdin.read().split()))
    # Shortest hops A to B
    pass
if __name__ == "__main__":
    solve()
''',
            '''
#include <bits/stdc++.h>
using namespace std;
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    return 0;
}
''',
            '''
import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
    }
}
''',
        ),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "from collections import defaultdict, deque\n"
                    "data = list(map(int, sys.stdin.read().split()))\n"
                    "it = iter(data)\n"
                    "n, m, A, B = next(it), next(it), next(it), next(it)\n"
                    "g = defaultdict(list)\n"
                    "for _ in range(m):\n"
                    "    u, v = next(it), next(it)\n"
                    "    if u == v:\n"
                    "        continue\n"
                    "    g[u].append(v)\n"
                    "    g[v].append(u)\n"
                    "if A == B:\n"
                    "    print(0)\n"
                    "else:\n"
                    "    dist = {A: 0}\n"
                    "    q = deque([A])\n"
                    "    ans = -1\n"
                    "    while q:\n"
                    "        u = q.popleft()\n"
                    "        for v in g[u]:\n"
                    "            if v not in dist:\n"
                    "                dist[v] = dist[u] + 1\n"
                    "                if v == B:\n"
                    "                    ans = dist[v]\n"
                    "                    q.clear()\n"
                    "                    break\n"
                    "                q.append(v)\n"
                    "    print(ans)\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("4 4 1 4\n1 2\n2 3\n3 4\n1 3", "2", category="normal"),
            _tc("3 1 1 3\n1 2", "-1", category="boundary"),
            _tc("1 0 1 1", "0", category="single"),
            _tc("2 1 1 2\n1 2", "1", category="minimum"),
            _tc("5 4 1 5\n1 2\n2 3\n3 4\n4 5", "4", category="maximum", is_hidden=True),
            _tc("4 3 2 4\n1 2\n2 3\n3 1", "-1", category="adversarial", is_hidden=True),
            _tc("6 5 1 6\n1 2\n2 3\n3 4\n4 5\n5 6", "5", category="normal", is_hidden=True),
            _tc("3 3 1 2\n1 2\n2 3\n3 1", "1", category="duplicates", is_hidden=True),
        ],
    },
    # 16 — Greedy
    {
        "title": "Internship Slot Booking",
        "slug": "internship-slot-booking",
        "difficulty": "medium",
        "topics": ["greedy", "arrays"],
        "patterns": ["activity selection"],
        "problem_statement": (
            "Each internship interview occupies a half-open interval [L, R). "
            "You can attend at most one interview at a time. Given n intervals, "
            "find the maximum number you can attend."
        ),
        "input_format": (
            "First line: n\n"
            "Next n lines: L R"
        ),
        "output_format": "A single integer — maximum non-overlapping interviews.",
        "constraints": "1 <= n <= 1e5\n0 <= L < R <= 1e9",
        "examples": [
            {
                "input": "3\n1 3\n2 4\n3 5",
                "output": "2",
                "explanation": "Take [1,3) and [3,5).",
            },
            {
                "input": "2\n1 10\n2 3",
                "output": "1",
                "explanation": "They overlap; pick either one.",
            },
        ],
        "explanation": "Sort by end time; greedily take an interval if its start is >= last chosen end.",
        "expected_time_complexity": "O(n log n)",
        "expected_space_complexity": "O(n)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(
            '''
import sys
def solve():
    data = list(map(int, sys.stdin.read().split()))
    # Max non-overlapping intervals
    pass
if __name__ == "__main__":
    solve()
''',
            '''
#include <bits/stdc++.h>
using namespace std;
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    return 0;
}
''',
            '''
import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
    }
}
''',
        ),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "data = list(map(int, sys.stdin.read().split()))\n"
                    "n = data[0]\n"
                    "iv = [(data[i], data[i+1]) for i in range(1, 2*n+1, 2)]\n"
                    "iv.sort(key=lambda x: x[1])\n"
                    "cnt = 0\n"
                    "end = -1\n"
                    "for L, R in iv:\n"
                    "    if L >= end:\n"
                    "        cnt += 1\n"
                    "        end = R\n"
                    "print(cnt)\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("3\n1 3\n2 4\n3 5", "2", category="normal"),
            _tc("2\n1 10\n2 3", "1", category="normal"),
            _tc("1\n0 1", "1", category="single"),
            _tc("4\n1 2\n2 3\n3 4\n4 5", "4", category="maximum", is_hidden=True),
            _tc("3\n1 5\n1 5\n1 5", "1", category="duplicates"),
            _tc("5\n0 2\n1 3\n2 4\n3 5\n4 6", "3", category="boundary", is_hidden=True),
            _tc("3\n5 6\n1 2\n3 4", "3", category="adversarial", is_hidden=True),
            _tc("2\n1 2\n2 3", "2", category="boundary", is_hidden=True),
        ],
    },
    # 17 — Recursion
    {
        "title": "Power Tower Modulo",
        "slug": "power-tower-modulo",
        "difficulty": "easy",
        "topics": ["recursion", "math"],
        "patterns": ["fast exponentiation"],
        "problem_statement": (
            "Compute (base ^ exp) mod MOD for non-negative integers using fast exponentiation. "
            "MOD is fixed at 1000000007. Print a single integer."
        ),
        "input_format": "A single line: base exp",
        "output_format": "base^exp modulo 1000000007",
        "constraints": "0 <= base, exp <= 1e9",
        "examples": [
            {
                "input": "2 10",
                "output": "1024",
                "explanation": "2^10 = 1024.",
            },
            {
                "input": "3 0",
                "output": "1",
                "explanation": "Any nonzero^0 is 1; 0^0 treated as 1 here.",
            },
        ],
        "explanation": "Recursive or iterative binary exponentiation with modular multiplications.",
        "expected_time_complexity": "O(log exp)",
        "expected_space_complexity": "O(log exp)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(
            '''
import sys
MOD = 10**9 + 7
def solve():
    base, exp = map(int, sys.stdin.read().split())
    # Modular power
    pass
if __name__ == "__main__":
    solve()
''',
            '''
#include <bits/stdc++.h>
using namespace std;
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    return 0;
}
''',
            '''
import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
    }
}
''',
        ),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "MOD = 10**9 + 7\n"
                    "base, exp = map(int, sys.stdin.read().split())\n"
                    "\n"
                    "def modpow(b, e):\n"
                    "    if e == 0:\n"
                    "        return 1\n"
                    "    half = modpow(b, e // 2)\n"
                    "    half = (half * half) % MOD\n"
                    "    if e % 2:\n"
                    "        half = (half * (b % MOD)) % MOD\n"
                    "    return half\n"
                    "\n"
                    "print(modpow(base, exp))\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("2 10", "1024", category="normal"),
            _tc("3 0", "1", category="boundary"),
            _tc("0 5", "0", category="boundary"),
            _tc("0 0", "1", category="minimum", is_hidden=True),
            _tc("2 30", "73741817", category="large", is_hidden=True),
            _tc("123456789 1", "123456789", category="single"),
            _tc("5 3", "125", category="normal", is_hidden=True),
            _tc("10 9", "1000000000", category="boundary", is_hidden=True),
        ],
    },
    # 18 — Backtracking
    {
        "title": "Club Project Combinations",
        "slug": "club-project-combinations",
        "difficulty": "medium",
        "topics": ["backtracking", "recursion"],
        "patterns": ["combinations"],
        "problem_statement": (
            "A club must choose exactly k distinct project ids from 1..n. "
            "Print all combinations in lexicographic order, one per line, "
            "with ids space-separated. If none, print nothing."
        ),
        "input_format": "A single line: n k",
        "output_format": "All combinations, each on its own line (lexicographic).",
        "constraints": "1 <= n <= 15\n0 <= k <= n",
        "examples": [
            {
                "input": "4 2",
                "output": "1 2\n1 3\n1 4\n2 3\n2 4\n3 4",
                "explanation": "All pairs from 1..4.",
            },
            {
                "input": "3 3",
                "output": "1 2 3",
                "explanation": "Only one full set.",
            },
        ],
        "explanation": "Backtracking that always appends a number larger than the last chosen.",
        "expected_time_complexity": "O(C(n,k) * k)",
        "expected_space_complexity": "O(k)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(
            '''
import sys
def solve():
    n, k = map(int, sys.stdin.read().split())
    # Print all combinations
    pass
if __name__ == "__main__":
    solve()
''',
            '''
#include <bits/stdc++.h>
using namespace std;
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    return 0;
}
''',
            '''
import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
    }
}
''',
        ),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "n, k = map(int, sys.stdin.read().split())\n"
                    "out = []\n"
                    "\n"
                    "def dfs(start, path):\n"
                    "    if len(path) == k:\n"
                    "        out.append(' '.join(map(str, path)))\n"
                    "        return\n"
                    "    for i in range(start, n + 1):\n"
                    "        path.append(i)\n"
                    "        dfs(i + 1, path)\n"
                    "        path.pop()\n"
                    "\n"
                    "dfs(1, [])\n"
                    "print('\\n'.join(out))\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("4 2", "1 2\n1 3\n1 4\n2 3\n2 4\n3 4", category="normal"),
            _tc("3 3", "1 2 3", category="normal"),
            _tc("3 0", "", category="empty"),
            _tc("1 1", "1", category="single"),
            _tc("5 1", "1\n2\n3\n4\n5", category="boundary", is_hidden=True),
            _tc("3 1", "1\n2\n3", category="minimum", is_hidden=True),
            _tc("5 5", "1 2 3 4 5", category="maximum", is_hidden=True),
            _tc("2 2", "1 2", category="boundary", is_hidden=True),
        ],
    },
    # 19 — Dynamic Programming
    {
        "title": "Internship Stipend Path",
        "slug": "internship-stipend-path",
        "difficulty": "medium",
        "topics": ["dynamic programming", "arrays"],
        "patterns": ["grid path dp"],
        "problem_statement": (
            "A stipend board is an R x C grid of numbers. You start at the top-left and may "
            "only move right or down to the bottom-right. Maximize the sum of collected cells."
        ),
        "input_format": (
            "First line: R C\n"
            "Next R lines: C integers each"
        ),
        "output_format": "A single integer — maximum path sum.",
        "constraints": "1 <= R, C <= 100\n-100 <= grid[i][j] <= 100",
        "examples": [
            {
                "input": "2 3\n1 2 3\n4 5 6",
                "output": "16",
                "explanation": "Path 1 → 4 → 5 → 6 sums to 16, which is maximal.",
            },
            {
                "input": "1 1\n7",
                "output": "7",
                "explanation": "Single cell.",
            },
        ],
        "explanation": "DP[i][j] = grid[i][j] + max(from top, from left), carefully handling first row/col.",
        "expected_time_complexity": "O(R*C)",
        "expected_space_complexity": "O(R*C)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(
            '''
import sys
def solve():
    data = list(map(int, sys.stdin.read().split()))
    # Max path sum right/down
    pass
if __name__ == "__main__":
    solve()
''',
            '''
#include <bits/stdc++.h>
using namespace std;
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    return 0;
}
''',
            '''
import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
    }
}
''',
        ),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "data = list(map(int, sys.stdin.read().split()))\n"
                    "R, C = data[0], data[1]\n"
                    "g = data[2:]\n"
                    "grid = [g[i*C:(i+1)*C] for i in range(R)]\n"
                    "dp = [[0]*C for _ in range(R)]\n"
                    "dp[0][0] = grid[0][0]\n"
                    "for j in range(1, C):\n"
                    "    dp[0][j] = dp[0][j-1] + grid[0][j]\n"
                    "for i in range(1, R):\n"
                    "    dp[i][0] = dp[i-1][0] + grid[i][0]\n"
                    "for i in range(1, R):\n"
                    "    for j in range(1, C):\n"
                    "        dp[i][j] = grid[i][j] + max(dp[i-1][j], dp[i][j-1])\n"
                    "print(dp[R-1][C-1])\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("2 3\n1 2 3\n4 5 6", "16", category="normal"),
            _tc("1 1\n7", "7", category="single"),
            _tc("3 3\n1 1 1\n1 1 1\n1 1 1", "5", category="duplicates"),
            _tc("2 2\n-1 -2\n-3 -4", "-7", category="negative", is_hidden=True),
            _tc("1 4\n1 2 3 4", "10", category="boundary"),
            _tc("4 1\n1\n2\n3\n4", "10", category="boundary", is_hidden=True),
            _tc("3 3\n5 0 0\n1 0 0\n1 1 10", "18", category="adversarial", is_hidden=True),
            _tc("2 3\n10 -1 5\n-2 3 4", "18", category="normal", is_hidden=True),
        ],
    },
    # 20 — Dynamic Programming (harder)
    {
        "title": "Prep Hours Knapsack",
        "slug": "prep-hours-knapsack",
        "difficulty": "hard",
        "topics": ["dynamic programming"],
        "patterns": ["0-1 knapsack"],
        "problem_statement": (
            "You have H study hours before placements. Topic i needs hours[i] and yields "
            "score[i] if completed fully (0-1). Maximize total score without exceeding H hours."
        ),
        "input_format": (
            "First line: n H\n"
            "Second line: n integers hours\n"
            "Third line: n integers scores"
        ),
        "output_format": "A single integer — maximum achievable score.",
        "constraints": "1 <= n <= 100\n1 <= H <= 1000\n1 <= hours[i] <= H\n1 <= scores[i] <= 1000",
        "examples": [
            {
                "input": "3 5\n2 3 4\n3 4 5",
                "output": "7",
                "explanation": "Take first two topics: 2+3 hours, score 3+4=7.",
            },
            {
                "input": "2 3\n2 2\n5 6",
                "output": "6",
                "explanation": "Only one topic fits; pick score 6.",
            },
        ],
        "explanation": "Classic 0-1 knapsack DP over hours capacity.",
        "expected_time_complexity": "O(n*H)",
        "expected_space_complexity": "O(H)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(
            '''
import sys
def solve():
    data = list(map(int, sys.stdin.read().split()))
    # 0-1 knapsack max score
    pass
if __name__ == "__main__":
    solve()
''',
            '''
#include <bits/stdc++.h>
using namespace std;
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    return 0;
}
''',
            '''
import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
    }
}
''',
        ),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "data = list(map(int, sys.stdin.read().split()))\n"
                    "n, H = data[0], data[1]\n"
                    "hours = data[2:2+n]\n"
                    "scores = data[2+n:2+2*n]\n"
                    "dp = [0]*(H+1)\n"
                    "for h, s in zip(hours, scores):\n"
                    "    for cap in range(H, h-1, -1):\n"
                    "        dp[cap] = max(dp[cap], dp[cap-h] + s)\n"
                    "print(dp[H])\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("3 5\n2 3 4\n3 4 5", "7", category="normal"),
            _tc("2 3\n2 2\n5 6", "6", category="normal"),
            _tc("1 1\n1\n10", "10", category="single"),
            _tc("4 10\n5 5 5 5\n1 2 3 4", "7", category="duplicates", is_hidden=True),
            _tc("3 4\n5 5 5\n9 9 9", "0", category="boundary"),
            _tc("5 8\n1 2 3 4 5\n1 2 3 4 5", "8", category="adversarial", is_hidden=True),
            _tc("3 6\n2 2 2\n10 10 10", "30", category="maximum", is_hidden=True),
            _tc("4 5\n1 2 3 4\n5 3 4 8", "13", category="boundary", is_hidden=True),
        ],
    },
    # 21 — Hashing
    {
        "title": "ID Card Frequency Audit",
        "slug": "id-card-frequency-audit",
        "difficulty": "easy",
        "topics": ["hashing", "arrays"],
        "patterns": ["frequency map"],
        "problem_statement": (
            "Given n student ID numbers (may repeat), print the ID that appears most often. "
            "If there is a tie, print the smaller ID."
        ),
        "input_format": "First line: n\nSecond line: n integers",
        "output_format": "A single integer — the mode (tie -> smaller ID).",
        "constraints": "1 <= n <= 1e5\n1 <= id <= 1e9",
        "examples": [
            {
                "input": "5\n1 2 2 3 1",
                "output": "1",
                "explanation": "1 and 2 both appear twice; smaller is 1.",
            },
            {
                "input": "3\n5 5 5",
                "output": "5",
                "explanation": "Only one distinct ID.",
            },
        ],
        "explanation": "Count frequencies with a hash map; track best count and smallest ID on ties.",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(n)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(
            '''
import sys
def solve():
    data = list(map(int, sys.stdin.read().split()))
    # Mode with tie -> smaller
    pass
if __name__ == "__main__":
    solve()
''',
            '''
#include <bits/stdc++.h>
using namespace std;
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    return 0;
}
''',
            '''
import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
    }
}
''',
        ),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "from collections import Counter\n"
                    "data = list(map(int, sys.stdin.read().split()))\n"
                    "n = data[0]\n"
                    "a = data[1:]\n"
                    "cnt = Counter(a)\n"
                    "best = min(cnt.items(), key=lambda kv: (-kv[1], kv[0]))\n"
                    "print(best[0])\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("5\n1 2 2 3 1", "1", category="normal"),
            _tc("3\n5 5 5", "5", category="duplicates"),
            _tc("1\n42", "42", category="single"),
            _tc("4\n9 8 7 6", "6", category="boundary", is_hidden=True),
            _tc("6\n3 3 2 2 1 1", "1", category="duplicates", is_hidden=True),
            _tc("7\n4 4 4 2 2 2 2", "2", category="adversarial"),
            _tc("5\n10 10 10 10 1", "10", category="maximum", is_hidden=True),
            _tc("2\n100 99", "99", category="minimum", is_hidden=True),
        ],
    },
    # 22 — Recursion / Trees-ish
    {
        "title": "Factorial Scoreboard",
        "slug": "factorial-scoreboard",
        "difficulty": "easy",
        "topics": ["recursion"],
        "patterns": ["simple recursion"],
        "problem_statement": (
            "The fun-fair scoreboard shows n! (factorial) for a non-negative integer n. "
            "Compute n! and print it. Constraints keep the result within a 64-bit signed range."
        ),
        "input_format": "A single integer n",
        "output_format": "n! as an integer",
        "constraints": "0 <= n <= 20",
        "examples": [
            {"input": "5", "output": "120", "explanation": "5! = 120."},
            {"input": "0", "output": "1", "explanation": "0! = 1."},
        ],
        "explanation": "Recursive definition: n! = n*(n-1)! with base 0! = 1.",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(n)",
        "supported_languages": _LANGS,
        "starter_code": _starter_trio(
            '''
import sys
def solve():
    n = int(sys.stdin.read().strip())
    # Compute factorial
    pass
if __name__ == "__main__":
    solve()
''',
            '''
#include <bits/stdc++.h>
using namespace std;
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    return 0;
}
''',
            '''
import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
    }
}
''',
        ),
        "reference_solutions": [
            {
                "language": "python",
                "code": (
                    "import sys\n"
                    "n = int(sys.stdin.read().strip())\n"
                    "\n"
                    "def fact(x):\n"
                    "    if x <= 1:\n"
                    "        return 1\n"
                    "    return x * fact(x - 1)\n"
                    "\n"
                    "print(fact(n))\n"
                ),
            }
        ],
        "candidate_test_cases": [
            _tc("5", "120", category="normal"),
            _tc("0", "1", category="boundary"),
            _tc("1", "1", category="single"),
            _tc("10", "3628800", category="normal", is_hidden=True),
            _tc("20", "2432902008176640000", category="maximum", is_hidden=True),
            _tc("3", "6", category="minimum"),
            _tc("7", "5040", category="normal", is_hidden=True),
            _tc("12", "479001600", category="boundary", is_hidden=True),
        ],
    },
]


def catalog_as_contracts():
    from app.coding_bank.schemas import GeneratedProblemContract

    return [GeneratedProblemContract.model_validate(x) for x in PLACEMENT_BANK_V1]
