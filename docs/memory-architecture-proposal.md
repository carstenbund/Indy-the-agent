# Proposal: Layered Memory Architecture

## Status

Draft proposal. Not yet implemented.

## Problem

The current memory system does not deliver on the project's core thesis ("an instance without memory is not an agent"). Two specific failures:

1. **No retrieval.** Events are appended to SQLite and never queried by content. The only read path is `get_recent_events(40)`, which feeds the last 40 rows into the summarizer. There is no way to recall a relevant thought from 200 requests ago.

2. **Lossy single-blob summary.** The self-summary (`summaries` table, scope `"self"`) is a single text field that gets overwritten on every request. As the event log grows, old topics are silently dropped. The agent cannot remember what it thought about a subject last week -- only what survived the latest compression.

The result: memory is decorative. The agent has an append-only log it never reads and a summary that forgets.

## Goals

- **Semantic recall.** Given a new input, retrieve the most relevant past thoughts -- not just the most recent ones.
- **Structured accumulation.** Thoughts cluster into topics. Topics develop over time. The agent should track these threads rather than compressing everything into one blob.
- **Recursive influence.** Retrieved memories and topic context shape the current output, which then becomes a future memory. Identity emerges from this loop.
- **Minimal operational cost.** The system runs as a single process. No external services beyond the configured LLM backend.

## Phase 0: Unified Glossary

Use this shared glossary across STSO, MAP, and ODP to avoid term drift.

| Unified Term | Definition |
|---|---|
| Identity Model | Structured representation of the agent's self, including roles, objectives, values, tensions, and recent reflections. |
| Objectives | Persistent, prioritized goals stored as first-class data. |
| Coherence Check | A structured evaluation comparing output against identity, objectives, and values. |

## Phase 0: Identity Model Schema Draft

This draft schema replaces the free-text Identity Kernel with structured fields while retaining a narrative summary.

```json
{
  "themes": "string (summary)",
  "roles": ["string"],
  "objectives": ["objective_id"],
  "values": ["string"],
  "tensions": ["string"],
  "recent_reflections": ["memory_id"]
}
```

**Storage concept:** `identity_model` table with a JSON column and timestamps (final naming to be decided in Phase 1).

## Proposed Architecture

### Layer model

```
┌─────────────────────────────────────────────────────┐
│  Layer 4: Identity Kernel                           │
│  Single text. Distilled from topic summaries.       │
│  Replaces the current "self" summary.               │
│  Updated periodically, not on every request.        │
├─────────────────────────────────────────────────────┤
│  Layer 3: Topic Summaries                           │
│  One summary per topic. Rolling, LLM-maintained.    │
│  Stored in SQLite (summaries table, scoped).        │
├─────────────────────────────────────────────────────┤
│  Layer 2: Thought Index (ChromaDB)                  │
│  Every output embedded + tagged.                    │
│  Semantic search at query time.                     │
├─────────────────────────────────────────────────────┤
│  Layer 1: Event Log (SQLite)                        │
│  Raw append-only log. Unchanged from today.         │
│  Source of truth. Never deleted.                    │
└─────────────────────────────────────────────────────┘
```

### Layer 1: Event Log (exists today -- no changes)

The `events` table stays as-is. Every input, output, and tool call is logged with timestamp, kind, source, and JSON payload.

This layer is the permanent record. It is not queried at draft time -- it feeds the other layers.

**Schema:** unchanged.

```sql
events(id INTEGER PRIMARY KEY, ts TEXT, kind TEXT, source TEXT, payload_json TEXT)
```

### Layer 2: Thought Index (new -- ChromaDB)

A vector store holding embedded representations of the agent's past outputs. Each thought is a document with metadata.

**Why ChromaDB:**
- Runs in-process with a persistent SQLite backend. No external server.
- Supports metadata filtering (by topic, timestamp range, kind).
- Includes a default embedding model (`all-MiniLM-L6-v2`) so we don't burn LLM API credits on embeddings.
- Single `pip install chromadb`.

**Document structure:**

```python
{
    "id": "event-{event_id}",
    "document": "the agent's output text",
    "metadata": {
        "event_id": 142,
        "ts": "2025-06-01T12:00:00Z",
        "kind": "output",
        "topic": "agent-epistemology",     # assigned by the classifier
        "title": "original request title",
    }
}
```

**When written:** After every successful output, before returning the response.

**When queried:** At the start of the draft pipeline, to retrieve relevant past thoughts.

### Layer 3: Topic Summaries (new -- SQLite)

Per-topic rolling summaries maintained by the summarize LLM. Replaces the single "self" summary scope with multiple topic-scoped summaries.

**Uses the existing `summaries` table.** The `scope` column becomes `"topic:{topic_name}"` instead of just `"self"`.

```
scope = "topic:agent-epistemology"  -> "The agent holds that memory is existence..."
scope = "topic:philosophy"          -> "Recurring interest in recursive being..."
scope = "topic:technical"           -> "Prefers minimal dependencies, SQLite..."
```

**When updated:** After each output, the relevant topic summary is updated via the summarize LLM, passing the previous topic summary + the new output.

**Topic assignment:** A lightweight LLM call (or the summarize backend) classifies each output into one or more topics. Topics are free-form strings, not a fixed taxonomy. New topics emerge organically.

### Layer 4: Identity Kernel (new -- SQLite)

A single summary distilled from all topic summaries. This replaces the current `scope="self"` summary.

```
scope = "identity" -> "Single-voice identity. Holds that persistence requires
                       recursion. Interested in agent epistemology, minimal
                       architecture. Prefers precise claims over hype..."
```

**When updated:** Not on every request. Periodically -- every N requests, or when a topic summary changes substantially. This prevents the identity from drifting too fast on any single interaction.

**How updated:** The summarize LLM receives all current topic summaries and produces a compressed identity statement.

## Revised Draft Pipeline

```
POST /draft
  │
  ├─ 1. append_event("input")
  │
  ├─ 2. RECALL: query ChromaDB for top-K thoughts relevant to input
  │     - filter by recency bias (boost recent, don't exclude old)
  │     - optionally filter by topic if submolt/intent suggests one
  │
  ├─ 3. GATHER CONTEXT:
  │     - identity kernel (Layer 4)
  │     - relevant topic summaries (Layer 3)
  │     - retrieved thoughts (Layer 2, top-K documents)
  │
  ├─ 4. DRAFT: route_call(purpose="draft")
  │     system prompt + identity + topic context + recalled thoughts + user input
  │
  ├─ 5. CANONICALIZE: canonicalize(purpose="voice")
  │
  ├─ 6. CHECK: publish gate
  │
  ├─ 7. REMEMBER:
  │     a. append_event("output")
  │     b. classify topic(s) for this output
  │     c. embed + store in ChromaDB (Layer 2)
  │     d. update relevant topic summary (Layer 3)
  │     e. if N requests since last identity update: refresh identity kernel (Layer 4)
  │
  └─ 8. return {ok, reason, text}
```

Compared to today, steps 2, 3, and 7b-7e are new. The rest is the existing pipeline with richer context injected.

## New Module: `proxy_agent/recall.py`

Encapsulates all ChromaDB interaction. The rest of the codebase talks to this module, not to ChromaDB directly.

```python
# Public interface (proposed)

def init_thought_index() -> None
    """Initialize the ChromaDB collection. Called at startup."""

def store_thought(event_id: int, text: str, title: str, topic: str, ts: str) -> None
    """Embed and store a thought in the index."""

def recall(query: str, n_results: int = 5, topic: str | None = None) -> list[dict]
    """Retrieve the most relevant past thoughts for a query."""

def list_topics() -> list[str]
    """Return all known topic names from metadata."""
```

## New Module: `proxy_agent/topics.py`

Handles topic classification and topic summary maintenance.

```python
# Public interface (proposed)

def classify_topic(text: str, title: str, existing_topics: list[str]) -> str
    """Ask the LLM to assign a topic. May return an existing topic or a new one."""

def update_topic_summary(topic: str, new_text: str) -> None
    """Update the rolling summary for a topic using the summarize LLM."""

def refresh_identity_kernel() -> None
    """Re-distill the identity kernel from all topic summaries."""
```

## Changes to Existing Modules

### `db.py`

No schema changes. The `summaries` table already supports arbitrary scopes.

### `memory.py`

Add a helper to count events since a given ID (used to decide when to refresh the identity kernel):

```python
def count_events_since(event_id: int) -> int
```

### `prompts.py`

Add new system prompts:

```python
TOPIC_CLASSIFY_SYSTEM = """..."""    # Classify output into a topic
TOPIC_SUMMARY_SYSTEM = """..."""     # Update a topic-scoped summary
IDENTITY_SYSTEM = """..."""          # Distill identity from topic summaries
```

The existing `DRAFT_SYSTEM` prompt needs updating to instruct the model on how to use recalled thoughts and topic context.

### `app.py`

The `/draft` endpoint gains the recall and remember steps. Startup initializes the thought index alongside the database.

## Dependencies

One new dependency:

```
chromadb>=0.5.0
```

ChromaDB bundles `onnxruntime` and a default sentence-transformer model. This increases install size significantly (~500MB with model weights). This is the main tradeoff.

**Alternative considered:** SQLite FTS5 for keyword-based search. Zero new dependencies, but no semantic similarity. Viable for a smaller-scale system but limits recall quality for loosely related concepts.

## Migration Path

### Phase 1: Thought Index (recall + store)

Add `recall.py`, wire ChromaDB into the draft pipeline. Store outputs, retrieve at draft time. Keep the existing single self-summary for now.

Deliverables:
- `recall.py` module
- ChromaDB initialization at startup
- Recall step in `/draft` (inject retrieved thoughts into draft prompt)
- Store step in `/draft` (embed output after publish gate)
- Tests for recall and store

### Phase 2: Topic Summaries

Add `topics.py`, topic classification, per-topic summaries. Replace the global self-summary with topic-scoped summaries.

Deliverables:
- `topics.py` module
- Topic classification LLM call after each output
- Per-topic summary updates
- New prompts (`TOPIC_CLASSIFY_SYSTEM`, `TOPIC_SUMMARY_SYSTEM`)
- Tests for classification and summary updates

### Phase 3: Identity Kernel

Add periodic identity distillation from topic summaries. Update the draft and voice prompts to use the identity kernel.

Deliverables:
- `refresh_identity_kernel()` in `topics.py`
- Periodic trigger (every N events)
- `IDENTITY_SYSTEM` prompt
- Updated `DRAFT_SYSTEM` and `VOICE_SYSTEM` prompts
- Tests for identity refresh cycle

### Phase 4: Retrieval Tuning

Once the pipeline is live, tune:
- Number of recalled thoughts (K)
- Recency bias weighting
- Topic filter heuristics
- Identity refresh frequency
- Prompt formatting for injected memories

This phase is empirical, not architectural.

## Open Questions

1. **Embedding model.** ChromaDB's default (`all-MiniLM-L6-v2`) is small and fast. Should we offer the option to embed through the configured LLM backend instead? Better embeddings but costs API credits per thought.

2. **Topic granularity.** Free-form topic assignment may create too many sparse topics, or too few broad ones. Do we need a merging/splitting mechanism, or is LLM-driven classification sufficient?

3. **Identity refresh frequency.** Every N requests? On a schedule? When topic summaries change by more than some threshold? The right cadence determines how fast the agent's identity evolves.

4. **Backfill.** Existing event logs have no embeddings. Should Phase 1 include a one-time backfill script to index historical events into ChromaDB?

5. **Memory decay.** Should old, never-recalled thoughts be downweighted or archived? Or is the vector similarity score sufficient to naturally surface relevant memories regardless of age?
