"""Unit tests for topic normalize + practice helpers (no DB / OpenAI)."""

from app.coding.practice import normalize_difficulty, normalize_topic_label


def test_normalize_topic_aliases():
    assert normalize_topic_label("dp") == "Dynamic Programming"
    assert normalize_topic_label("HASHING") == "Hashing"
    assert normalize_topic_label("sliding window") == "Sliding Window"


def test_normalize_free_text_topic():
    assert "Interval" in normalize_topic_label("interval scheduling")


def test_normalize_difficulty():
    assert normalize_difficulty("Beginner") == "easy"
    assert normalize_difficulty("intermediate") == "medium"
    assert normalize_difficulty("expert") == "hard"
