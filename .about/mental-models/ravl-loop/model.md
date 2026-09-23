# A RAVL loop — the mental model

> How to reason about a loop: what it is, how it moves between LLM-driven and
> code-driven execution, how it learns, which other loops it may read, who owns it, and
> how a tree of loops is grown and pruned. Read this before writing a loop, reading a
> loop's learnings, or changing the library.

## Scope

`ravl` is for **outcomes that recur**: a report produced every week, a data feed
ingested every night, a service that must stay up, a state of the world that must be
maintained. Each time the outcome is produced again, the loop that produces it should
cost less and fail less than the time before.

`ravl` is not for one-off tasks. For a task that happens once, an interactive agent that
retries inside a session gets to a result faster. A loop pays for its structure over
repeated runs; a single run does not recover that cost.

## The four phases

```
REFLECT ──► ACT ──► VERIFY ──► LEARN
```

| Phase | Does | Does not |
|---|---|---|
| **Reflect** | Reads the current state of the world, the resource inventory for this run, and every steer entry the loop is permitted to read. Produces the context for Act. | Decide or act. |
| **Act** | Performs the work described by the intent, either by an LLM acting directly, by code, or by a combination. Produces the **effect**. May create, edit or remove child loops. | Re-read the world, verify, or learn. |
| **Verify** | Compares the effect against the owner's criteria. Judges domain quality only. Whether the machinery worked is already recorded in the trace. | Take new actions or update anything. |
| **Learn** | Classifies what happened, decides whether the loop's execution mode changes, and writes **steer**. | Act, re-analyse the world, or write outside its own loop directory. |

One run is one pass through the four phases. There is no branch back to an earlier
phase inside a run.

## Axioms

### A1 — A loop is an intent plus a verifier, optionally with code, and is developed by running it

The owner holds two things: the **intent** (a description of the wanted outcome) and
the **verifier** (the criteria that decide whether the outcome was achieved). The
specification may also contain **code** that performs Act. Everything not in the
specification — generated code, strategy, learnings — is derived and can be deleted
and re-derived.

The specification is developed incrementally. The owner runs the loop on a bare intent,
reads the result, sharpens the intent or adds a verification criterion, and runs again,
until the loop passes consistently. This is the red–green–refactor cycle applied to a
plain-language specification. The library's job is to make each cycle fast and to show
the owner what it understood from the specification.

A specification is one of two files in the loop's directory:

- `ravl.md` — intent and verifier in plain language. Act starts LLM-driven.
- `ravl.py` — code that performs Act, with the intent and verifier as documented
  fields. Act starts code-driven. The owner wrote by hand what Learn would otherwise
  have generated.

Both are run by the same runner and go through the same four phases. A `ravl.py` loop
whose Verify fails for a solution reason is handled exactly like a `ravl.md` loop whose
generated code failed: Learn moves it toward LLM-driven and the next Act re-derives from
the intent. The owner may then accept the re-derived code into `ravl.py` or leave it as
a learned artefact.

The owner may be a human or an LLM-driven agent. Nothing below distinguishes them.

### A2 — Execution mode is learned, and the owner may fix it

Each loop has an **execution mode** on a scale from *LLM-driven* to *code-driven*:

```
 LLM-driven ─────────────────────────────────────► code-driven
 an LLM performs Act directly                       code performs Act; no LLM call
 slow, costly, adaptive, non-deterministic          fast, cheap, fixed, deterministic
```

Learn moves the loop along this scale:

- **Toward code-driven** when Verify has passed on consecutive runs, the procedure is
  the same from run to run, and the LLM-driven path costs more than the outcome
  justifies. Learn generates code that performs Act.
- **Toward LLM-driven** when Verify fails on code and Learn attributes the failure to
  the solution rather than to the external world. An LLM performs the next Act and new
  code may be generated from it.

The owner may set the mode explicitly:

- `lock` — run the current code unchanged every time. This is a valid choice when an
  LLM-driven run produced the wanted outcome but the intent was not specific enough to
  reproduce it reliably.
- `never-lock` — always perform Act with an LLM, because the task requires judgement on
  every run.

An explicit setting always overrides the learned mode.

### A3 — One attempt per run; nothing inside `ravl` starts a run

A run performs each phase once and stops. There is no retry, backoff or repeat inside a
run. A failed run is recorded and becomes input to the next run. This keeps each
failure visible as a failure, and keeps the delay between an action and its feedback as
short as possible.

A run starts only when something outside the library invokes it on a directory: a
scheduler, a human at a terminal, an agent, or a parent loop's Act. The library has no
scheduler, no event system and no trigger. A loop that must respond to a change in the
world, or in a child, is run often enough by its owner to notice the change, or its Act
watches for the change in whatever way its owner specifies. How to watch is part of the
loop's design, and it can be learned like anything else the loop does.

A loop is a tool that a long-running agent can call; it is not itself a long-running
process.

### A4 — Domain knowledge and execution knowledge are stored and used separately

| | Domain learning | Execution learning |
|---|---|---|
| **Concerns** | Facts about the task and its subject matter | Facts about making this loop's machinery work |
| **Example** | "Fixture data is published about six hours after the match" | "The package is published as `scikit-learn`, not `sklearn`" |
| **Written by** | Learn, from Verify's judgement | Learn, from the run trace |
| **Used by** | Reflect, as context for Act | The code-generation step, as a **constraint** that a generated program must satisfy |

Execution learnings are enforced when code is generated. A generated program that
violates a recorded execution constraint is rejected before it runs. Domain learnings
are supplied as context and are not mechanically enforced.

Both kinds are stored beside the loop by default. Configuration may relocate them. They
are never stored in the same file.

### A5 — The core has no knowledge of its environment; each run receives a resource inventory

The library does not name any knowledge store, organisation, host or agent runtime.
**Surfaces** (a command-line tool, an agent skill, a tool-call interface) invoke the
core. **Resources** (files, APIs, a memory system reached over MCP, the learnings of a
loop elsewhere) are passed to a run as an inventory by the surface that invoked it or
named in the specification by the owner.

Reflect reads the inventory and may use any resource in it, including one that earlier
runs did not use. Learn records which resources contributed to a passing run. When the
loop becomes code-driven, the generated code uses only the resources that contributed.
This is how a loop stops consulting a resource that never helps: an earlier run recorded
that it contributed nothing.

### A6 — Three write channels

| Channel | Written by | Content | Purpose |
|---|---|---|---|
| **Effect** | Act | The loop's output: a file, a report, an API call, a change to a child loop | The reason the loop exists |
| **Trace** | The runtime, in every phase | A record of what happened, including partial state if a phase stalled or crashed, and the **cost ledger** for the run | Audit and diagnosis |
| **Steer** | Learn only | Guidance for later runs, each entry addressed to a named reader | Input to a later Reflect |

The trace is written incrementally, so a run that crashes during Act still leaves a
record of where it crashed and what it was doing. Learn is the only phase that writes
interpretation.

Steer entries have three possible addressees:

| Addressee | Content | Question it answers for the reader |
|---|---|---|
| **This loop's next Reflect** | Failure classification, mode change, resource relevance, what to focus on | What to do differently on this run |
| **The owner** | Outcome summary and open questions | Whether this loop needs an owner decision |
| **Sibling loops' Reflect** | Domain patterns tagged as portable or local | Whether a pattern learned elsewhere applies here |

A steer entry addressed to the owner is written into the loop's own directory. The loop
does not know who the owner is or where the owner's files are. The owner reads it.

Two rules apply inside Learn:

- **Classify the failure before changing anything.** Every failure is classified as
  **world** (external service down, data absent, transient error, budget exhausted) or
  **solution** (the approach was wrong). World failures do not change the execution
  mode. Solution failures on code move the loop toward LLM-driven. Solution failures on
  an LLM-driven run sharpen the specification, and produce a question for the owner
  when the ambiguity is in the intent.
- **Steer is short and addressed.** Raw output stays in the trace. Steer states what to
  prioritise, what to avoid, and which resources were irrelevant.

### A7 — What a loop may read is determined by directory placement, measured in hops

```
container/
  ravl.md              reads: itself (hop 0); child_a, child_b (hop 1); their children (hop 2) ...
  child_a/  ravl.md    reads: itself (hop 0); child_b and its own children (hop 1) ...
  child_b/  ravl.md    reads: itself (hop 0); child_a and its own children (hop 1) ...
```

- **Write:** a loop writes learnings only into its own directory.
- **Read:** a loop reads learnings within a **radius** of *n* hops. Hop 0 is its own
  learnings. Hop 1 is its siblings (loops sharing its containing directory) and its
  children. Each further hop goes one directory level deeper. The radius never extends
  above the containing directory: a loop lists its containing directory to find its
  siblings, and reads no `ravl.*` or learnings file in that directory or any directory
  above it.
- **Default radius is 1.** The owner sets it in the loop's `config/`.
- Within its granted radius, a loop **narrows** what it reads by learned relevance (A5):
  a sibling whose learnings never contribute is dropped from Reflect. A loop may not
  **widen** its radius; it proposes widening to its owner as a question (A8).
- Learnings from outside the radius are resources the owner names in the
  specification (A5). They are not topology.

Two groups of loops that must not inform each other are placed so that they share no
containing directory. The core does not need to know what the groups are.

**A loop has no knowledge of its ancestors.** It does not read them, signal them, or
depend on their existence. This is what makes a loop copyable: a loop taken from one
tree, or from a library, works unchanged in another. Everything an ancestor wants a
loop to know is written into the loop's specification, config or budget.

### A8 — Every loop has exactly one owner; the owner grows and prunes the tree

The owner is whoever holds the loop's intent and verifier. Ownership is determined by
placement: a loop inside another loop's directory is owned by that loop; a root loop is
owned by whoever runs it, human or agent. There is no owner field and no registry.

**Only the owner may:** change the intent, verifier or code; set `lock` or
`never-lock`; set the read radius; set the budget; split, merge or retire the loop. For
each of these the loop's role is to **propose**, as a question in its steer. It never
applies the change to itself.

**A loop may create, edit and remove loops in its own directory.** It may not create,
edit or remove itself or anything outside its directory. This is how a tree grows: a
human writes one root loop with an abstract intent and owns it; that loop's Act creates
children with narrower intents and owns them; each child's Act may do the same. Each
loop repairs itself within its own scope. A parent intervenes only when a child's steer
says the child cannot, or when the parent's own Verify shows the children's combined
effect no longer produces the parent's outcome. The parent then edits, splits, merges
or removes children as its Act. This behaviour is on by default and can be disabled in
configuration.

**Before removing a child, a parent absorbs the child's domain learnings** into its
own. Removal then deletes the child's directory. Execution learnings are not absorbed;
they concerned machinery that no longer exists.

A parent loop, being an agent, may act on a child's proposal at its next Act. A human
acts when they choose. The mechanism is the same; only the delay differs.

### A9 — Every loop has a budget, set by its owner, bounded by its owner's budget

Every run records a **cost ledger**: tokens by model, wall time, network calls,
compute. Two budgets are read against it:

| Budget | Scope | When exceeded |
|---|---|---|
| **Per run** | One run of this loop | The run stops. The trace records where. Learn classifies it as a world failure. |
| **Per subtree** | This loop and all its descendants, over a rolling window | The loop may not create children or run LLM-driven until the window moves. Learn writes a question to the owner. |

Budgets have defaults set by the library and are overridden per loop in `config/`. When
a parent creates a child it sets the child's budgets, and a child's budgets may not
exceed the parent's remaining budget. A child never reads its parent's budget; the
parent wrote a number into the child's config and that is all the child sees.

The defaults are deliberately tight and are recalibrated from real loops.

## The decision framework

The questions a loop evaluates, in order.

### On every run, Reflect evaluates

1. **What is the execution mode, and was it set by the owner or learned?** An owner
   setting wins.
2. **What is my budget for this run, and what has this subtree spent in the current
   window?** From `config/` and the cost ledgers.
3. **Which steer entries may I read, within my radius, and which of those have
   contributed before?** From this loop's last Learn, from siblings, from descendants.
   None from ancestors.
4. **What is in this run's resource inventory, and which resources did earlier passing
   runs use?** LLM-driven: consider every resource. Code-driven: use the recorded set.
5. **Did the last run complete?** A stall or crash recorded in the trace is the first
   input to this run.

### After Verify, Learn evaluates, in order, without skipping

6. **Did the run complete, and was the effect produced?** Read from the trace.
7. **Did Verify pass?** If no verifier is defined yet, record that. A loop without a
   verifier is in the red phase of development (A1), not in a failed state.
8. **If Verify failed: world or solution?** World (including budget exhausted): record
   it, make no mode change. Solution: continue.
9. **If solution: is the fault in the specification or in the derivation?** Ambiguous
   intent: write a question to the owner; make no mode change. Wrong derivation: move
   toward LLM-driven so the next Act re-derives.
10. **If Verify passed: is the loop ready to move toward code-driven?** Four signals:
    the number of consecutive passes; how much the effect varies between runs with
    similar inputs; how much the inputs vary between runs; and the cost of the
    LLM-driven path from the cost ledger. Input data may vary while the procedure stays
    the same; in that case generate code for the procedure.
11. **Should this loop be `never-lock`?** If repeatability has not converged after many
    runs, propose `never-lock` to the owner instead of continuing to test for it.
12. **Which resources and which readable learnings contributed to this run?** Record
    relevance. Code uses only these resources. Reflect drops learnings that never
    contribute. If learnings outside the radius would have helped, propose a wider
    radius to the owner.
13. **Is this one loop or two?** Signals: one part of the work has become repeatable
    while another has not; verification criteria that fail independently of each other.
    Propose a split to the owner.
14. **Which of this run's domain learnings apply to siblings, and which are local?** Tag
    each before writing steer.
15. **If this loop has children: does their steer, or my own Verify result, call for a
    change to the children?** Edit a specification, set a budget or radius, split,
    merge, create or remove. This is performed by the next Act. Configuration may
    disable it.

### Questions a loop does not evaluate

- Whether to retry now (A3).
- Whether to run itself or any other loop (A3).
- Whether to write into another loop's learnings (A7).
- What an ancestor loop has learned, spent or decided (A7, A9).
- Whether to widen its own read radius or raise its own budget (A7, A9).
- Whether the domain output was good, when the run failed for an execution reason (A4).
- Whether to split itself or set its own mode permanently — it proposes, the owner
  decides (A8).

## Reading a loop's directory

```
my_loop/
  ravl.md  or  ravl.py  intent and verifier (and code, in .py); the file the owner edits
  config/               owner settings: execution mode, read radius, budgets, overrides
  learnings/
    domain/             facts about the task (A4)
    execution/          constraints on generated code (A4)
    steer/              addressed guidance from the last Learn (A6)
  runs/                 one directory per run: trace, cost ledger, list of effects produced
  child_a/              a child loop, owned by my_loop (A8), which reads its siblings (A7)
```

The owner edits `ravl.md` (or `ravl.py`) and `config/`. `learnings/` and `runs/` are
written by the library and can be deleted; the loop will rebuild them over subsequent
runs. A `ravl.toml` at the root of a tree holds settings for the whole tree (minimum
library version, learning-store location, whether parents may edit children).

## Related

- What this repository is a part of: [`../../purpose.md`](../../purpose.md)
- Position on the alignment stack: [`../../situates.md`](../../situates.md)
- The values behind these axioms: [`../../principles.md`](../../principles.md)
- Decision records: [`../../decisions/`](../../decisions/README.md)
- What to carry from RavlGPT, and what to leave:
  [`../../../specifications/reference/ravlgpt-guardrails.md`](../../../specifications/reference/ravlgpt-guardrails.md)
- The first loop to build: [`../../../specifications/first-loop.md`](../../../specifications/first-loop.md)
