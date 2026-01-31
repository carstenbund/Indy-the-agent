# Memory Architecture Evaluation Guide

## Purpose

This guide defines how to evaluate the proposed layered memory architecture in a
way that balances product quality, performance, and operational cost. It is
intended to be used incrementally alongside the migration phases.

## Core Principles

- **Measure recall quality before increasing complexity.** Only advance to the
  next phase if the current phase produces tangible improvements in relevance
  and consistency.
- **Prefer observable outcomes over intuition.** Use concrete metrics and
  repeatable tests.
- **Track cost and footprint.** Memory improvements that double runtime or
  install size are only justified if they demonstrably improve agent behavior.

## Phase 1 Evaluation: Thought Index (Recall + Store)

### Goals

- Verify semantic recall improves response quality over baseline.
- Validate that indexing and retrieval are performant and stable.
- Confirm that stored thoughts are correctly linked to events.

### Setup

- Use a fixed suite of prompts (10–30) that span distinct topics and time gaps.
- Build a baseline by running prompts with the current memory system and
  recording outputs.
- Run the same suite with recall enabled and compare results.

### Measurements

**Quality**

- **Recall relevance score (human-rated):** 1–5 score on whether recalled
  thoughts are meaningfully related to the new prompt.
- **Output consistency score (human-rated):** 1–5 score on whether the response
  aligns with prior stated positions.
- **Recall utilization:** percentage of prompts where recalled content is
  explicitly used in the output.

**Performance**

- **p50/p95 retrieval latency:** time from query to retrieved thoughts.
- **Memory footprint:** size on disk of the ChromaDB index.
- **CPU cost:** average CPU usage during recall on the prompt suite.

**Correctness**

- **Event linkage audit:** sample 20 stored thoughts and verify event_id, title,
  and timestamp are correct.
- **Recall stability:** repeated queries with same input should return similar
  top-K results (allowing for minor variance).

### Success Criteria (Suggested)

- Recall relevance score ≥ 4.0 average.
- Output consistency score improves by ≥ 0.5 over baseline.
- p95 retrieval latency ≤ 250ms on local hardware.
- Index size growth ≤ 1.5x raw output text size.

### Decision Gate

Proceed to Phase 2 only if recall improves quality and does not introduce
unacceptable latency or storage cost.

## Phase 2 Evaluation: Topic Summaries

### Goals

- Validate that topic classification is coherent and stable over time.
- Confirm topic summaries improve continuity across sessions.

### Setup

- Use the same prompt suite plus a small set (5–10) of longitudinal prompts
  that revisit topics days later.
- Capture baseline behavior with Phase 1 only.

### Measurements

**Classification Quality**

- **Topic stability:** percentage of similar prompts mapped to the same topic.
- **Topic sprawl:** ratio of total topics to total prompts.
- **Manual audit:** review 20 classifications for reasonableness.

**Summary Quality**

- **Topic summary fidelity:** 1–5 score on whether the summary accurately
  reflects the set of outputs in that topic.
- **Continuity improvement:** 1–5 score on whether later outputs reflect the
  correct topic context.

### Success Criteria (Suggested)

- Topic stability ≥ 70% on similar prompts.
- Topic sprawl ≤ 1 topic per 3 prompts (adjust based on dataset size).
- Summary fidelity ≥ 4.0 average.

### Decision Gate

Proceed to Phase 3 only if topic summaries improve continuity without excessive
fragmentation.

## Phase 3 Evaluation: Identity Kernel

### Goals

- Validate that the identity kernel stabilizes behavior without drifting too
  quickly.
- Ensure the identity kernel remains coherent and aligned with topic summaries.

### Setup

- Run the prompt suite across multiple sessions spaced over time.
- Compare responses with and without identity kernel injection.

### Measurements

- **Identity coherence score:** 1–5 score on whether the identity statement
  remains consistent with topic summaries.
- **Drift rate:** number of substantial identity shifts per N requests.
- **Behavioral stability:** change in output tone/stance across sessions.

### Success Criteria (Suggested)

- Identity coherence ≥ 4.0 average.
- Drift rate ≤ 1 substantial shift per 50 requests.
- Behavioral stability improves relative to Phase 2.

### Decision Gate

Only retain the identity kernel if it clearly improves stability and does not
introduce regressions or rigidity.

## Phase 4 Evaluation: Retrieval Tuning

### Goals

- Optimize recall for quality and speed.
- Avoid overloading the draft prompt with irrelevant context.

### Measurements

- **Recall precision/recall tradeoff:** vary K and measure relevance vs noise.
- **Recency weighting:** test different recency biases and measure relevance.
- **Prompt bloat:** total context length added per request.

### Success Criteria (Suggested)

- Best-performing configuration improves quality without exceeding context
  budget or latency targets.

## Evaluation Artifacts

Capture and store the following for each phase:

- Prompt suite and outputs (baseline vs experimental).
- Score sheets and reviewer notes.
- Performance logs and resource usage.
- Final decision log noting whether the phase is accepted or rejected.

## Optional Automation Ideas

- Build a small harness that runs the prompt suite against the agent and
  records outputs, timings, and retrieved memories.
- Use a structured scoring sheet (JSON or CSV) to standardize human ratings.
- Track results over time to detect regressions as the memory system evolves.
