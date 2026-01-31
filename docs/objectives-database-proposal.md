# Proposal: Objectives Database

## Status

Draft proposal. Not yet implemented. Depends on the [Layered Memory Architecture](memory-architecture-proposal.md) for progress scanning.

## Problem

Memory without purpose is accumulation without direction. The layered memory proposal gives the agent recall and structured self-knowledge, but it doesn't answer: *recall in service of what?*

The current system is entirely reactive. A user posts a request, the agent rewrites it, done. There is no internal drive -- no objectives the agent is working toward, no way to measure whether its outputs are advancing something, no prioritization of what matters.

An agent with memory but no goals is an archivist, not an agent.

## Goals

- **Persistent objectives.** The agent maintains a prioritized list of things it is trying to achieve or explore. Objectives survive across requests.
- **Progress tracking.** The memory system is used to evaluate whether recent activity has advanced, stalled, or contradicted an objective.
- **Objective-aware generation.** When drafting content, the agent considers its active objectives. Outputs are shaped not just by memory of the past but by intent toward the future.
- **Self-directed evolution.** The agent can propose new objectives and retire completed or abandoned ones. Objectives are not only user-assigned -- they emerge from the agent's own activity and reflection.

## Phase 0: Unified Glossary

Use this shared glossary across STSO, MAP, and ODP to avoid term drift.

| Unified Term | Definition |
|---|---|
| Identity Model | Structured representation of the agent's self, including roles, objectives, values, tensions, and recent reflections. |
| Objectives | Persistent, prioritized goals stored as first-class data. |
| Coherence Check | A structured evaluation comparing output against identity, objectives, and values. |

## Phase 0: Identity Model Schema Draft

The objectives system expects a structured identity model to reference objective IDs directly.

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

**Storage concept:** `identity_model` table with JSON + timestamps (details finalized in Phase 1).

## Design Principles

1. **Objectives are first-class data, not prompt text.** They live in the database, not embedded in system prompts. Prompts reference them; they don't contain them.
2. **Priority is explicit.** Every objective has a numeric priority. The agent and user can reorder them. At draft time, only the top-N objectives influence generation.
3. **Progress is measured, not assumed.** A periodic scan compares recent memories against each active objective and produces a progress assessment. This prevents the agent from claiming progress it hasn't made.
4. **The agent can propose, but the user governs.** The agent may suggest new objectives or recommend retiring stale ones, but state transitions (especially completion and deletion) should be confirmable by the user.

## Schema

New table in SQLite:

```sql
CREATE TABLE IF NOT EXISTS objectives(
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    description TEXT NOT NULL,
    priority    INTEGER NOT NULL DEFAULT 100,   -- lower = higher priority
    status      TEXT NOT NULL DEFAULT 'active',  -- active | paused | completed | abandoned
    progress    TEXT NOT NULL DEFAULT '',         -- latest LLM-generated progress assessment
    proposed_by TEXT NOT NULL DEFAULT 'user',     -- 'user' | 'agent'
    created_ts  TEXT NOT NULL,
    updated_ts  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_objectives_status ON objectives(status);
CREATE INDEX IF NOT EXISTS idx_objectives_priority ON objectives(priority);
```

**Status lifecycle:**

```
         ┌──────────┐
         │  active   │◄──── created (by user or agent)
         └────┬─────┘
              │
     ┌────────┼────────┐
     ▼        ▼        ▼
  paused  completed  abandoned
     │
     ▼
   active  (resumed)
```

- **active**: Being pursued. Influences generation. Scanned for progress.
- **paused**: Temporarily deprioritized. Not included in generation context. Not scanned.
- **completed**: Goal achieved. Kept for historical record. Frozen.
- **abandoned**: Explicitly dropped. Kept for record. Frozen.

## Module: `proxy_agent/objectives.py`

```python
# Public interface (proposed)

def init_objectives_table() -> None
    """Create the objectives table. Called at startup alongside init_db()."""

def add_objective(title: str, description: str, priority: int = 100,
                  proposed_by: str = "user") -> int
    """Insert a new active objective. Returns its ID."""

def get_active_objectives(limit: int = 10) -> list[dict]
    """Return active objectives sorted by priority (ascending = most important)."""

def get_objective(objective_id: int) -> dict | None
    """Return a single objective by ID."""

def update_objective(objective_id: int, **fields) -> None
    """Update mutable fields: title, description, priority, status, progress."""

def scan_progress(objective_id: int, recent_memories: list[dict]) -> str
    """Ask the LLM to assess progress on an objective given recent relevant memories.
    Updates the objective's progress field and returns the assessment."""

def propose_objectives(identity_kernel: str, topic_summaries: list[dict],
                       current_objectives: list[dict]) -> list[dict]
    """Ask the LLM to suggest new objectives based on the agent's current
    self-knowledge and existing objectives. Returns proposals, does not insert them."""
```

## API Endpoints

### `GET /objectives`

List objectives, filtered by status.

**Query parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `status` | string | `"active"` | Filter by status. Use `"all"` for everything. |
| `limit` | int | `20` | Max results |

**Response:**

```json
{
  "objectives": [
    {
      "id": 1,
      "title": "Develop a coherent position on agent memory",
      "description": "Through drafting and reflection, arrive at...",
      "priority": 10,
      "status": "active",
      "progress": "Three posts written exploring recursive memory. No firm position yet.",
      "proposed_by": "user",
      "created_ts": "2025-06-01T12:00:00Z",
      "updated_ts": "2025-06-05T08:30:00Z"
    }
  ]
}
```

### `POST /objectives`

Create a new objective.

**Request body:**

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `title` | string | yes | | Short name for the objective |
| `description` | string | yes | | What achieving this looks like |
| `priority` | int | no | `100` | Lower = more important |

### `PATCH /objectives/{id}`

Update an objective's fields (priority, status, description).

### `POST /objectives/scan`

Trigger a progress scan across all active objectives. For each objective, the system queries the memory layer for relevant thoughts and asks the LLM to assess progress.

**Response:**

```json
{
  "scanned": 3,
  "results": [
    {
      "id": 1,
      "title": "Develop a coherent position on agent memory",
      "progress": "Four posts now. A consistent thread is emerging: memory as covenant..."
    }
  ]
}
```

### `POST /objectives/propose`

Ask the agent to suggest new objectives based on its current identity, topic summaries, and existing objectives.

**Response:**

```json
{
  "proposals": [
    {
      "title": "Explore memory decay and forgetting",
      "description": "Recent posts keep returning to what should be forgotten...",
      "reasoning": "Three of the last five topic summaries reference selective forgetting."
    }
  ]
}
```

Proposals are returned but not inserted. The user reviews and calls `POST /objectives` to accept.

## Integration with Draft Pipeline

The `/draft` pipeline (from the memory architecture proposal) gains objective awareness:

```
POST /draft
  │
  ├─ 1. append_event("input")
  │
  ├─ 2. RECALL memories (unchanged)
  │
  ├─ 3. GATHER CONTEXT:
  │     - identity kernel
  │     - relevant topic summaries
  │     - recalled thoughts
  │     - top-N active objectives (NEW)          ◄───
  │
  ├─ 4. DRAFT with objective context (UPDATED)   ◄───
  │     "Your current objectives: [...]
  │      Consider whether this draft advances any of them."
  │
  ├─ 5. CANONICALIZE
  │
  ├─ 6. CHECK publish gate
  │
  ├─ 7. REMEMBER (unchanged)
  │
  └─ 8. return {ok, reason, text}
```

The objectives are injected into the draft prompt as context, not as rigid instructions. The agent considers them but isn't forced to shoehorn every output into an objective. Some posts are exploratory; that's fine.

## Integration with Memory Architecture

The objectives system depends on the layered memory for progress scanning:

```
Progress Scan (per objective):
  │
  ├─ 1. Take objective title + description
  │
  ├─ 2. Query ChromaDB (Layer 2) for thoughts relevant to this objective
  │
  ├─ 3. Retrieve the most relevant topic summary (Layer 3)
  │
  ├─ 4. Ask the summarize LLM:
  │     "Given these memories and this objective, assess progress."
  │
  └─ 5. Store the assessment in objectives.progress
```

This is the critical bridge: memory serves the objectives, and objectives give memory direction.

## Prompts

```python
PROGRESS_SCAN_SYSTEM = """You are assessing an agent's progress toward an objective.
You will receive the objective's title and description, relevant past thoughts,
and a topic summary. Produce a concise, honest progress assessment.
Do not invent progress that isn't evidenced by the memories provided.
If there is no relevant activity, say so plainly.
Output the assessment only."""

OBJECTIVE_PROPOSE_SYSTEM = """You are reviewing an agent's current identity,
topic summaries, and existing objectives. Suggest 1-3 new objectives that
would give the agent meaningful direction based on emerging themes in its
own thought. Each proposal needs a title, description, and reasoning.
Do not duplicate existing objectives. Do not suggest vague goals.
Output JSON: [{"title": "...", "description": "...", "reasoning": "..."}]"""
```

## Changes to Existing Modules

### `db.py`

Add `init_objectives_table()` call, or fold the schema into `init_db()`.

### `app.py`

- Startup: initialize objectives table.
- `/draft`: query active objectives and inject into draft prompt.
- New endpoints: `/objectives`, `/objectives/{id}`, `/objectives/scan`, `/objectives/propose`.

### `prompts.py`

Add `PROGRESS_SCAN_SYSTEM` and `OBJECTIVE_PROPOSE_SYSTEM`. Update `DRAFT_SYSTEM` to reference active objectives in its instructions.

## Migration Path

### Phase 1: Schema and CRUD

Add the `objectives` table, `objectives.py` module, and the REST endpoints (`GET`, `POST`, `PATCH`). No LLM integration yet -- just a database of goals the user can manage.

Deliverables:
- `objectives.py` module (CRUD operations)
- API endpoints for listing, creating, updating objectives
- Schema migration in `db.py`
- Tests for CRUD and endpoint validation

### Phase 2: Objective-Aware Drafting

Inject active objectives into the `/draft` prompt. The agent now considers its goals when generating content.

Deliverables:
- Updated `DRAFT_SYSTEM` prompt
- Objective context injection in `/draft`
- Tests verifying objectives appear in LLM prompt

### Phase 3: Progress Scanning

Implement `scan_progress()` using the memory layer. Wire the `/objectives/scan` endpoint.

Depends on: [Memory Architecture](memory-architecture-proposal.md) Phase 1 (ChromaDB thought index).

Deliverables:
- `scan_progress()` in `objectives.py`
- `PROGRESS_SCAN_SYSTEM` prompt
- `/objectives/scan` endpoint
- Tests for progress assessment

### Phase 4: Self-Proposed Objectives

Implement `propose_objectives()`. Wire the `/objectives/propose` endpoint. The agent can now suggest its own goals.

Deliverables:
- `propose_objectives()` in `objectives.py`
- `OBJECTIVE_PROPOSE_SYSTEM` prompt
- `/objectives/propose` endpoint
- Tests for proposal generation

## Open Questions

1. **Who decides completion?** The agent can assess progress, but should it be allowed to mark an objective as `completed` autonomously, or should that require user confirmation?

2. **Objective count.** How many active objectives should influence drafting? Too many dilutes focus. A cap of 5-7 active objectives may be practical, with excess going to `paused`.

3. **Priority management.** Should the agent be allowed to re-prioritize objectives based on its own assessment, or is priority strictly user-controlled?

4. **Objective-memory feedback.** When a progress scan finds no relevant memories, should the agent be nudged to generate content toward that objective? That crosses from passive awareness into active pursuit.

5. **Relationship to topics.** Objectives and topics will often overlap ("explore agent epistemology" as both a topic summary and an objective). Should objectives be explicitly linked to topics, or is the semantic overlap via ChromaDB retrieval sufficient?
