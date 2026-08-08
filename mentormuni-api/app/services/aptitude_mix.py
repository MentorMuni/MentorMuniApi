"""Section mix + difficulty allocation for aptitude readiness plans."""

from __future__ import annotations

from collections import OrderedDict

# question_count: any multiple of 5 from MIN..MAX (inclusive).
MIN_QUESTION_COUNT = 5
MAX_QUESTION_COUNT = 50
QUESTION_COUNT_STEP = 5
ALLOWED_LEVELS: tuple[str, ...] = ("intermediate", "expert")

SECTION_LABELS = {
    "quantitative": "Quantitative Aptitude",
    "logical": "Logical Reasoning",
    "verbal": "Verbal Ability",
    "non_verbal": "Non-Verbal / Abstract Reasoning",
}


def allowed_question_counts(
    min_n: int = MIN_QUESTION_COUNT,
    max_n: int = MAX_QUESTION_COUNT,
    step: int = QUESTION_COUNT_STEP,
) -> tuple[int, ...]:
    return tuple(range(min_n, max_n + 1, step))


# Back-compat alias for callers / docs
ALLOWED_QUESTION_COUNTS: tuple[int, ...] = allowed_question_counts()


def normalize_level(raw: str | None) -> str:
    key = str(raw or "intermediate").strip().lower().replace("-", "_").replace(" ", "_")
    if key in ("hard", "advanced", "expert_level"):
        return "expert"
    if key in ("medium", "moderate", "intermediate_level", "easy"):
        return "intermediate"
    if key in ALLOWED_LEVELS:
        return key
    return "intermediate"


def normalize_question_count(raw: int | None) -> int:
    """
    Accept any multiple of 5 from MIN_QUESTION_COUNT..MAX_QUESTION_COUNT.
    Invalid values snap to the nearest allowed multiple (clamped to range).
    """
    try:
        n = int(raw) if raw is not None else 15
    except (TypeError, ValueError):
        n = 15

    if n < MIN_QUESTION_COUNT:
        return MIN_QUESTION_COUNT
    if n > MAX_QUESTION_COUNT:
        return MAX_QUESTION_COUNT

    # Already a valid multiple of 5
    if n % QUESTION_COUNT_STEP == 0:
        return n

    # Snap to nearest multiple of 5 within range
    lo = (n // QUESTION_COUNT_STEP) * QUESTION_COUNT_STEP
    hi = lo + QUESTION_COUNT_STEP
    lo = max(lo, MIN_QUESTION_COUNT)
    hi = min(hi, MAX_QUESTION_COUNT)
    if abs(n - lo) <= abs(n - hi):
        return lo
    return hi


def _allocate(weights: dict[str, float], n: int) -> dict[str, int]:
    """Largest-remainder allocation; every key gets ≥1 when n ≥ len(keys)."""
    keys = list(weights.keys())
    if n < len(keys):
        # Degenerate: put all into first keys
        out = {k: 0 for k in keys}
        for i in range(n):
            out[keys[i % len(keys)]] += 1
        return out

    raw = {k: n * float(weights[k]) for k in keys}
    floors = {k: int(raw[k]) for k in keys}
    for k in keys:
        if floors[k] < 1:
            floors[k] = 1
    total = sum(floors.values())
    while total > n:
        # Trim from the largest above 1
        donor = max(keys, key=lambda k: (floors[k], raw[k]))
        if floors[donor] <= 1:
            break
        floors[donor] -= 1
        total -= 1
    rem = n - sum(floors.values())
    order = sorted(keys, key=lambda k: (raw[k] - int(raw[k])), reverse=True)
    i = 0
    while rem > 0 and order:
        floors[order[i % len(order)]] += 1
        rem -= 1
        i += 1
    return floors


def compute_section_mix(
    question_count: int,
    level: str = "intermediate",
    company_type: str = "both",
) -> OrderedDict[str, int]:
    """
    Return ordered section → count mapping that always sums to question_count.
    Always includes quantitative + logical + verbal.
    Includes non_verbal when question_count >= 25.
    """
    n = normalize_question_count(question_count)
    lvl = normalize_level(level)
    ctype = str(company_type or "both").strip().lower()
    product_bias = ctype == "product_company" or lvl == "expert"
    include_nv = n >= 25

    if include_nv:
        if product_bias:
            weights = {
                "quantitative": 0.32,
                "logical": 0.36,
                "verbal": 0.22,
                "non_verbal": 0.10,
            }
        else:
            weights = {
                "quantitative": 0.30,
                "logical": 0.32,
                "verbal": 0.28,
                "non_verbal": 0.10,
            }
    else:
        if product_bias:
            weights = {"quantitative": 0.36, "logical": 0.40, "verbal": 0.24}
        else:
            # Balanced classic placement mix
            weights = {"quantitative": 1 / 3, "logical": 1 / 3, "verbal": 1 / 3}

    # Exact presets for common small / default sizes (always all core sections)
    if n == 5:
        # Smallest paper that still covers all three core sections
        mix = {"quantitative": 2, "logical": 2, "verbal": 1}
    elif n == 10 and not product_bias:
        mix = {"quantitative": 4, "logical": 3, "verbal": 3}
    elif n == 10 and product_bias:
        mix = {"quantitative": 4, "logical": 4, "verbal": 2}
    elif n == 15 and not product_bias:
        mix = {"quantitative": 5, "logical": 5, "verbal": 5}
    elif n == 15 and product_bias:
        mix = {"quantitative": 5, "logical": 6, "verbal": 4}
    else:
        mix = _allocate(weights, n)

    return OrderedDict((k, mix[k]) for k in mix if mix[k] > 0)


def section_order_from_mix(mix: dict[str, int]) -> list[str]:
    order: list[str] = []
    for section, count in mix.items():
        order.extend([section] * int(count))
    return order


def compute_difficulty_mix(question_count: int, level: str) -> dict[str, int]:
    """
    Per-question difficulty labels: easy | intermediate | expert.
    Always sums to question_count.
    """
    n = normalize_question_count(question_count)
    lvl = normalize_level(level)
    if lvl == "expert":
        # No soft easy; stretch intermediate + expert
        weights = {"easy": 0.0, "intermediate": 0.30, "expert": 0.70}
    else:
        weights = {"easy": 0.20, "intermediate": 0.60, "expert": 0.20}
    # Drop zero-weight keys for allocation stability
    active = {k: v for k, v in weights.items() if v > 0}
    mix = _allocate(active, n)
    for k in ("easy", "intermediate", "expert"):
        mix.setdefault(k, 0)
    # Fix sum
    while sum(mix.values()) > n:
        donor = max(mix, key=mix.get)
        if mix[donor] > 0:
            mix[donor] -= 1
    while sum(mix.values()) < n:
        mix["intermediate" if lvl != "expert" else "expert"] += 1
    return mix


def format_section_mix_block(mix: dict[str, int]) -> str:
    lines = []
    start = 1
    for section, count in mix.items():
        end = start + count - 1
        label = SECTION_LABELS.get(section, section)
        lines.append(f"Questions {start}–{end} ({count}): {label}  [section=\"{section}\"]")
        start = end + 1
    lines.append(f"TOTAL = {sum(mix.values())} questions.")
    return "\n".join(lines)


def format_difficulty_mix_block(diff_mix: dict[str, int], level: str) -> str:
    lvl = normalize_level(level)
    return (
        f"Assessment level parameter: {lvl}\n"
        f"Generate EXACTLY:\n"
        f"* {diff_mix.get('easy', 0)} Easy\n"
        f"* {diff_mix.get('intermediate', 0)} Intermediate\n"
        f"* {diff_mix.get('expert', 0)} Expert\n"
        "Distribute these difficulties across ALL sections (do not dump all expert Qs into one section)."
    )


def max_tokens_for_count(question_count: int) -> int:
    n = normalize_question_count(question_count)
    if n <= 10:
        return 3072
    if n <= 15:
        return 4096
    if n <= 20:
        return 6144
    if n <= 30:
        return 8192
    if n <= 40:
        return 12000
    return 14000
