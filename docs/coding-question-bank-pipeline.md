# Coding Question Bank Pipeline

Internal/admin content-generation + validation pipeline for MentorMuni placement coding problems.

**Status:** Pipeline implemented. **Do not generate the ~50 problems until this design is reviewed.**

This package does **not** change Phase 2/3 student execution architecture, does **not** wire Judge0 into generation, and does **not** auto-publish to students.

## Goals

Hiring Intelligence → patterns → AI candidate problem → reference solution → tests → validation → duplicate detection → quality → human approval → production bank.

MVP target: ~50 **canonical** placement problems (not per-company clones). Company/role relevance is metadata on one problem.

## Database changes (Alembic `0019_coding_question_bank`)

### Extended existing tables (no duplicate production problem tables)

| Table | Additions |
|-------|-----------|
| `coding_problems` | `prompt_version`, `generation_model`, `generation_run_id`, `quality_score`, `validation_summary_json`, `approved_at`, `approved_by`, `published_at`, `rejected_reason`, `content_fingerprint` |
| `coding_problem_versions` | `explanation_text`, `supported_languages_json`, `generation_payload_json` |
| `coding_test_cases` | `category` |

### New support tables

| Table | Purpose |
|-------|---------|
| `coding_generation_runs` | Batch/config tracking for curriculum generation |
| `coding_validation_results` | Append-only validation reports |
| `coding_problem_relevances` | Canonical problem ↔ company/role/round + evidence/confidence |

Student APIs continue to serve only `coding_problems.status = published`.

## Package layout

```
app/coding_bank/
  schemas.py       # GeneratedProblemContract (strict Pydantic)
  prompt.py        # coding_problem_generation_v1
  curriculum.py    # placement_v1 matrix (~50 specs)
  generator.py     # OpenAI client wrapper (rejects malformed JSON)
  validators/      # schema, content, reference, tests, duplicate, quality, pipeline
  lifecycle.py     # status transitions
  promote.py       # persist + approve + publish
  service.py       # CodingBankService façade
```

## Generation JSON schema

Validated by `GeneratedProblemContract` (`extra=forbid`):

- Identity: `title`, `slug`
- Classification: `difficulty`, `topics[]`, `patterns[]`, complexities
- Student content: `problem_statement`, `input_format`, `output_format`, `constraints`, `examples[]`, `explanation`
- Execution: `supported_languages`, `starter_code[]`, `reference_solutions[]`, `candidate_test_cases[]`

Hard rules in schema:

- kebab-case slug
- ≥1 Python reference solution
- ≥5 tests across ≥3 categories including `normal`
- Big-O strings must contain `O(...)`

Export: `GENERATED_PROBLEM_JSON_SCHEMA` / `openai_response_format()`.

## Prompt version

`PROMPT_VERSION = coding_problem_generation_v1`

Instructs original placement wording; prohibits copying proprietary banks; requires internal consistency of statement + constraints + examples + reference + tests.

## Validation architecture

```
AI JSON
  → SchemaValidator
  → ContentValidator
  → ComplexityValidator
  → ReferenceSolutionValidator   # static AST + optional ReferenceExecutor
  → TestCaseValidator            # input → reference → canonical expected_output
  → DuplicateDetector            # normalized title/statement/topic/pattern (+ fingerprint)
  → QualityValidator             # 0–100 heuristic score
  → ProblemValidator (orchestrator)
```

`ReferenceExecutor` is an interface. Default is `NullReferenceExecutor` (no Judge0 coupling). When a real executor (future `CodeExecutionService` adapter) is injected, LLM `expected_output` is overwritten by reference stdout.

## Lifecycle

```
generated → validating → pending_review → approved → published
                   ↘ validation_failed
         pending_review → rejected
published → archived only (never overwrite immutable published version rows)
```

## Generation matrix (`placement_v1`)

Configurable via `CurriculumConfig` / `config_json` on `coding_generation_runs`. Default ~50 slots across:

Arrays, Strings, Hashing, Two Pointers, Sliding Window, Binary Search, Stack, Queue, Linked List, Trees, Graphs, Greedy, Recursion, Backtracking, Dynamic Programming.

Build with `build_placement_curriculum_v1()`.

## Approval → production bank

1. Persist contract → `CodingProblem` + `CodingProblemVersion` v1 + refs + tests (`status=generated`)
2. Validate → `pending_review` or `validation_failed` (+ `coding_validation_results` row)
3. Human `approve_problem` → `approved` (sets `approved_at` / `approved_by`)
4. `promote_to_published` → `published` + `published_at`
5. Optional: `attach_relevance(...)` for company/role/round without cloning the problem
6. Student assessments may then attach the published problem (existing Phase 2 mapping)

Only **approved** can publish. Rejected stay unavailable to students.

## Student Coding Round (topic browser + practice resolve)

### What students see
1. Free-text **Topic** + **Level** (+ optional company theme)
2. **Topic browser** of published bank problems
3. **Practice sets** (per-topic assessments)
4. Results + AI coaching

### APIs
- `GET /api/coding/topics`
- `GET /api/coding/bank/problems?topic=&difficulty=`
- `POST /api/coding/practice/resolve` `{ topic, difficulty, company_key?, allow_generate }`

Resolve flow: match published bank → else generate original problem with campus-placement guardrails → validate → publish → create practice assessment → start.

### Seed bank
```bash
cd mentormuni-api
python -m app.coding_bank.bootstrap_seed
```
Curated catalog: ~22 problems in `seed_catalog.py`. On-demand generation fills gaps toward ~50+.

## How to run tests

```bash
cd mentormuni-api
pytest tests/test_coding_bank_pipeline.py -q
```
