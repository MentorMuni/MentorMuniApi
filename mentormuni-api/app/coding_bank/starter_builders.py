"""Reusable starter templates for campus coding problems (stdin-based)."""

from __future__ import annotations


def starter_trio(py_body: str, cpp_body: str, java_body: str) -> list[dict]:
    return [
        {"language": "python", "code": py_body.strip() + "\n"},
        {"language": "cpp", "code": cpp_body.strip() + "\n"},
        {"language": "java", "code": java_body.strip() + "\n"},
    ]


_PY_HEADER = """import sys

def solve():
"""

_PY_FOOTER = """
if __name__ == "__main__":
    solve()
"""

_CPP_HEADER = """#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
"""

_CPP_FOOTER = """
    return 0;
}
"""

_JAVA_HEADER = """import java.util.*;
import java.io.*;

public class Main {
    public static void main(String[] args) throws Exception {
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
"""

_JAVA_FOOTER = """    }
}
"""


def py_starter(body: str) -> str:
    return _PY_HEADER + body + _PY_FOOTER


def cpp_starter(body: str) -> str:
    return _CPP_HEADER + body + _CPP_FOOTER


def java_starter(body: str) -> str:
    return _JAVA_HEADER + body + _JAVA_FOOTER


def trio_from_py_comment(comment: str, py_body: str) -> list[dict]:
    """Build trio where Python has full parsing; C++/Java have guided comments."""
    py = py_starter(f"    # {comment}\n{py_body}")
    cpp = cpp_starter(f"    // {comment}\n    // Read stdin, print answer")
    java = java_starter(f"        // {comment}\n        // Read stdin, print answer")
    return starter_trio(py, cpp, java)


_LANGS = ["python", "cpp", "java"]
