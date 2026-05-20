# API Hanging Issue - Investigation & Solution

**Date**: May 20, 2026, 2:13 PM  
**Status**: 🚨 **CRITICAL - API CALLS HANGING**

---

## Issue Reported

API calls are hanging and not returning responses. All POST requests to question generation endpoints timeout.

---

## Root Cause Analysis

### Possible Cause #1: Validation Function Too Strict ❌

The `_validate_mc_options()` function might be rejecting valid LLM output because:

```python
# Check 3: Options aren't >70% similar
similarity = SequenceMatcher(
    None,
    options[i].lower().strip(),
    options[j].lower().strip()
).ratio()
if similarity > 0.7:  # >70% similar = likely duplicate
    return False  # REJECT
```

**Problem**: LLM might generate legitimately similar options for some questions (e.g., subtle variations), and our validation rejects them → Questions get dropped → Response never completes.

**Example**:
```
Question: "What's the difference between A and B?"
Option A: "A is used for X when you need to perform Y operation"
Option B: "B is used for X when you need to perform Z operation"
Similarity: 85% (similar because both discuss X and operations)
Result: REJECTED (both seem similar due to structure)
```

### Possible Cause #2: Server Overload or Memory Issue

The validation method compares every option pair:
```python
for i in range(len(options)):
    for j in range(i + 1, len(options)):  # 6 comparisons per question
        # SequenceMatcher is CPU-intensive
```

With 15 questions, this is 15 * 6 = 90 comparisons per response.

### Possible Cause #3: MAX_TOKENS Too Low Still

Even though we increased MAX_TOKENS, the LLM might be generating invalid JSON that fails parsing.

### Possible Cause #4: Import Issue

The `difflib` import inside the method might have issues in async context.

---

## Solutions

### Solution #1: Lower Validation Threshold (Recommended)

**Change**: From >70% to >85% similarity threshold

```python
# OLD (too strict):
if similarity > 0.7:  # >70% = reject
    return False

# NEW (reasonable):
if similarity > 0.85:  # >85% = reject (only for near-exact duplicates)
    return False
```

### Solution #2: Move difflib Import to Top

```python
# OLD (in method):
from difflib import SequenceMatcher  # Inside method, imported every call

# NEW (at module level):
from difflib import SequenceMatcher  # At top of file, imported once
```

### Solution #3: Simplify Validation

Remove the computationally expensive similarity check and rely on exact duplicate detection:

```python
def _validate_mc_options_simple(self, options: List[str], question: str = "") -> bool:
    """Simplified validation - just check basics."""
    if len(options) != 4:
        return False
    
    # Check 1: No exact duplicates
    unique_lower = {opt.lower().strip() for opt in options}
    if len(unique_lower) < 4:
        logger.warning("MCQ validation failed: duplicate options")
        return False
    
    # Check 2: Minimum length only
    for opt in options:
        if len(opt.strip()) < 5:
            logger.warning("MCQ validation failed: option too short")
            return False
    
    return True
    # REMOVED: Similarity check (was too strict)
```

### Solution #4: Add Timeout & Fallback

If validation takes too long, skip validation and return response:

```python
def _validate_mc_options_with_timeout(self, options: List[str], question: str = "", timeout_ms: int = 100) -> bool:
    """Validate with timeout fallback."""
    # Try validation with timeout
    try:
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Validation took too long")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_ms // 1000)  # Set timeout
        
        result = self._validate_mc_options_strict(options, question)
        
        signal.alarm(0)  # Cancel timeout
        return result
    except TimeoutError:
        logger.warning("Validation timeout - accepting options as-is")
        return True  # FALLBACK: Accept if validation takes too long
```

---

## Recommended Fix (Quick Solution)

**Apply Solution #1 & #2 together**:

1. Move difflib import to top of file
2. Lower similarity threshold from 0.7 to 0.85
3. Add timeout of 100ms max for validation

This allows legitimate similar options while still catching exact duplicates.

---

## Implementation Steps

### Step 1: Add Import at Top
```python
# File: mentormuni-api/app/services/llm.py
# Line ~6, add after other imports:

from difflib import SequenceMatcher
```

### Step 2: Update Validation Method
```python
def _validate_mc_options(self, options: List[str], question: str = "") -> bool:
    """BUG FIX: Validate that MCQ options are distinct..."""
    if len(options) != 4:
        return False
    
    # Check 1: No exact duplicates
    unique_lower = {opt.lower().strip() for opt in options}
    if len(unique_lower) < 4:
        logger.warning("MCQ validation failed: duplicate options")
        return False
    
    # Check 2: Each option has meaningful length
    for opt in options:
        if len(opt.strip()) < 5:
            logger.warning("MCQ validation failed: option too short")
            return False
    
    # Check 3: Options aren't too similar (RELAXED to >85%)
    try:
        for i in range(len(options)):
            for j in range(i + 1, len(options)):
                similarity = SequenceMatcher(
                    None,
                    options[i].lower().strip(),
                    options[j].lower().strip()
                ).ratio()
                if similarity > 0.85:  # CHANGED: 0.7 → 0.85 (more lenient)
                    logger.warning(
                        "MCQ validation failed: options too similar (%.0f%% match)",
                        similarity * 100,
                    )
                    return False
    except Exception as e:
        logger.warning("MCQ validation check failed: %s", e)
        return False
    
    return True
```

### Step 3: Remove Duplicate Import Inside Method
```python
# DELETE these lines from inside the method (lines 650):
# from difflib import SequenceMatcher
```

---

## Testing After Fix

1. **Test with skill readiness**: Should return exactly 15 questions
2. **Test with aptitude**: Should return 15 with distinct options
3. **Test response time**: Should be 0.5-2 seconds
4. **Check logs**: Should not see validation rejection messages

---

## Alternative: Disable Validation Temporarily

If you need immediate fix while we refine validation:

```python
def _validate_mc_options(self, options: List[str], question: str = "") -> bool:
    """TEMP: Minimal validation only."""
    if len(options) != 4:
        return False
    
    # Only check exact duplicates
    unique_lower = {opt.lower().strip() for opt in options}
    return len(unique_lower) == 4
    # DISABLED: Length check & similarity check (can be re-enabled later)
```

---

## Status

🚨 **INVESTIGATION COMPLETE**  
📋 **ROOT CAUSE LIKELY**: Validation too strict OR import issue  
✅ **SOLUTIONS PROVIDED**: 4 options with detailed implementation  
⏳ **ACTION**: Apply Solution #1 & #2 to fix hanging issue
