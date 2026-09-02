"""GfG-style placement bank for 4th-year engineering students (easy + medium only).

Classic DSA patterns with clear statements and stdin starter code.
Inspired by common GeeksforGeeks campus topics — original wording, not copied text.
"""

from __future__ import annotations

from app.coding_bank.starter_builders import (
    _LANGS,
    cpp_starter,
    java_starter,
    py_starter,
    starter_trio,
    trio_from_py_comment,
)


def _tc(
    inp: str,
    out: str,
    *,
    is_hidden: bool = False,
    category: str = "normal",
    weight: float = 1.0,
) -> dict:
    return {
        "input": inp,
        "expected_output": out,
        "is_hidden": is_hidden,
        "weight": weight,
        "category": category,
    }


def _ref(py: str, notes: str = "") -> list[dict]:
    return [{"language": "python", "code": py, "notes": notes or None}]


GFG_PLACEMENT_BANK: list[dict] = [
    # --- Arrays (easy) ---
    {
        "title": "Two Sum — Return Indices",
        "slug": "two-sum-indices",
        "difficulty": "easy",
        "topics": ["arrays", "hashing"],
        "patterns": ["hashmap complement"],
        "problem_statement": (
            "Given an array of n integers and a target value T, find two distinct positions "
            "(1-based indices) such that the values at those positions add up to T. "
            "Exactly one valid pair exists. This is the classic Two Sum pattern asked in "
            "campus OA and product screening rounds."
        ),
        "input_format": "Line 1: n\nLine 2: n integers\nLine 3: T",
        "output_format": "Two 1-based indices i j (i < j) separated by a space.",
        "constraints": "2 <= n <= 1e5\n-1e9 <= values, T <= 1e9\nAll values distinct.",
        "examples": [
            {"input": "4\n2 7 11 15\n9", "output": "1 2", "explanation": "2 + 7 = 9."},
            {"input": "3\n3 2 4\n6", "output": "2 3", "explanation": "2 + 4 = 6."},
        ],
        "explanation": "Store each value's index in a hash map. For x, check if T-x was seen.",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(n)",
        "supported_languages": _LANGS,
        "starter_code": trio_from_py_comment(
            "Classic Two Sum — hash map complement lookup",
            """    data = list(map(int, sys.stdin.read().split()))
    n = data[0]
    nums = data[1:1 + n]
    target = data[1 + n]
    # Return 1-based indices of two numbers that sum to target
    pass""",
        ),
        "reference_solutions": _ref(
            "import sys\n"
            "data = list(map(int, sys.stdin.read().split()))\n"
            "n = data[0]\n"
            "nums = data[1:1+n]\n"
            "T = data[1+n]\n"
            "seen = {}\n"
            "for i, x in enumerate(nums):\n"
            "    if T - x in seen:\n"
            "        print(seen[T-x] + 1, i + 1)\n"
            "        break\n"
            "    seen[x] = i\n"
        ),
        "candidate_test_cases": [
            _tc("4\n2 7 11 15\n9", "1 2"),
            _tc("3\n3 2 4\n6", "2 3", is_hidden=True),
            _tc("2\n1 2\n3", "1 2", category="minimum"),
            _tc("5\n0 -1 2 -3 5\n-4", "2 4", category="negative", is_hidden=True),
            _tc("4\n10 20 35 40\n50", "1 4", category="boundary"),
            _tc("5\n8 1 9 3 4\n13", "3 5", is_hidden=True),
            _tc("3\n1000000000 -1000000000 0\n0", "1 2", category="boundary", is_hidden=True),
            _tc("5\n5 1 9 3 8\n13", "1 5"),
        ],
    },
    {
        "title": "Reverse an Array",
        "slug": "reverse-array-in-place",
        "difficulty": "easy",
        "topics": ["arrays"],
        "patterns": ["two pointers swap"],
        "problem_statement": (
            "Given an array of n integers, reverse the array and print the result "
            "space-separated on one line. Classic warm-up from GeeksforGeeks arrays section."
        ),
        "input_format": "Line 1: n\nLine 2: n integers",
        "output_format": "Reversed array, space-separated.",
        "constraints": "1 <= n <= 1e5\n-1e9 <= a[i] <= 1e9",
        "examples": [
            {"input": "5\n1 2 3 4 5", "output": "5 4 3 2 1"},
            {"input": "1\n9", "output": "9"},
        ],
        "explanation": "Swap elements from both ends moving inward — O(n) time, O(1) extra space.",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": trio_from_py_comment(
            "Reverse array using two pointers",
            """    data = list(map(int, sys.stdin.read().split()))
    n = data[0]
    arr = data[1:1 + n]
    # Reverse arr and print space-separated
    pass""",
        ),
        "reference_solutions": _ref(
            "import sys\n"
            "data = list(map(int, sys.stdin.read().split()))\n"
            "n = data[0]\n"
            "a = data[1:1+n]\n"
            "a.reverse()\n"
            "print(' '.join(map(str, a)))\n"
        ),
        "candidate_test_cases": [
            _tc("5\n1 2 3 4 5", "5 4 3 2 1"),
            _tc("1\n9", "9", category="single"),
            _tc("2\n3 7", "7 3", category="minimum"),
            _tc("4\n-1 0 0 1", "1 0 0 -1", category="negative", is_hidden=True),
            _tc("6\n10 20 30 40 50 60", "60 50 40 30 20 10", is_hidden=True),
            _tc("3\n5 5 5", "5 5 5", category="duplicates"),
            _tc("4\n0 0 0 0", "0 0 0 0", category="empty"),
            _tc("3\n100 -50 25", "25 -50 100", category="boundary"),
        ],
    },
    # --- Strings (easy) ---
    {
        "title": "Check Valid Anagram",
        "slug": "valid-anagram-check",
        "difficulty": "easy",
        "topics": ["strings", "hashing"],
        "patterns": ["frequency count"],
        "problem_statement": (
            "Given two strings S and T of lowercase letters, determine if T is an anagram of S "
            "(same letters, same counts, possibly different order). Print YES or NO."
        ),
        "input_format": "Two lines: string S, then string T.",
        "output_format": "YES or NO",
        "constraints": "1 <= |S|, |T| <= 1e5\nLowercase English letters only.",
        "examples": [
            {"input": "listen\nsilent", "output": "YES"},
            {"input": "hello\nbello", "output": "NO"},
        ],
        "explanation": "Count character frequencies in both strings and compare.",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": trio_from_py_comment(
            "Compare character frequencies of two strings",
            """    lines = sys.stdin.read().splitlines()
    s = lines[0].strip()
    t = lines[1].strip()
    # Print YES if anagrams else NO
    pass""",
        ),
        "reference_solutions": _ref(
            "import sys\n"
            "from collections import Counter\n"
            "lines = sys.stdin.read().splitlines()\n"
            "s, t = lines[0].strip(), lines[1].strip()\n"
            "print('YES' if Counter(s) == Counter(t) else 'NO')\n"
        ),
        "candidate_test_cases": [
            _tc("listen\nsilent", "YES"),
            _tc("hello\nbello", "NO"),
            _tc("a\na", "YES", category="single"),
            _tc("ab\nba", "YES", category="minimum"),
            _tc("abc\nab", "NO", category="boundary", is_hidden=True),
            _tc("aaa\naaa", "YES", category="duplicates"),
            _tc("rat\ncar", "NO", is_hidden=True),
            _tc("anagram\nnagaram", "YES", category="normal", is_hidden=True),
        ],
    },
    {
        "title": "Palindrome String Check",
        "slug": "palindrome-string-check",
        "difficulty": "easy",
        "topics": ["strings", "two pointers"],
        "patterns": ["two pointers"],
        "problem_statement": (
            "Given a string S, check whether it reads the same forwards and backwards. "
            "Print YES if palindrome, otherwise NO. Case-sensitive."
        ),
        "input_format": "A single line string S (no spaces).",
        "output_format": "YES or NO",
        "constraints": "1 <= |S| <= 1e5",
        "examples": [
            {"input": "madam", "output": "YES"},
            {"input": "campus", "output": "NO"},
        ],
        "explanation": "Compare characters from both ends or compare S with S[::-1].",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": trio_from_py_comment(
            "Two-pointer palindrome check",
            """    s = sys.stdin.read().strip()
    # Print YES if palindrome else NO
    pass""",
        ),
        "reference_solutions": _ref(
            "import sys\n"
            "s = sys.stdin.read().strip()\n"
            "print('YES' if s == s[::-1] else 'NO')\n"
        ),
        "candidate_test_cases": [
            _tc("madam", "YES"),
            _tc("campus", "NO"),
            _tc("a", "YES", category="single"),
            _tc("aa", "YES", category="minimum"),
            _tc("ab", "NO", category="minimum", is_hidden=True),
            _tc("12321", "YES", is_hidden=True),
            _tc("AbA", "YES", category="boundary"),
            _tc("racecar", "YES", is_hidden=True),
        ],
    },
    # --- Hashing (easy) ---
    {
        "title": "Most Frequent Element",
        "slug": "most-frequent-element",
        "difficulty": "easy",
        "topics": ["hashing", "arrays"],
        "patterns": ["frequency map"],
        "problem_statement": (
            "Given n integers, find the value that appears most often. "
            "If multiple values tie, print the smallest one."
        ),
        "input_format": "Line 1: n\nLine 2: n integers",
        "output_format": "A single integer — the answer value.",
        "constraints": "1 <= n <= 1e5\n-1e9 <= a[i] <= 1e9",
        "examples": [
            {"input": "6\n1 2 2 3 3 3", "output": "3"},
            {"input": "4\n5 5 1 1", "output": "1"},
        ],
        "explanation": "Use a hash map to count frequencies, then pick max count with smallest value on tie.",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(n)",
        "supported_languages": _LANGS,
        "starter_code": trio_from_py_comment(
            "Count frequencies with hash map",
            """    data = list(map(int, sys.stdin.read().split()))
    n = data[0]
    arr = data[1:1 + n]
    # Print most frequent value (smallest on tie)
    pass""",
        ),
        "reference_solutions": _ref(
            "import sys\n"
            "from collections import Counter\n"
            "data = list(map(int, sys.stdin.read().split()))\n"
            "n = data[0]\n"
            "a = data[1:1+n]\n"
            "c = Counter(a)\n"
            "best = max(c.values())\n"
            "ans = min(k for k, v in c.items() if v == best)\n"
            "print(ans)\n"
        ),
        "candidate_test_cases": [
            _tc("6\n1 2 2 3 3 3", "3"),
            _tc("4\n5 5 1 1", "1"),
            _tc("1\n42", "42", category="single"),
            _tc("5\n7 7 7 7 7", "7", category="duplicates"),
            _tc("3\n-1 -1 2", "-1", category="negative", is_hidden=True),
            _tc("4\n10 20 10 20", "10", is_hidden=True),
            _tc("6\n1 1 2 2 3 3", "1", category="boundary"),
            _tc("5\n0 0 1 2 2", "0", is_hidden=True),
        ],
    },
    # --- Math (easy) ---
    {
        "title": "GCD of Two Numbers",
        "slug": "gcd-two-numbers",
        "difficulty": "easy",
        "topics": ["math"],
        "patterns": ["euclidean algorithm"],
        "problem_statement": (
            "Given two positive integers A and B, compute their greatest common divisor (GCD) "
            "using Euclid's algorithm — a standard GeeksforGeeks math topic."
        ),
        "input_format": "Two integers A and B on one line.",
        "output_format": "A single integer — GCD(A, B).",
        "constraints": "1 <= A, B <= 1e12",
        "examples": [
            {"input": "12 18", "output": "6"},
            {"input": "7 13", "output": "1"},
        ],
        "explanation": "Repeatedly replace (a,b) with (b, a mod b) until b becomes 0.",
        "expected_time_complexity": "O(log min(A,B))",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": trio_from_py_comment(
            "Euclidean GCD algorithm",
            """    a, b = map(int, sys.stdin.read().split())
    # Print GCD(a, b)
    pass""",
        ),
        "reference_solutions": _ref(
            "import sys\n"
            "import math\n"
            "a, b = map(int, sys.stdin.read().split())\n"
            "print(math.gcd(a, b))\n"
        ),
        "candidate_test_cases": [
            _tc("12 18", "6"),
            _tc("7 13", "1"),
            _tc("1 1", "1", category="minimum"),
            _tc("100 25", "25", category="boundary"),
            _tc("54 24", "6", is_hidden=True),
            _tc("17 17", "17", category="duplicates"),
            _tc("1000000000000 1", "1", category="maximum", is_hidden=True),
            _tc("48 18", "6", is_hidden=True),
        ],
    },
    # --- Two Pointers (easy) ---
    {
        "title": "Pair with Given Sum in Sorted Array",
        "slug": "pair-sum-sorted-array",
        "difficulty": "easy",
        "topics": ["arrays", "two pointers"],
        "patterns": ["two pointers"],
        "problem_statement": (
            "A sorted array and target T are given. Determine if any two elements sum to T. "
            "Print YES or NO. Classic two-pointer pattern from GfG."
        ),
        "input_format": "Line 1: n T\nLine 2: n sorted integers",
        "output_format": "YES or NO",
        "constraints": "2 <= n <= 1e5\n-1e9 <= values, T <= 1e9\nArray is non-decreasing.",
        "examples": [
            {"input": "5 9\n1 2 4 5 6", "output": "YES"},
            {"input": "4 10\n1 2 3 4", "output": "NO"},
        ],
        "explanation": "Left pointer at start, right at end; move based on whether sum is too small or large.",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": trio_from_py_comment(
            "Two pointers on sorted array",
            """    data = list(map(int, sys.stdin.read().split()))
    n, T = data[0], data[1]
    arr = data[2:2 + n]
    # Print YES if any pair sums to T
    pass""",
        ),
        "reference_solutions": _ref(
            "import sys\n"
            "data = list(map(int, sys.stdin.read().split()))\n"
            "n, T = data[0], data[1]\n"
            "a = data[2:2+n]\n"
            "i, j = 0, n - 1\n"
            "ok = False\n"
            "while i < j:\n"
            "    s = a[i] + a[j]\n"
            "    if s == T:\n"
            "        ok = True\n"
            "        break\n"
            "    elif s < T:\n"
            "        i += 1\n"
            "    else:\n"
            "        j -= 1\n"
            "print('YES' if ok else 'NO')\n"
        ),
        "candidate_test_cases": [
            _tc("5 9\n1 2 4 5 6", "YES"),
            _tc("4 10\n1 2 3 4", "NO"),
            _tc("2 3\n1 2", "YES", category="minimum"),
            _tc("2 4\n1 2", "NO", category="minimum", is_hidden=True),
            _tc("2 0\n-5 5", "YES", category="negative", is_hidden=True),
            _tc("5 11\n1 3 5 7 9", "NO"),
            _tc("3 100\n1 50 101", "NO", category="boundary", is_hidden=True),
            _tc("4 4\n2 2 2 2", "YES", category="duplicates"),
        ],
    },
    # --- Sliding Window (easy) ---
    {
        "title": "Maximum Sum Subarray of Size K",
        "slug": "max-sum-subarray-size-k",
        "difficulty": "easy",
        "topics": ["arrays", "sliding window"],
        "patterns": ["fixed window"],
        "problem_statement": (
            "Given an array of n integers and window size k, find the maximum sum of any "
            "contiguous subarray of exactly k elements. Standard sliding-window warm-up."
        ),
        "input_format": "Line 1: n k\nLine 2: n integers",
        "output_format": "A single integer — maximum k-window sum.",
        "constraints": "1 <= k <= n <= 1e5\n-1e4 <= a[i] <= 1e4",
        "examples": [
            {"input": "5 3\n2 1 5 1 3", "output": "9"},
            {"input": "4 2\n-1 -2 -3 -4", "output": "-3"},
        ],
        "explanation": "Compute first window sum, slide by adding next and removing previous element.",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": trio_from_py_comment(
            "Fixed-size sliding window sum",
            """    data = list(map(int, sys.stdin.read().split()))
    n, k = data[0], data[1]
    arr = data[2:2 + n]
    # Print max sum of any k-length subarray
    pass""",
        ),
        "reference_solutions": _ref(
            "import sys\n"
            "data = list(map(int, sys.stdin.read().split()))\n"
            "n, k = data[0], data[1]\n"
            "a = data[2:2+n]\n"
            "s = sum(a[:k])\n"
            "best = s\n"
            "for i in range(k, n):\n"
            "    s += a[i] - a[i-k]\n"
            "    best = max(best, s)\n"
            "print(best)\n"
        ),
        "candidate_test_cases": [
            _tc("5 3\n2 1 5 1 3", "9"),
            _tc("4 2\n-1 -2 -3 -4", "-3", category="negative"),
            _tc("1 1\n42", "42", category="single"),
            _tc("6 6\n1 2 3 4 5 6", "21", category="maximum", is_hidden=True),
            _tc("5 4\n1 1 1 1 100", "103", category="boundary"),
            _tc("7 3\n4 2 -1 9 0 3 1", "12", is_hidden=True),
            _tc("3 2\n0 0 0", "0", category="empty"),
            _tc("6 1\n3 -5 7 0 2 -1", "7", category="boundary"),
        ],
    },
    # --- Sliding Window (medium) ---
    {
        "title": "Longest Substring Without Repeating Characters",
        "slug": "longest-unique-substring",
        "difficulty": "medium",
        "topics": ["strings", "sliding window", "hashing"],
        "patterns": ["variable window"],
        "problem_statement": (
            "Given a lowercase string S, find the length of the longest substring that contains "
            "no repeated character. Medium classic — often asked after easy string warm-ups."
        ),
        "input_format": "A single line lowercase string S.",
        "output_format": "A single integer — maximum length.",
        "constraints": "1 <= |S| <= 1e5",
        "examples": [
            {"input": "abcabcbb", "output": "3"},
            {"input": "bbbbb", "output": "1"},
        ],
        "explanation": "Sliding window with last-seen index map; shrink left on duplicate.",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": trio_from_py_comment(
            "Variable window + last seen index",
            """    s = sys.stdin.read().strip()
    # Print length of longest substring without repeats
    pass""",
        ),
        "reference_solutions": _ref(
            "import sys\n"
            "s = sys.stdin.read().strip()\n"
            "last = {}\n"
            "left = best = 0\n"
            "for i, c in enumerate(s):\n"
            "    if c in last and last[c] >= left:\n"
            "        left = last[c] + 1\n"
            "    last[c] = i\n"
            "    best = max(best, i - left + 1)\n"
            "print(best)\n"
        ),
        "candidate_test_cases": [
            _tc("abcabcbb", "3"),
            _tc("bbbbb", "1", category="duplicates"),
            _tc("a", "1", category="single"),
            _tc("abcdef", "6", category="maximum", is_hidden=True),
            _tc("pwwkew", "3"),
            _tc("abba", "2", category="boundary", is_hidden=True),
            _tc("dvdf", "3", category="adversarial", is_hidden=True),
            _tc("tmmzuxt", "5", is_hidden=True),
        ],
    },
    # --- Binary Search (easy) ---
    {
        "title": "Search Insert Position",
        "slug": "search-insert-position",
        "difficulty": "easy",
        "topics": ["arrays", "binary search"],
        "patterns": ["lower bound"],
        "problem_statement": (
            "Given a sorted array of distinct integers and target X, return the 1-based index "
            "where X would be inserted to keep order. If X exists, return its current position."
        ),
        "input_format": "Line 1: n X\nLine 2: n sorted integers",
        "output_format": "1-based insertion index.",
        "constraints": "1 <= n <= 1e5\n-1e9 <= values, X <= 1e9",
        "examples": [
            {"input": "4 5\n1 3 5 6", "output": "3"},
            {"input": "4 2\n1 3 5 6", "output": "2"},
        ],
        "explanation": "Binary search for first index with value >= X (lower bound).",
        "expected_time_complexity": "O(log n)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": trio_from_py_comment(
            "Binary search lower bound (1-based index)",
            """    data = list(map(int, sys.stdin.read().split()))
    n, X = data[0], data[1]
    arr = data[2:2 + n]
    # Print 1-based insert position
    pass""",
        ),
        "reference_solutions": _ref(
            "import sys\n"
            "import bisect\n"
            "data = list(map(int, sys.stdin.read().split()))\n"
            "n, X = data[0], data[1]\n"
            "a = data[2:2+n]\n"
            "print(bisect.bisect_left(a, X) + 1)\n"
        ),
        "candidate_test_cases": [
            _tc("4 5\n1 3 5 6", "3"),
            _tc("4 2\n1 3 5 6", "2"),
            _tc("1 5\n5", "1", category="single"),
            _tc("1 4\n5", "1", category="single", is_hidden=True),
            _tc("5 0\n-5 -2 0 1 4", "3", category="negative"),
            _tc("5 7\n1 3 5 7 9", "4", is_hidden=True),
            _tc("3 10\n1 2 3", "4", category="boundary"),
        ],
    },
    # --- Stack (easy) ---
    {
        "title": "Valid Parentheses",
        "slug": "valid-parentheses-check",
        "difficulty": "easy",
        "topics": ["stack", "strings"],
        "patterns": ["stack matching"],
        "problem_statement": (
            "Given a string containing only '(', ')', '{', '}', '[' and ']', determine if "
            "the brackets are correctly nested and closed. Print YES or NO."
        ),
        "input_format": "A single line bracket string S.",
        "output_format": "YES or NO",
        "constraints": "1 <= |S| <= 1e5",
        "examples": [
            {"input": "()[]{}", "output": "YES"},
            {"input": "(]", "output": "NO"},
        ],
        "explanation": "Push opening brackets; on closing, check top of stack matches.",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(n)",
        "supported_languages": _LANGS,
        "starter_code": trio_from_py_comment(
            "Stack-based bracket matching",
            """    s = sys.stdin.read().strip()
    # Print YES if valid parentheses else NO
    pass""",
        ),
        "reference_solutions": _ref(
            "import sys\n"
            "s = sys.stdin.read().strip()\n"
            "pairs = {')': '(', ']': '[', '}': '{'}\n"
            "st = []\n"
            "ok = True\n"
            "for c in s:\n"
            "    if c in '([{':\n"
            "        st.append(c)\n"
            "    elif not st or st.pop() != pairs[c]:\n"
            "        ok = False\n"
            "        break\n"
            "if st:\n"
            "    ok = False\n"
            "print('YES' if ok else 'NO')\n"
        ),
        "candidate_test_cases": [
            _tc("()[]{}", "YES"),
            _tc("(]", "NO"),
            _tc("(", "NO", category="single"),
            _tc("()", "YES", category="minimum"),
            _tc("{[]}", "YES", is_hidden=True),
            _tc("([)]", "NO", category="adversarial"),
            _tc("]]", "NO", category="boundary", is_hidden=True),
            _tc("((()))", "YES", is_hidden=True),
        ],
    },
    # --- Queue (easy) ---
    {
        "title": "First Negative in Every Window of Size K",
        "slug": "first-negative-window-k",
        "difficulty": "easy",
        "topics": ["queue", "arrays", "sliding window"],
        "patterns": ["deque window"],
        "problem_statement": (
            "Given an array and window size k, for each window print the first negative number, "
            "or 0 if none exists. Windows are processed left to right; output values space-separated."
        ),
        "input_format": "Line 1: n k\nLine 2: n integers",
        "output_format": "Space-separated first negatives per window (or 0).",
        "constraints": "1 <= k <= n <= 1e5\n-1e9 <= a[i] <= 1e9",
        "examples": [
            {"input": "5 3\n-8 -2 3 4 5", "output": "-8 -2 0"},
            {"input": "4 2\n1 2 3 4", "output": "0 0 0"},
        ],
        "explanation": "Use a deque storing indices of negative numbers within current window.",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(k)",
        "supported_languages": _LANGS,
        "starter_code": trio_from_py_comment(
            "Sliding window with deque of negative indices",
            """    data = list(map(int, sys.stdin.read().split()))
    n, k = data[0], data[1]
    arr = data[2:2 + n]
    # Print first negative in each k-window (0 if none)
    pass""",
        ),
        "reference_solutions": _ref(
            "import sys\n"
            "from collections import deque\n"
            "data = list(map(int, sys.stdin.read().split()))\n"
            "n, k = data[0], data[1]\n"
            "a = data[2:2+n]\n"
            "dq = deque()\n"
            "out = []\n"
            "for i in range(n):\n"
            "    if dq and dq[0] <= i - k:\n"
            "        dq.popleft()\n"
            "    if a[i] < 0:\n"
            "        dq.append(i)\n"
            "    if i >= k - 1:\n"
            "        out.append(str(a[dq[0]] if dq else 0))\n"
            "print(' '.join(out))\n"
        ),
        "candidate_test_cases": [
            _tc("5 3\n-8 -2 3 4 5", "-8 -2 0"),
            _tc("4 2\n1 2 3 4", "0 0 0"),
            _tc("3 3\n-1 -2 -3", "-1", category="minimum"),
            _tc("1 1\n-5", "-5", category="single"),
            _tc("6 2\n-1 5 -3 2 -2 8", "-1 -3 -3 -2 -2", is_hidden=True),
            _tc("5 2\n0 0 0 0 0", "0 0 0 0", category="empty"),
            _tc("4 4\n-4 1 2 3", "-4", category="boundary"),
            _tc("7 3\n1 -1 2 -2 3 -3 4", "-1 -1 -2 -2 -3", is_hidden=True),
        ],
    },
    # --- Linked List (easy) — array representation ---
    {
        "title": "Middle Element of Array (Linked List Warm-up)",
        "slug": "middle-element-array",
        "difficulty": "easy",
        "topics": ["linked list", "arrays", "two pointers"],
        "patterns": ["slow fast pointers"],
        "problem_statement": (
            "Given n node values stored in order, return the middle value using the "
            "slow/fast pointer idea (same as finding middle of a linked list). "
            "For even n, print the right-middle element (1-based position)."
        ),
        "input_format": "Line 1: n\nLine 2: n integers",
        "output_format": "A single integer — middle value.",
        "constraints": "1 <= n <= 1e5",
        "examples": [
            {"input": "5\n1 2 3 4 5", "output": "3"},
            {"input": "4\n10 20 30 40", "output": "30"},
        ],
        "explanation": "Slow moves 1 step, fast moves 2; when fast reaches end, slow is at middle.",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": trio_from_py_comment(
            "Slow/fast pointer middle element",
            """    data = list(map(int, sys.stdin.read().split()))
    n = data[0]
    arr = data[1:1 + n]
    # Print middle element (right-middle if even length)
    pass""",
        ),
        "reference_solutions": _ref(
            "import sys\n"
            "data = list(map(int, sys.stdin.read().split()))\n"
            "n = data[0]\n"
            "a = data[1:1+n]\n"
            "slow = 0\n"
            "fast = 0\n"
            "while fast + 1 < n:\n"
            "    slow += 1\n"
            "    fast += 2\n"
            "print(a[slow])\n"
        ),
        "candidate_test_cases": [
            _tc("5\n1 2 3 4 5", "3"),
            _tc("4\n10 20 30 40", "30"),
            _tc("1\n7", "7", category="single"),
            _tc("2\n5 9", "9", category="minimum"),
            _tc("6\n1 1 1 2 2 2", "2", category="duplicates", is_hidden=True),
            _tc("3\n-1 0 1", "0", category="negative"),
            _tc("7\n9 8 7 6 5 4 3", "6", is_hidden=True),
            _tc("8\n1 2 3 4 5 6 7 8", "5", category="boundary"),
        ],
    },
    # --- Trees (easy) ---
    {
        "title": "Sum of Nodes at Maximum Depth",
        "slug": "sum-nodes-max-depth",
        "difficulty": "easy",
        "topics": ["trees", "graphs"],
        "patterns": ["bfs level"],
        "problem_statement": (
            "A binary tree is given in level-order as integers; -1 means null/missing node. "
            "Find the sum of all non-null nodes at the maximum depth (deepest level)."
        ),
        "input_format": (
            "Line 1: n (number of values in level order)\n"
            "Line 2: n integers (-1 for null)"
        ),
        "output_format": "Sum of deepest-level nodes.",
        "constraints": "1 <= n <= 1e4\nValues are -1 or integers in [-1e9, 1e9].",
        "examples": [
            {"input": "7\n1 2 3 4 5 -1 -1", "output": "9"},
            {"input": "3\n5 -1 7", "output": "7"},
        ],
        "explanation": "BFS level by level; track sum of last processed level.",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(n)",
        "supported_languages": _LANGS,
        "starter_code": trio_from_py_comment(
            "BFS level-order; sum last level",
            """    data = list(map(int, sys.stdin.read().split()))
    n = data[0]
    vals = data[1:1 + n]
    # Sum non-null nodes at maximum depth
    pass""",
        ),
        "reference_solutions": _ref(
            "import sys\n"
            "from collections import deque\n"
            "data = list(map(int, sys.stdin.read().split()))\n"
            "n = data[0]\n"
            "vals = data[1:1+n]\n"
            "if n == 0 or vals[0] == -1:\n"
            "    print(0)\n"
            "    raise SystemExit\n"
            "q = deque([0])\n"
            "level_sum = 0\n"
            "while q:\n"
            "    level_sum = 0\n"
            "    for _ in range(len(q)):\n"
            "        idx = q.popleft()\n"
            "        if idx >= n or vals[idx] == -1:\n"
            "            continue\n"
            "        level_sum += vals[idx]\n"
            "        left, right = 2 * idx + 1, 2 * idx + 2\n"
            "        if left < n and vals[left] != -1:\n"
            "            q.append(left)\n"
            "        if right < n and vals[right] != -1:\n"
            "            q.append(right)\n"
            "print(level_sum)\n"
        ),
        "candidate_test_cases": [
            _tc("7\n1 2 3 4 5 -1 -1", "9"),
            _tc("3\n5 -1 7", "7"),
            _tc("1\n10", "10", category="single"),
            _tc("3\n1 2 3", "5", category="minimum", is_hidden=True),
            _tc("5\n1 -1 2 -1 3", "2", category="boundary"),
            _tc("7\n1 2 3 -1 -1 4 5", "9", is_hidden=True),
            _tc("4\n1 2 -1 -1", "2", category="empty"),
            _tc("15\n1 2 3 4 5 6 7 -1 -1 -1 -1 -1 -1 -1 -1", "22", category="maximum", is_hidden=True),
        ],
    },
    # --- Graphs (easy) ---
    {
        "title": "Count Islands in Grid",
        "slug": "count-islands-grid",
        "difficulty": "easy",
        "topics": ["graphs"],
        "patterns": ["dfs flood fill"],
        "problem_statement": (
            "Given an r x c grid of 0 (water) and 1 (land), count the number of islands "
            "(connected groups of 1s moving up/down/left/right). Classic GfG graph/grid DFS."
        ),
        "input_format": (
            "Line 1: r c\n"
            "Next r lines: c space-separated 0/1 values"
        ),
        "output_format": "Number of islands.",
        "constraints": "1 <= r, c <= 500",
        "examples": [
            {"input": "4 5\n1 1 0 0 0\n1 1 0 0 0\n0 0 1 0 0\n0 0 0 1 1", "output": "3"},
            {"input": "1 1\n1", "output": "1"},
        ],
        "explanation": "Scan grid; on land cell, DFS/BFS to mark entire island, increment count.",
        "expected_time_complexity": "O(r * c)",
        "expected_space_complexity": "O(r * c)",
        "supported_languages": _LANGS,
        "starter_code": trio_from_py_comment(
            "DFS/BFS flood-fill island counting",
            """    lines = sys.stdin.read().splitlines()
    r, c = map(int, lines[0].split())
    grid = [list(map(int, lines[i + 1].split())) for i in range(r)]
    # Print number of islands
    pass""",
        ),
        "reference_solutions": _ref(
            "import sys\n"
            "lines = sys.stdin.read().splitlines()\n"
            "r, c = map(int, lines[0].split())\n"
            "grid = [list(map(int, lines[i+1].split())) for i in range(r)]\n"
            "def dfs(i, j):\n"
            "    if i < 0 or j < 0 or i >= r or j >= c or grid[i][j] == 0:\n"
            "        return\n"
            "    grid[i][j] = 0\n"
            "    dfs(i+1,j); dfs(i-1,j); dfs(i,j+1); dfs(i,j-1)\n"
            "cnt = 0\n"
            "for i in range(r):\n"
            "    for j in range(c):\n"
            "        if grid[i][j] == 1:\n"
            "            cnt += 1\n"
            "            dfs(i, j)\n"
            "print(cnt)\n"
        ),
        "candidate_test_cases": [
            _tc("4 5\n1 1 0 0 0\n1 1 0 0 0\n0 0 1 0 0\n0 0 0 1 1", "3"),
            _tc("1 1\n1", "1", category="single"),
            _tc("2 2\n0 0\n0 0", "0", category="empty"),
            _tc("1 5\n1 1 1 1 1", "1", category="minimum"),
            _tc("3 3\n1 0 1\n0 1 0\n1 0 1", "5", is_hidden=True),
            _tc("2 3\n1 1 0\n0 1 1", "1", category="boundary"),
            _tc("5 1\n1\n1\n0\n1\n1", "2", is_hidden=True),
            _tc("3 4\n1 1 1 1\n1 0 0 1\n1 1 1 1", "1", category="maximum", is_hidden=True),
        ],
    },
    # --- Greedy (easy) ---
    {
        "title": "Maximum Activities (Non-overlapping)",
        "slug": "max-non-overlapping-activities",
        "difficulty": "easy",
        "topics": ["greedy"],
        "patterns": ["activity selection"],
        "problem_statement": (
            "n activities have start and end times. Pick the maximum number of activities "
            "a student can attend (no overlap). Sort by finish time — classic greedy."
        ),
        "input_format": (
            "Line 1: n\n"
            "Next n lines: start end (integers)"
        ),
        "output_format": "Maximum count of non-overlapping activities.",
        "constraints": "1 <= n <= 1e5\n0 <= start < end <= 1e9",
        "examples": [
            {"input": "4\n1 3\n2 5\n4 6\n6 8", "output": "3"},
            {"input": "1\n0 5", "output": "1"},
        ],
        "explanation": "Sort by end time; greedily pick next compatible activity.",
        "expected_time_complexity": "O(n log n)",
        "expected_space_complexity": "O(n)",
        "supported_languages": _LANGS,
        "starter_code": trio_from_py_comment(
            "Greedy activity selection by finish time",
            """    lines = sys.stdin.read().splitlines()
    n = int(lines[0])
    acts = [tuple(map(int, line.split())) for line in lines[1:1 + n]]
    # Print max non-overlapping activities
    pass""",
        ),
        "reference_solutions": _ref(
            "import sys\n"
            "lines = sys.stdin.read().splitlines()\n"
            "n = int(lines[0])\n"
            "acts = [tuple(map(int, l.split())) for l in lines[1:1+n]]\n"
            "acts.sort(key=lambda x: x[1])\n"
            "cnt = 0\n"
            "end = -1\n"
            "for s, e in acts:\n"
            "    if s >= end:\n"
            "        cnt += 1\n"
            "        end = e\n"
            "print(cnt)\n"
        ),
        "candidate_test_cases": [
            _tc("4\n1 3\n2 5\n4 6\n6 8", "3"),
            _tc("1\n0 5", "1", category="single"),
            _tc("3\n1 2\n2 3\n3 4", "3", category="minimum"),
            _tc("2\n1 10\n2 3", "1", category="boundary"),
            _tc("5\n1 4\n3 5\n0 6\n5 7\n8 9", "3", is_hidden=True),
            _tc("4\n1 2\n1 2\n1 2\n1 2", "1", category="duplicates"),
            _tc("6\n1 3\n2 4\n3 5\n4 6\n5 7\n6 8", "3", is_hidden=True),
            _tc("3\n0 1\n1 2\n2 3", "3", category="normal"),
        ],
    },
    # --- Recursion (easy) ---
    {
        "title": "Fibonacci Number",
        "slug": "fibonacci-number",
        "difficulty": "easy",
        "topics": ["recursion", "math", "dynamic programming"],
        "patterns": ["recurrence"],
        "problem_statement": (
            "Given n, compute the n-th Fibonacci number F(n) where F(0)=0, F(1)=1, "
            "and F(k)=F(k-1)+F(k-2). Use recursion or iteration — standard GfG warm-up."
        ),
        "input_format": "A single integer n.",
        "output_format": "F(n) as integer.",
        "constraints": "0 <= n <= 45",
        "examples": [
            {"input": "5", "output": "5"},
            {"input": "0", "output": "0"},
        ],
        "explanation": "Iterative DP is O(n); naive recursion works for small n.",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": trio_from_py_comment(
            "Iterative or recursive Fibonacci",
            """    n = int(sys.stdin.read().strip())
    # Print F(n)
    pass""",
        ),
        "reference_solutions": _ref(
            "import sys\n"
            "n = int(sys.stdin.read().strip())\n"
            "if n <= 1:\n"
            "    print(n)\n"
            "else:\n"
            "    a, b = 0, 1\n"
            "    for _ in range(2, n + 1):\n"
            "        a, b = b, a + b\n"
            "    print(b)\n"
        ),
        "candidate_test_cases": [
            _tc("5", "5"),
            _tc("0", "0", category="boundary"),
            _tc("1", "1", category="single"),
            _tc("10", "55", category="normal", is_hidden=True),
            _tc("2", "1", category="minimum"),
            _tc("20", "6765", is_hidden=True),
            _tc("45", "1134903170", category="maximum", is_hidden=True),
            _tc("7", "13", category="boundary"),
        ],
    },
    # --- Backtracking (easy) ---
    {
        "title": "Print All Subsets (Power Set)",
        "slug": "print-all-subsets",
        "difficulty": "easy",
        "topics": ["backtracking", "recursion"],
        "patterns": ["subset generation"],
        "problem_statement": (
            "Given n distinct integers, print the count of all subsets (including empty set). "
            "This is 2^n — classic backtracking / bit-mask introduction."
        ),
        "input_format": "Line 1: n\nLine 2: n integers",
        "output_format": "Single integer — number of subsets.",
        "constraints": "0 <= n <= 20",
        "examples": [
            {"input": "3\n1 2 3", "output": "8"},
            {"input": "0", "output": "1"},
        ],
        "explanation": "Each element is either included or not — 2^n subsets.",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": trio_from_py_comment(
            "Count subsets as 2^n",
            """    data = list(map(int, sys.stdin.read().split()))
    n = data[0]
    # Print total subset count (2^n)
    pass""",
        ),
        "reference_solutions": _ref(
            "import sys\n"
            "data = list(map(int, sys.stdin.read().split()))\n"
            "n = data[0]\n"
            "print(1 << n)\n"
        ),
        "candidate_test_cases": [
            _tc("3\n1 2 3", "8"),
            _tc("0", "1", category="empty"),
            _tc("1\n5", "2", category="single"),
            _tc("2\n1 2", "4", category="minimum"),
            _tc("4\n1 2 3 4", "16", is_hidden=True),
            _tc("5\n10 20 30 40 50", "32", category="boundary"),
            _tc("10\n1 2 3 4 5 6 7 8 9 10", "1024", is_hidden=True),
            _tc("20\n" + " ".join(str(i) for i in range(20)), "1048576", category="maximum", is_hidden=True),
        ],
    },
    # --- Dynamic Programming (easy) ---
    {
        "title": "Climbing Stairs",
        "slug": "climbing-stairs-count",
        "difficulty": "easy",
        "topics": ["dynamic programming", "recursion"],
        "patterns": ["1d dp"],
        "problem_statement": (
            "You can climb 1 or 2 steps at a time. Given n steps, in how many distinct ways "
            "can you reach the top? Classic DP intro (same as Fibonacci shifted)."
        ),
        "input_format": "A single integer n.",
        "output_format": "Number of ways.",
        "constraints": "1 <= n <= 45",
        "examples": [
            {"input": "3", "output": "3"},
            {"input": "2", "output": "2"},
        ],
        "explanation": "ways(n) = ways(n-1) + ways(n-2) with base ways(1)=1, ways(2)=2.",
        "expected_time_complexity": "O(n)",
        "expected_space_complexity": "O(1)",
        "supported_languages": _LANGS,
        "starter_code": trio_from_py_comment(
            "1D DP — ways to climb stairs",
            """    n = int(sys.stdin.read().strip())
    # Print number of distinct ways
    pass""",
        ),
        "reference_solutions": _ref(
            "import sys\n"
            "n = int(sys.stdin.read().strip())\n"
            "if n <= 2:\n"
            "    print(n)\n"
            "else:\n"
            "    a, b = 1, 2\n"
            "    for _ in range(3, n + 1):\n"
            "        a, b = b, a + b\n"
            "    print(b)\n"
        ),
        "candidate_test_cases": [
            _tc("3", "3"),
            _tc("2", "2", category="minimum"),
            _tc("1", "1", category="single"),
            _tc("5", "8", category="normal", is_hidden=True),
            _tc("10", "89", is_hidden=True),
            _tc("45", "1836311903", category="maximum", is_hidden=True),
            _tc("4", "5", category="boundary"),
            _tc("6", "13", is_hidden=True),
        ],
    },
    # --- Dynamic Programming (medium) ---
    {
        "title": "Coin Change — Minimum Coins",
        "slug": "coin-change-minimum",
        "difficulty": "medium",
        "topics": ["dynamic programming"],
        "patterns": ["unbounded knapsack"],
        "problem_statement": (
            "Given coin denominations and amount A, find the minimum number of coins needed "
            "to make amount A. Print -1 if impossible. Medium classic DP for campus interviews."
        ),
        "input_format": (
            "Line 1: n A\n"
            "Line 2: n coin values"
        ),
        "output_format": "Minimum coin count or -1.",
        "constraints": "1 <= n <= 20\n1 <= coin[i], A <= 1e4",
        "examples": [
            {"input": "3 11\n1 2 5", "output": "3"},
            {"input": "1 3\n2", "output": "-1"},
        ],
        "explanation": "DP[i] = min coins for amount i; try each coin if dp[i-coin]+1 is better.",
        "expected_time_complexity": "O(n * A)",
        "expected_space_complexity": "O(A)",
        "supported_languages": _LANGS,
        "starter_code": trio_from_py_comment(
            "Unbounded knapsack DP for minimum coins",
            """    data = list(map(int, sys.stdin.read().split()))
    n, A = data[0], data[1]
    coins = data[2:2 + n]
    # Print min coins for amount A or -1
    pass""",
        ),
        "reference_solutions": _ref(
            "import sys\n"
            "data = list(map(int, sys.stdin.read().split()))\n"
            "n, A = data[0], data[1]\n"
            "coins = data[2:2+n]\n"
            "INF = 10**9\n"
            "dp = [INF] * (A + 1)\n"
            "dp[0] = 0\n"
            "for i in range(1, A + 1):\n"
            "    for c in coins:\n"
            "        if c <= i and dp[i - c] + 1 < dp[i]:\n"
            "            dp[i] = dp[i - c] + 1\n"
            "print(dp[A] if dp[A] < INF else -1)\n"
        ),
        "candidate_test_cases": [
            _tc("3 11\n1 2 5", "3"),
            _tc("1 3\n2", "-1"),
            _tc("1 0\n5", "0", category="boundary"),
            _tc("2 4\n1 2", "2", category="minimum"),
            _tc("3 7\n2 3 5", "2", is_hidden=True),
            _tc("4 20\n1 5 10 25", "2", category="normal"),
            _tc("2 3\n3 5", "1", category="single", is_hidden=True),
            _tc("5 100\n1 2 5 10 20", "5", category="maximum", is_hidden=True),
        ],
    },
]
