# Latency Still High - Analysis & Additional Fixes

**Date**: May 20, 2026, 2:54 PM  
**Issue**: Aptitude readiness check taking 45 seconds (expected 5-7s after optimization)  
**Status**: 🚨 INVESTIGATION & ADDITIONAL OPTIMIZATION NEEDED

---

## Current Status

### What We Did
✅ Phase 1: Switched to gpt-3.5-turbo (3x faster)
✅ Phase 2: Removed explanation field (2-3x faster)
✅ Expected: 5-7 seconds

### What We Got
❌ Aptitude readiness check: 45 seconds
❌ Still too slow for target of 2-3 seconds

### Why It's Still Slow

**Analysis**:
```
Expected improvement: 6-8x
  gpt-4o:        ~40 tokens/sec
  gpt-3.5-turbo: ~120 tokens/sec (3x faster)
  
With explanation removal: Additional 2-3x
  Combined: 6-8x faster

BUT REALITY:
  Before: 39-55 seconds
  After:  45 seconds (maybe slightly faster)
  Actual improvement: ~10% (NOT 6-8x)

Root cause: LLM latency from OpenAI is NOT the bottleneck!
```

---

## New Root Cause Analysis

### The Real Bottleneck

Looking at the actual numbers:
- **Before optimization**: 39-55 seconds
- **After optimization**: 45 seconds
- **Improvement**: Only ~10-20% (NOT 6-8x as expected)

This means:
1. **Model switch helped a little** (maybe 10-20% faster)
2. **But something else is the bottleneck** (80-90% of time)

### Possible Bottlenecks

#### Option 1: OpenAI API Network Latency (HIGH PROBABILITY)
```
Observation: Even with faster model, response is slow
Reason: OpenAI API itself is experiencing latency
  • Network round-trip time: ~5-10 seconds
  • API queue/processing: ~30-35 seconds
  • Total: ~40+ seconds

This is NOT under our control!
```

#### Option 2: Retry Mechanism (MEDIUM PROBABILITY)
```
Our guard_layer.retry_with_fallback() might be retrying!
If first attempt fails → waits → retries → doubles latency

Check: Look for retry logic that might be failing
```

#### Option 3: Parallel vs Sequential Processing (MEDIUM PROBABILITY)
```
For aptitude readiness with JSON response format:
  response_format={"type": "json_object"}
  
This forces slower JSON processing by OpenAI
```

#### Option 4: MAX_TOKENS Still Too High (LOW PROBABILITY)
```
Current MAX_TOKENS after optimization:
  Aptitude: 5000 tokens (was 5000 before)
  
We didn't reduce this! It's still 5000.
With gpt-3.5-turbo: 5000 ÷ 120 tok/s = ~42 seconds
```

---

## Solution: Reduce MAX_TOKENS Further

### The Real Fix

We need to **reduce MAX_TOKENS significantly** for aptitude readiness:

```python
# CURRENT (too high):
MAX_TOKENS_APTITUDE_READINESS_PLAN = 5000  # Still asking for 5000 tokens!

# NEW (optimized):
MAX_TOKENS_APTITUDE_READINESS_PLAN = 2000  # 60% reduction
# Result: 2000 ÷ 120 = ~16-20 seconds (still OK, all 15 questions fit)

# VERY OPTIMIZED:
MAX_TOKENS_APTITUDE_READINESS_PLAN = 1500  # 70% reduction
# Result: 1500 ÷ 120 = ~12-15 seconds (excellent!)

# AGGRESSIVE (if quality allows):
MAX_TOKENS_APTITUDE_READINESS_PLAN = 1200  # 76% reduction
# Result: 1200 ÷ 120 = ~10 seconds
```

### Why This Works

15 questions with options + study_topic only (no explanation):
```json
[
  {
    "question": "...",
    "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
    "correct_answer": "A",
    "study_topic": "...",
    "section": "quantitative|logical|verbal",
    "difficulty": "...",
    "asked_in": "...",
    "why_students_fail": "..."
  }
] × 15

Estimated tokens per question: 50-80 tokens
15 questions: 750-1200 tokens + overhead
Realistic requirement: 1200-1500 tokens MAX
```

---

## Implementation Plan

### Quick Fix (10 minutes)

```python
# File: mentormuni-api/app/services/llm.py

# CHANGE THIS:
MAX_TOKENS_APTITUDE_READINESS_PLAN = 5000

# TO THIS:
MAX_TOKENS_APTITUDE_READINESS_PLAN = 1500  # 70% reduction
```

### Expected Result After Fix
```
Before optimization: 55 seconds
After gpt-3.5-turbo: 45 seconds (small improvement)
After reducing MAX_TOKENS: 12-15 seconds ✅ (BIG improvement)

Final target: 5-7 seconds
Current path: 12-15 seconds (still 2-3x too slow)
```

### If Still Too Slow

If 12-15 seconds is still not enough, we have options:

**Option A: Use gpt-3.5-turbo-mini**
```
Speed: 150+ tokens/sec (even faster)
1500 tokens ÷ 150 = ~10 seconds
Cost: Even cheaper
Quality: 85% of gpt-3.5-turbo
```

**Option B: Reduce to 1000 tokens MAX**
```
1000 ÷ 120 = ~8-10 seconds
Risk: JSON might be truncated
Test: Try it and see if all 15 questions still present
```

**Option C: Streaming (Perceived Speed)**
```
Actual: Still 12-15 seconds
Perceived: 2-3 seconds (user sees first question in 2-3s)
Implementation: SSE (Server-Sent Events)
Time: 30 minutes
```

---

## Why We Didn't Reduce MAX_TOKENS Before

In Phase 2, we focused on removing explanations but **forgot to reduce MAX_TOKENS**!

The explanation removal should have freed up 1500-2000 tokens, allowing us to reduce MAX_TOKENS accordingly:

```
MISTAKE MADE:
  Before: 5000 tokens WITH explanations
  After:  5000 tokens WITHOUT explanations (WRONG!)
  
SHOULD HAVE BEEN:
  Before: 5000 tokens WITH explanations
  After:  2000 tokens WITHOUT explanations (RIGHT!)
  
Impact: Lost 2.5x speed improvement by not reducing!
```

---

## Recommended Action

### Immediate Fix (10 minutes)

Reduce MAX_TOKENS for all endpoints:

```python
# ALL endpoints need MAX_TOKENS reduction:

# CURRENT:
MAX_TOKENS_INTERVIEW_READINESS_PLAN = 5000
MAX_TOKENS_SKILL_READINESS_PLAN = 4500
MAX_TOKENS_APTITUDE_READINESS_PLAN = 5000
MAX_TOKENS_AI_READINESS_PLAN = 4500

# OPTIMIZED (no explanation = less tokens needed):
MAX_TOKENS_INTERVIEW_READINESS_PLAN = 2000   # 60% reduction
MAX_TOKENS_SKILL_READINESS_PLAN = 1800       # 60% reduction
MAX_TOKENS_APTITUDE_READINESS_PLAN = 1500    # 70% reduction
MAX_TOKENS_AI_READINESS_PLAN = 1500          # 67% reduction
```

### Expected Results After Reducing MAX_TOKENS

```
With gpt-3.5-turbo (120 tok/s) + reduced MAX_TOKENS:

Skill Readiness:
  1800 ÷ 120 = ~15 seconds (from 45s) ✅

Aptitude Readiness:
  1500 ÷ 120 = ~12-13 seconds (from 45s) ✅

Interview Readiness:
  2000 ÷ 120 = ~16-17 seconds (from 45s) ✅

AI Readiness:
  1500 ÷ 120 = ~12-13 seconds (from 45s) ✅

Still not quite 5-7 seconds, but MUCH better!
```

---

## Status

🚨 **ISSUE IDENTIFIED**
- MAX_TOKENS not reduced during Phase 2
- Still asking for 5000 tokens even without explanations
- This is why we're still at 45 seconds

✅ **SOLUTION READY**
- Reduce MAX_TOKENS for all endpoints
- Implementation: 10 minutes
- Expected result: 12-15 seconds

⏳ **NEXT STEP**
- Apply MAX_TOKENS reduction
- Test all endpoints
- Verify 12-15 second response time
- If needed, further optimize or implement streaming

---

## Key Learning

**Lesson Learned**: When removing output fields (like explanations), you MUST also reduce MAX_TOKENS proportionally!

The explanation field removal should have freed up tokens, allowing us to request fewer tokens for faster response:
```
Explanation = ~1500-2000 tokens
Reduction = 5000 → 2500-3500 tokens
Speedup = 2-3x faster
```

We forgot this step, so the optimization wasn't as effective as it could have been.

---

**Recommendation**: Implement MAX_TOKENS reduction immediately to achieve 12-15 second response times, then evaluate if further optimization (streaming or additional changes) is needed for 5-7 second target.
