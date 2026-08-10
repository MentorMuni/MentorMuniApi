# Fear to Widget Mapping System

## 🎯 Overview

Instead of generic advice, the Know Me Intervention System **intelligently maps each student fear to existing MentorMuni widgets & tools**.

Each fear gets:
- ✅ A primary widget (main tool)
- ✅ Secondary widgets (supporting tools)
- ✅ Week-by-week progression of how to use them
- ✅ Specific metrics & success criteria for each week

---

## 📚 Fear Categories & Widget Mappings

### 1️⃣ COMMUNICATION FEARS

#### Fear: "English Communication (Speaking, Confidence)"
**Primary Tool:** `AI HR Mock`
**Secondary Tools:** `Voice Interview`, `Mock Interview`

| Week | Activity | Tool | Metric | Target |
|------|----------|------|--------|--------|
| 1 | 5-min self-intro & basic Q&A | AI HR Mock | Clarity 60%+ | Comfortable speaking |
| 2 | Voice interview - project explanation | Voice Interview | Fluency score | Explain projects |
| 3 | Full mock interview | Mock Interview | Overall score | Interview ready |

**AI HR Mock Context:**
- Focus: fluency, clarity, confidence
- Difficulty: Adaptive (starts easy)
- Interview style: Conversational
- Frequency: Daily
- Duration: 10 minutes

#### Fear: "HR Interview (Soft Skills, Behavior)"
**Primary Tool:** `AI HR Mock`
**Secondary Tools:** `Mock Interview`, `Voice Interview`

| Week | Activity | Tool | Metric | Target |
|------|----------|------|--------|--------|
| 1 | Tell me about yourself (60 sec) | AI HR Mock | Structure + clarity | Perfect intro |
| 2 | Behavioral questions (STAR method) | AI HR Mock | Structure + impact | Master STAR |
| 3 | Full mock interview HR focus | Mock Interview | Overall performance | Pass HR round |

**AI HR Mock Context:**
- Interview type: HR-specific
- Topics: Self, strengths, weaknesses, situations, teamwork
- Feedback: Detailed
- Difficulty: Progressive

---

### 2️⃣ TECHNICAL FEARS

#### Fear: "DSA Not Strong (Data Structures & Algorithms)"
**Primary Tool:** `DSA Practice`
**Secondary Tools:** `Coding Round`, `Skill Readiness Test`, `Skill AI Mock`

| Week | Activity | Tool | Metric | Target |
|------|----------|------|--------|--------|
| 1 | Arrays, Strings, Fundamentals | DSA Practice | 10 easy problems | Strong fundamentals |
| 2 | LinkedList, Stack, Queue | DSA Practice | 15 problems, 80%+ | Data structures |
| 3 | Coding round - easy problems | Coding Round | 3 problems in 30 min | Interview-ready |

**Progression:**
- Week 1: Start with basics (array problems)
- Week 2: Build to intermediate (linked list, trees)
- Week 3: Practice under timed conditions

#### Fear: "Specific Skill Weak (Java, Python, React, etc.)"
**Primary Tool:** `Skill Readiness Test`
**Secondary Tools:** `Skill AI Mock`, `Coding Round`, `Readiness Roadmap`

| Week | Activity | Tool | Metric | Target |
|------|----------|------|--------|--------|
| 1 | Readiness test - diagnose gaps | Skill Readiness Test | Identify weak areas | Know what to fix |
| 2 | Practice weak concepts | Skill AI Mock | 70%+ on practice | Concept mastery |
| 3 | Apply in interviews | Coding Round | 2+ problems solved | Interview ready |

**Skill AI Mock Context:**
- Target: Dynamic (based on test results)
- Practice type: Concepts then code
- Difficulty: Adaptive

#### Fear: "Coding Skills Weak (Can't write code)"
**Primary Tool:** `Coding Round`
**Secondary Tools:** `DSA Practice`, `Skill AI Mock`

| Week | Activity | Tool | Metric | Target |
|------|----------|------|--------|--------|
| 1 | Very basic coding (loops, functions) | Coding Round | 5 basic problems | Comfortable writing |
| 2 | Medium difficulty problems | Coding Round | 4 medium problems | Solve interview problems |
| 3 | Mixed DSA + Coding | DSA Practice | 10 mixed problems | Interview ready |

**Coding Round Context:**
- Start level: Very basic (hello world)
- Time limit: Relaxed initially
- Difficulty progression: Linear

---

### 3️⃣ PROJECT & PORTFOLIO FEARS

#### Fear: "Can't Explain Projects (Technical Depth)"
**Primary Tool:** `Project AI Mock`
**Secondary Tools:** `Voice Interview`, `Mock Interview`, `Portfolio Review`

| Week | Activity | Tool | Metric | Target |
|------|----------|------|--------|--------|
| 1 | Explain architecture in detail | Project AI Mock | Clarity 70%+ | Understand deeply |
| 2 | 5-minute verbal project pitch | Voice Interview | Record 3, improve | Fluent explanation |
| 3 | Full mock interview on projects | Mock Interview | Handle follow-ups | Interview ready |

**Project AI Mock Context:**
- Focus: Technical depth
- Feedback: Detailed explanation quality
- Metrics: Clarity, depth, completeness

#### Fear: "No Real Projects (Portfolio Gap)"
**Primary Tool:** `Portfolio Review`
**Secondary Tools:** `Project AI Mock`, `Readiness Roadmap`

| Week | Activity | Tool | Metric | Target |
|------|----------|------|--------|--------|
| 1 | Plan quick project | Portfolio Review | Finalize idea | Have a plan |
| 2 | Build basic project (2 weeks) | Readiness Roadmap | Complete working | Show something |
| 3 | Practice explaining it | Project AI Mock | Explain confidently | Interview ready |

**Portfolio Review Context:**
- Action: Build quick project
- Timeline: 2 weeks
- Project ideas: Beginner-friendly (TODO app, blog)

---

### 4️⃣ CONFIDENCE & APTITUDE FEARS

#### Fear: "Aptitude Not Strong (Quant, Logical, Verbal)"
**Primary Tool:** `Aptitude Test`
**Secondary Tools:** `Readiness Roadmap`

| Week | Activity | Tool | Metric | Target |
|------|----------|------|--------|--------|
| 1 | Diagnostic test - identify weak areas | Aptitude Test | 60%+ score | Know what to improve |
| 2 | Practice weak category | Aptitude Test | 20 daily, 70%+ | Category mastery |
| 3 | Full test - validate improvement | Aptitude Test | 80%+ score | Aptitude ready |

**Aptitude Test Context:**
- Adaptive: Adjusts difficulty
- Categories: Quantitative, Logical, Verbal
- Weekly practice: 20 questions daily

#### Fear: "General Placement Confidence (Imposter Syndrome)"
**Primary Tool:** `Mock Interview`
**Secondary Tools:** `Leaderboard`, `Readiness Roadmap`, `Voice Interview`

| Week | Activity | Tool | Metric | Target |
|------|----------|------|--------|--------|
| 1 | Full interview (low pressure) | Mock Interview | Complete w/o panic | Realize you can do it |
| 2 | Check readiness roadmap | Readiness Roadmap | 70%+ overall | Build confidence via data |
| 3 | More challenging mock | Mock Interview | Higher score | See improvement |

**Mock Interview Context:**
- Type: Full round
- Feedback: Encouraging & detailed
- Purpose: Confidence building

---

## 🔄 How It Works

### 1. Student Takes Initial Check-In
```
Input: 8 conversational questions about fears
Output: 3 main fears with severity (1-10)
```

### 2. System Maps Fears to Widgets
```python
fear = "Can't explain projects"
widget = get_widget_for_fear(fear)
# Returns: FEAR_PROJECT_EXPLANATION
```

### 3. OpenAI Generates 6-Week Plan
```
Input:
- Fear name + severity
- Student profile
- **Widget context** (primary tool, secondary tools, progression)

Output: 6-week plan that specifically uses these tools
```

Example week 1 for project explanation fear:
```json
{
  "day1": {
    "action": "Use Project AI Mock to explain your project architecture",
    "tool": "project_ai_mock",
    "metric": "Clarity score 60%+",
    "duration": "15 minutes"
  },
  "day2": {
    "action": "Re-record explanation based on feedback",
    "tool": "project_ai_mock",
    "metric": "Clarity improved by 10%",
    "duration": "15 minutes"
  },
  ...
}
```

### 4. Student Follows the 6-Week Journey
Each week points to specific widgets with clear metrics.

### 5. Progress is Tracked Against Widget Usage
- Did they use AI HR Mock on schedule?
- Did they complete DSA practice problems?
- What was their Skill Readiness Test score improvement?

---

## 🛠️ Available Widgets

### Communication & Interview
- **AI HR Mock** - HR interview practice with feedback
- **Voice Interview** - Real-time voice interview practice
- **Mock Interview** - Full technical + HR interview simulation

### Technical Learning
- **Skill Readiness Test** - Assess knowledge gaps in a skill
- **Skill AI Mock** - Practice concepts & coding for a skill
- **Coding Round** - Practice coding problems
- **DSA Practice** - Data structures & algorithm problems

### Project & Portfolio
- **Project AI Mock** - Practice explaining technical projects
- **Portfolio Review** - Get feedback on portfolio/projects

### Aptitude
- **Aptitude Test** - Adaptive aptitude test (quant, logical, verbal)

### Navigation & Progress
- **Readiness Roadmap** - Personalized learning path
- **Mock Interview** - Full interview with all rounds
- **Leaderboard** - Compare progress (optional for motivation)

---

## 📊 Widget Usage Tracking

When a student submits weekly progress, the system can check:

```python
# In weekly_progress endpoint
weekly_progress = {
    "fear_id": "project_explanation",
    "week": 1,
    "tools_used": [
        {"tool": "project_ai_mock", "sessions": 5, "score": 0.72},
        {"tool": "voice_interview", "sessions": 0}  # Not used yet
    ],
    "actions_completed": 5,  # Out of 7
    "metric": "Clarity score 72%"
}
```

The AI feedback can reference this:
```
"You used Project AI Mock 5 times this week and improved clarity from 60% to 72%.
Great work! Continue this pattern next week and add Voice Interview practice."
```

---

## 🎯 Benefits of This Approach

### For Students
✅ **Practical** - Advice points to real tools they can use now
✅ **Specific** - Know exactly what to do each day
✅ **Measurable** - Can see progress in each tool
✅ **Integrated** - Seamless experience across MentorMuni

### For MentorMuni
✅ **Drives Tool Usage** - Each fear drives students to specific tools
✅ **Data Insights** - See which tools help which fears
✅ **Engagement** - 6 weeks of structured, guided usage
✅ **Differentiation** - Personalized paths for each student

### For the Business
✅ **Premium Feature** - Intervention system is a differentiator
✅ **Monetization** - Can charge for personalized coaching
✅ **Retention** - 6-week structured journey keeps students engaged
✅ **Network Effects** - Success stories drive word-of-mouth

---

## 🔧 Adding New Fears

To add a new fear → widget mapping:

```python
# In fear_to_widget_mapping.py

FEAR_CUSTOM = FearWidget(
    fear_id="custom_fear",
    fear_name="Custom Fear Description",
    primary_widget=WidgetType.SOME_TOOL,
    secondary_widgets=[WidgetType.SUPPORTING_TOOL1],
    context={
        "some_tool": {
            "setting1": "value1",
            "setting2": "value2",
        }
    },
    progression=[
        {
            "week": 1,
            "activity": "What to do week 1",
            "tool": WidgetType.SOME_TOOL,
            "metric": "How to measure",
            "target": "Goal for week 1",
        },
        # ... weeks 2-3
    ]
)

# Add to mapping
FEAR_TO_WIDGET_MAP["custom_fear"] = FEAR_CUSTOM
```

Then OpenAI will automatically use this when generating the 6-week plan.

---

## 📈 Example Flow for One Student

### Step 1: Initial Check-In
Student takes 8-question interview, identifies fears:
```
- "Can't explain my projects" (severity: 9)
- "Weak in Java" (severity: 7)
- "General confidence issues" (severity: 8)
```

### Step 2: Widget Mapping
System maps to:
```
Project Fear      → Project AI Mock (primary) + Voice Interview + Mock Interview
Java Skill Fear   → Skill Readiness Test → Skill AI Mock → Coding Round
Confidence Fear   → Mock Interview + Readiness Roadmap + Leaderboard
```

### Step 3: 6-Week Plans Generated
Each with specific widget usage:
```
Week 1:
  Day 1-7: Use Project AI Mock (target: 60% clarity)
           Use Skill Readiness Test (diagnose Java gaps)
           Use Mock Interview (build confidence)
           
Week 2:
  Day 8-14: Voice Interview for project explanation
            Skill AI Mock for Java concepts
            Check Readiness Roadmap progress
            
Week 3:
  Day 15-21: Full Mock Interview
             Coding problems from Java topics
             Milestone check-in
```

### Step 4: Weekly Progress
Each week, student reports:
```
"I used Project AI Mock 5 times, improved to 72% clarity.
Did 10 Java practice problems, scoring 75%.
Took a mock interview, improved by 15 points."

AI Response: "Excellent progress! Fear reduced from 9→7.
Continue with Voice Interview next week."
```

### Step 5: After 6 Weeks
```
Project Explanation: 9/10 → 0/10 ✅
Java Skills: 7/10 → 1/10 ✅
Confidence: 8/10 → 0/10 ✅

Student is ready for placements!
```

---

## 🚀 Implementation Status

✅ Fear to Widget mapping created  
✅ Widget context system built  
✅ OpenAI prompts updated to use widgets  
✅ Service layer integrated  
✅ Week-by-week progression defined  

Ready for immediate use!

---

## 📞 Support

For questions about mapping a specific fear:
1. Check `FEAR_TO_WIDGET_MAP` for existing mapping
2. If not found, create new `FearWidget` object
3. Add to `FEAR_TO_WIDGET_MAP` dictionary
4. OpenAI will automatically use it for that fear

That's it! No other changes needed.
