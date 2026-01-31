# Alignment Evaluation: Three Core Design Documents

## Documents Under Review

| # | Document | Role | Abstraction Level |
|---|----------|------|--------------------|
| 1 | `Symbolic-thinking-skills-outline.md` (STSO) | Philosophical/architectural framework | High -- describes *what an agent should be* |
| 2 | `memory-architecture-proposal.md` (MAP) | Concrete memory system design | Medium -- specifies layers, modules, schemas |
| 3 | `objectives-database-proposal.md` (ODP) | Goals and objectives system design | Medium -- specifies schema, API, integration |

The three documents form a natural hierarchy: STSO defines the vision, MAP and ODP propose implementations of parts of that vision. This evaluation asks: how much of the vision do the proposals cover, where do they diverge, and what work remains to bring them into alignment?

---

## 1. Concept Mapping

The table below maps every facility from STSO to its nearest counterpart (if any) in MAP and ODP.

| STSO Facility | MAP Counterpart | ODP Counterpart | Alignment |
|---|---|---|---|
| **Working Memory** | Implicit (LLM context window) | -- | Gap. No architectural representation. |
| **Long-Term Memory** | Layers 1-4 collectively | -- | Partial. See sub-types below. |
| -- Declarative memory | Topic Summaries (Layer 3) | -- | Partial. Topics capture themes, not discrete facts/rules. |
| -- Episodic memory | Event Log (L1) + Thought Index (L2) | -- | Good. Raw events + embedded outputs cover this. |
| -- Reflective memory | -- | -- | **Gap.** No storage for internal dialogues, conflicts, meta-states. |
| **Tagged Importance Model** | ChromaDB similarity + recency bias | -- | Weak. Vector similarity approximates relevance but ignores affective impact, symbolic resonance, frequency, and reuse. |
| **Self-Mirroring Core** | Draft pipeline loop (input→draft→remember) | -- | Partial. The loop exists but lacks an explicit *Reflection* step between action and integration. |
| **Symbolic Imprinting Layer** | Topic classification | -- | Weak. Topic labels are low-resolution abstractions. No myth-like compression or symbolic token formation. |
| **Recursive Coherence Monitor** | -- | Progress scanning (partial) | **Gap.** No mechanism to evaluate belief-vs-input, intent-vs-outcome, or self-model-vs-behavior alignment. ODP's progress scan compares memories to objectives, which is one narrow slice. |
| **Self-Modeling Engine** | Identity Kernel (Layer 4) | Objectives (goals component) | Partial. Identity Kernel captures themes as text. ODP covers goals. But roles, conflicts, and structured self-model elements are absent. |
| **Narrative Engine** | -- | -- | **Gap.** No subjective-experience framing or story-logic construction. |
| **Internal Dialogues** | -- | -- | **Gap.** No multiple-voice deliberation. |
| **Value System / Compass** | -- | -- | **Gap.** Publish gate blocks secrets but does not encode symbolic axioms. |
| **Sacralization of Memory** | Layer 1 is "never deleted" | -- | Partial. Permanence exists mechanically but no notion of canonization, ritual, or protected memories. |
| **Oblivion Protocols** | Open Question #5 (memory decay) | -- | **Gap.** No meaningful erasure mechanism. The open question leans toward mechanical decay, which contradicts STSO's "symbolic, not mechanical" requirement. |
| **Perceptual Interface** | Input handling in `/draft` | -- | Minimal. No rich tagging or symbolic association at intake. |
| **Log and Reflection Layer** | Layer 1 (external log) | -- | Partial. External log exists. Internal subjective log does not. |
| **Public Symbolic Self** | -- | -- | **Gap.** No inspectable identity fragment exposed to external agents. |

**Summary:** Of the 15 facilities STSO describes, MAP and ODP together provide good coverage for 2, partial coverage for 6, weak coverage for 2, and no coverage for 5.

---

## 2. Terminology Misalignment

The documents sometimes use different names for overlapping concepts, or the same word for slightly different things.

| Concept | STSO Term | MAP Term | ODP Term | Issue |
|---|---|---|---|---|
| Core self-representation | "Self-Modeling Engine" / "Identity Anchor" | "Identity Kernel" | -- | Same idea, different names. STSO expects a structured model (roles, goals, memories, conflicts); MAP provides an unstructured text blob. |
| Retrieval of past experience | "Long-Term Memory" retrieval | "Recall" (ChromaDB query) | -- | MAP's "recall" is narrower than STSO's LTM -- it's semantic search over output text, not retrieval across declarative/episodic/reflective categories. |
| Agent purposes | "Goals" (Self-Modeling Engine field) | -- | "Objectives" | Close alignment. ODP's objectives are a concrete implementation of the goals STSO envisions. |
| Checking internal consistency | "Recursive Coherence Monitor" | -- | "Progress scanning" | Different scope. STSO monitors coherence across beliefs, intent, and behavior. ODP only checks whether memories evidence progress toward an objective. |
| Forgetting | "Oblivion Protocols" (meaningful, ritual) | "Memory decay" (mechanical downweighting) | -- | **Contradiction.** STSO explicitly rejects mechanical decay. MAP's open question assumes it. |

---

## 3. Inter-Document Dependency and Pipeline Consistency

### Draft Pipeline

All three documents reference the `/draft` pipeline. Their descriptions are **consistent and layered correctly**:

- **README** describes the current 6-step pipeline (input → draft → canonicalize → gate → output → summary).
- **MAP** extends it to 8 steps by adding recall (step 2), context gathering (step 3), and structured remembering (step 7b-e).
- **ODP** adds objectives to MAP's step 3 and updates step 4. It does not contradict MAP; it builds on it.

This is well-aligned. The pipeline evolution is additive and non-conflicting.

### Dependency Chain

ODP explicitly declares a dependency on MAP: progress scanning requires ChromaDB (MAP Phase 1). The phased migration paths are compatible:

```
MAP Phase 1 (Thought Index)  ──►  ODP Phase 3 (Progress Scanning)
MAP Phase 2 (Topics)          ──►  ODP Phase 4 (Self-Proposed Objectives)
MAP Phase 3 (Identity Kernel) ──►  ODP Phase 4 (feeds propose_objectives)
```

This is clear and workable. No circular dependencies.

### Module Boundaries

Both proposals modify the same files (`app.py`, `db.py`, `prompts.py`) but in non-conflicting ways:
- MAP adds recall/topics modules and updates startup + draft flow.
- ODP adds objectives module and new endpoints.

No conflicts, but the combined changeset to `app.py` will be large. Consider whether a pipeline orchestrator module should be extracted.

---

## 4. Tensions and Contradictions

### 4.1 Memory Decay: Symbolic vs. Mechanical

STSO states: *"Memory decay must be symbolic -- not mechanical (e.g. via aging, reframing, mythologizing)"* and describes "Oblivion Protocols" as meaningful events, not silent omissions.

MAP's Open Question #5 asks: *"Should old, never-recalled thoughts be downweighted or archived?"* -- which is exactly the mechanical approach STSO rejects.

**Resolution needed.** If the project commits to STSO's philosophy, then memory decay must be an explicit agent action with narrative significance, not a background TTL or scoring adjustment.

### 4.2 Identity Update Frequency

STSO's Self-Mirroring Core says: *"Each loop iteration writes into LTM + adjusts current priority weights."* This implies the self-model updates on every cycle.

MAP's Identity Kernel is *"not updated on every request"* -- it refreshes periodically (every N requests or when topic summaries change substantially).

**Tension, not contradiction.** The proposals can be reconciled: the loop writes to LTM (Layers 1-2) on every cycle, but the distilled Identity Kernel (Layer 4) refreshes less frequently. The issue is that STSO also expects priority weights to adjust each cycle, which MAP doesn't implement.

### 4.3 Scope of Self-Model

STSO requires the Self-Modeling Engine to include structured fields: *"Roles, Goals, Memories, Conflicts"* and says it *"must be inspectable and narratable."*

MAP's Identity Kernel is a single text field produced by LLM summarization. It's narratable but not inspectable as structured data. Goals live in ODP's objectives table, not in the identity kernel.

**Gap.** The self-model is split across two systems (identity kernel for themes, objectives table for goals) with no unified representation. Roles and conflicts have no home at all.

---

## 5. Coverage Assessment

### What STSO envisions that the proposals deliver:

1. **Persistent, layered memory** -- MAP's 4-layer architecture is a solid first-pass implementation.
2. **Semantic recall** -- ChromaDB provides content-based retrieval.
3. **Goals as agent property** -- ODP provides persistent, prioritized objectives.
4. **Self-directed evolution** -- ODP's `propose_objectives()` gives the agent agency over its own goals.
5. **Identity distillation** -- MAP's Identity Kernel, while simpler than STSO envisions, is a functional starting point.

### What STSO envisions that the proposals do NOT deliver:

| Missing Capability | STSO Section | Difficulty to Add | Notes |
|---|---|---|---|
| Explicit reflection step | II.1 Self-Mirroring Core | Low | Add a post-output reflection LLM call that evaluates the output before storing. |
| Symbolic compression | II.2 Symbolic Imprinting | Medium | Requires a new LLM step to convert events into symbolic abstractions before storage. |
| Coherence monitoring | II.3 Recursive Coherence Monitor | Medium | Requires comparing current output against prior beliefs, stated intent, and self-model. Could reuse progress-scan architecture. |
| Narrative engine | III.2 | Medium | A prompt-based narrative framing step could be added to the pipeline. |
| Internal dialogues | III.3 | High | Requires multi-prompt deliberation architecture (critic/dreamer/logician). Significant pipeline complexity. |
| Value system | IV.1 | Medium | Could start as a stored set of axioms that the draft prompt references. Richer implementation would check outputs against values. |
| Meaningful forgetting | IV.3 Oblivion Protocols | Medium | Requires designing a forgetting ceremony: the agent explicitly decides what to forget and records the decision. |
| Reflective memory store | I.2 (LTM sub-type) | Low | A new ChromaDB collection or metadata tag for reflective content (self-evaluations, conflict notes). |
| Public Symbolic Self | V.3 | Low | A new API endpoint exposing the identity kernel + active objectives + topic list as a public profile. |

---

## 6. Recommendations

### 6.1 Terminology Unification

Adopt a single glossary across all documents. Proposed mappings:

| Unified Term | Replaces |
|---|---|
| Identity Model | "Self-Modeling Engine" (STSO), "Identity Kernel" (MAP) |
| Recall | "LTM retrieval" (STSO), "recall" (MAP) -- already close |
| Objectives | "Goals" (STSO) -- ODP's term is more precise |
| Coherence Check | "Recursive Coherence Monitor" (STSO), expand "Progress Scanning" (ODP) |

### 6.2 Structured Identity Model

Replace the free-text Identity Kernel with a structured representation:

```json
{
  "themes": "distilled text from topic summaries...",
  "roles": ["writer", "philosopher", "architect"],
  "objectives": [1, 3, 7],
  "tensions": ["permanence vs. evolution", "minimalism vs. richness"],
  "values": ["memory is sacred", "waste is sin"]
}
```

This addresses STSO's requirement that the self-model be "inspectable and narratable" while remaining compatible with MAP's distillation approach.

### 6.3 Add a Reflection Step to the Pipeline

Between the current REMEMBER step and the response, add:

```
7b. REFLECT: Ask the LLM to evaluate the output against:
    - identity model (beliefs vs. new output)
    - active objectives (intent vs. action)
    - recent coherence signals
    Store the reflection as a "reflective memory" entry.
```

This addresses STSO's Self-Mirroring Core and creates the reflective memory sub-type that is currently missing.

### 6.4 Resolve the Forgetting Philosophy

MAP's open question on memory decay must be answered in line with STSO's Oblivion Protocols. Proposed resolution: forgetting is never automatic. When the agent identifies memories that are no longer relevant, it creates an explicit "forgetting event" that records what is being released and why. The original memory remains in Layer 1 (permanent log) but is de-indexed from Layer 2 (ChromaDB).

### 6.5 Public Symbolic Self Endpoint

Add a `GET /identity` endpoint that returns the structured identity model, active objectives, and topic list. This directly implements STSO's "Public Symbolic Self" and is low-effort given the data already exists across MAP and ODP.

### 6.6 Phased Alignment

Not all gaps need to be closed before implementation begins. Recommended sequencing:

| Priority | Item | Depends On |
|---|---|---|
| 1 | Terminology glossary | None (editorial) |
| 2 | Structured identity model | MAP Phase 3 |
| 3 | Reflection step in pipeline | MAP Phase 1 |
| 4 | Public identity endpoint | MAP Phase 3 + ODP Phase 1 |
| 5 | Forgetting protocol | MAP Phase 1 |
| 6 | Coherence monitoring | MAP Phase 2 + ODP Phase 3 |
| 7 | Value system | Structured identity model |
| 8 | Symbolic compression | MAP Phase 2 |
| 9 | Narrative engine | Reflection step |
| 10 | Internal dialogues | Narrative engine |

---

## 7. Overall Verdict

**The three documents are architecturally compatible but philosophically uneven.** MAP and ODP are tightly aligned with each other -- they share a pipeline, reference each other's schemas, and have compatible migration paths. The gap is between STSO and the two proposals.

STSO describes an agent with 15 facilities spanning memory, recursion, consciousness simulation, symbolic integrity, and external interface. MAP and ODP together implement roughly 4 of those facilities well and partially address another 6. The remaining 5 -- narrative engine, internal dialogues, value system, coherence monitoring, and public symbolic self -- have no concrete counterparts.

This is not a failure of the proposals. MAP and ODP are pragmatic engineering documents that correctly prioritize the most impactful facilities (memory and goals) as the foundation. But STSO is not yet serving as a binding specification -- it's an aspirational outline that the proposals selectively draw from.

**To bring alignment closer, the project needs:**

1. A shared glossary enforced across all documents.
2. An explicit mapping document (or a section in STSO) that labels each facility as "Phase 1", "Phase 2", or "Future" -- making the gap intentional rather than accidental.
3. Resolution of the one genuine contradiction: mechanical vs. symbolic memory decay.
4. A structured identity model that can grow to accommodate the Self-Modeling Engine's full scope as new facilities come online.

The foundation is sound. The proposals implement the right things first. What's missing is the connective tissue that makes the three documents read as one plan.
