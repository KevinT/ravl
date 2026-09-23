# A RAVL loop — the mental model

> How to reason about a loop: what it is, how it moves between LLM-driven and
> code-driven execution, how it learns, which other loops it may read, and who owns it.
> Read this before writing a loop, reading a loop's learnings, or changing the library.

## The four phases

```
REFLECT ──► ACT ──► VERIFY ──► LEARN
```

| Phase | Does | Does not |
|---|---|---|
| **Reflect** | Reads the current state of the world, the resource inventory for this run, and every steer entry addressed to this loop. Produces the context for Act. | Decide or act. |
| **Act** | Performs the work described by the intent, either by an LLM acting directly, by generated code, or by a combination. Produces the **effect**. | Re-read the world, verify, or learn. |
| **Verify** | Compares the effect against the owner's criteria. Judges domain quality only. Whether the machinery worked is already recorded in the trace. | Take new actions or update anything. |
| **Learn** | Classifies what happened, decides whether the loop's execution mode changes, and writes **steer** for named readers. | Act, re-analyse the world, or write outside its own loop directory. |

One run is one pass through the four phases. There is no branch back to an earlier
phase inside a run.

## Axioms

### A1 — A loop is an intent plus a verifier, and is developed by running it

The owner holds two things: the **intent** (a description of the wanted outcome) and
the **verifier** (the criteria that decide whether the outcome was achieved).
Everything else — structure, generated code, strategy — is derived from those two and
can be deleted and re-derived.

The specification is developed incrementally. The owner runs the loop on a bare intent,
reads the result, sharpens the intent or adds a verification criterion, and runs again,
until the loop passes consistently. This is the red–green–refactor cycle applied to a
plain-language specification. The library's job is to make each cycle fast and to show
the owner what it understood from the specification.

The owner may be a human or an LLM-driven agent. Nothing below distinguishes them.

### A2 — Execution mode is learned, and the owner may fix it

Each loop has an **execution mode** on a scale from *LLM-driven* to *code-driven*:

```
 LLM-driven ─────────────────────────────────────► code-driven
 an LLM performs Act directly                       generated code performs Act; no LLM call
 slow, costly, adaptive, non-deterministic          fast, cheap, fixed, deterministic
```

Learn moves the loop along this scale:

- **Toward code-driven** when Verify has passed on consecutive runs, the procedure is
  the same from run to run, and the LLM-driven path costs more than the outcome
  justifies. Learn generates code that performs Act.
- **Toward LLM-driven** when Verify fails on generated code and Learn attributes the
  failure to the solution rather than to the external world. An LLM performs the next
  Act and new code may be generated from it.

The owner may set the mode explicitly:

- `lock` — run the current generated code unchanged every time. This is a valid choice
  when an LLM-driven run produced the wanted outcome but the intent was not specific
  enough to reproduce it reliably.
- `never-lock` — always perform Act with an LLM, because the task requires judgement on
  every run.

An explicit setting always overrides the learned mode.

### A3 — One attempt per run

A run performs each phase once and stops. There is no retry, backoff or repeat inside a
run. A failed run is recorded and becomes input to the next run. This keeps each
failure visible as a failure, and keeps the delay between an action and its feedback as
short as possible.

Longer-running behaviour is built by composition: a loop's Act may invoke other loops.
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
core. **Resources** (files, APIs, a memory system reached over MCP) are passed to a run
as an inventory by the surface that invoked it.

Reflect reads the inventory and may use any resource in it, including one that earlier
runs did not use. Learn records which resources contributed to a passing run. When the
loop becomes code-driven, the generated code uses only the resources that contributed.
This is how a loop that fetches a sports score stops consulting a memory system on
every run: an earlier run recorded that the memory system contributed nothing.

### A6 — Three write channels

| Channel | Written by | Content | Purpose |
|---|---|---|---|
| **Effect** | Act | The loop's output: a file, a report, an API call | The reason the loop exists |
| **Trace** | The runtime, in every phase | A record of what happened, including partial state if a phase stalled or crashed, and the **cost ledger** for the run | Audit and diagnosis |
| **Steer** | Learn only | Guidance for the next run, each entry addressed to a named reader | Input to the next Reflect |

The trace is written incrementally, so a run that crashes during Act still leaves a
record of where it crashed and what it was doing. Learn is the only phase that writes
interpretation.

Steer entries have three possible addressees:

| Addressee | Content | Question it answers for the reader |
|---|---|---|
| **This loop's next Reflect** | Failure classification, mode change, resource relevance, what to focus on | What to do differently on this run |
| **The parent loop's Reflect** | Outcome summary and open questions for the owner | Whether this child needs an owner decision |
| **Sibling loops' Reflect** | Domain patterns tagged as portable or local | Whether a pattern learned elsewhere applies here |

Two rules apply inside Learn:

- **Classify the failure before changing anything.** Every failure is classified as
  **world** (external service down, data absent, transient error) or **solution** (the
  approach was wrong). World failures do not change the execution mode. Solution
  failures on generated code move the loop toward LLM-driven. Solution failures on an
  LLM-driven run sharpen the specification, and produce a question for the owner when
  the ambiguity is in the intent.
- **Steer is short and addressed.** Raw output stays in the trace. Steer states what to
  prioritise, what to avoid, and which resources were irrelevant.

### A7 — Which loops may read each other is determined by directory placement

```
parent/
  ravl_loop.md            reads steer from: itself, all descendants
  child_a/  ravl_loop.md  reads steer from: itself, child_b
  child_b/  ravl_loop.md  reads steer from: itself, child_a
```

- **Write:** a loop writes learnings only into its own directory.
- **Read:** a loop reads learnings from its siblings (loops sharing its parent
  directory) and from its descendants. It does not read from any ancestor.
- Sibling steer is an input to Reflect, not an optional extra.

Two groups of loops that must not inform each other are placed so that they share no
parent directory. The core does not need to know what the groups are.

**How a parent influences its children.** Steer does not flow from parent to child. A
parent that learns something its children should act on edits the children's
specification (intent or verifier) during its next Act, in the same way a human owner
would. This behaviour is on by default and can be disabled in configuration.

This arrangement lets a set of loops coordinate without any loop having a view of the
whole set: each reacts to the steer of its siblings and descendants only.

### A8 — Every loop has exactly one owner

The owner is whoever holds the loop's intent and verifier. Ownership is determined by
placement: a loop inside a parent loop's directory is owned by that parent; a root loop
is owned by whoever runs it, human or agent. There is no owner field and no registry.

Only the owner may: change the intent or verifier; set `lock` or `never-lock`; split
or merge the loop; retire it. For each of these the loop's role is to **propose**, as a
question in its steer addressed to the owner. It never applies the change to itself.

A parent loop, being an agent, may act on a proposal at its next Act. A human acts when
they choose. The mechanism is the same; only the delay differs.

## The decision framework

The questions a loop evaluates, in order.

### On every run, Reflect evaluates

1. **What is the execution mode, and was it set by the owner or learned?** An owner
   setting wins.
2. **Which steer entries are addressed to me?** From this loop's last Learn, from
   siblings, from descendants. None from ancestors.
3. **What is in this run's resource inventory, and which resources did earlier passing
   runs use?** LLM-driven: consider every resource. Code-driven: use the recorded set.
4. **Did the last run complete?** A stall or crash recorded in the trace is the first
   input to this run.

### After Verify, Learn evaluates, in order, without skipping

5. **Did the run complete, and was the effect produced?** Read from the trace.
6. **Did Verify pass?** If no verifier is defined yet, record that. A loop without a
   verifier is in the red phase of development (A1), not in a failed state.
7. **If Verify failed: world or solution?** World: record it, make no mode change.
   Solution: continue.
8. **If solution: is the fault in the specification or in the derivation?** Ambiguous
   intent: write a question to the owner; make no mode change. Wrong derivation: move
   toward LLM-driven so the next Act re-derives.
9. **If Verify passed: is the loop ready to move toward code-driven?** Four signals:
   the number of consecutive passes; how much the effect varies between runs with
   similar inputs; how much the inputs vary between runs; and the cost of the LLM-driven
   path from the cost ledger (tokens by model, wall time, network calls, compute). Input
   data may vary while the procedure stays the same; in that case generate code for the
   procedure.
10. **Should this loop be `never-lock`?** If repeatability has not converged after many
    runs, propose `never-lock` to the owner instead of continuing to test for it.
11. **Which resources contributed to this run?** Record relevance. Generated code uses
    only these.
12. **Is this one loop or two?** Signals: one part of the work has become repeatable
    while another has not; verification criteria that fail independently of each other.
    Propose a split to the owner. Do not change the directory structure.
13. **Which of this run's domain learnings apply to siblings, and which are local?** Tag
    each before writing steer.
14. **If this loop has children: does their combined steer imply a specification
    change?** If so, the next Act edits the child specification (A7). Deployment may
    disable this.

### Questions a loop does not evaluate

- Whether to retry now (A3).
- Whether to write into another loop's learnings (A7).
- What an ancestor loop has learned (A7).
- Whether the domain output was good, when the run failed for an execution reason (A4).
- Whether to split itself or set its own mode permanently — it proposes, the owner
  decides (A8).

## Reading a loop's directory

```
my_loop/
  ravl_loop.md        intent and verifier; the only file the owner edits by hand
  config/             owner settings: execution mode, learning-store location, overrides
  learnings/
    domain/           facts about the task (A4)
    execution/        constraints on generated code (A4)
    steer/            addressed guidance from the last Learn (A6)
  runs/               one directory per run: trace, cost ledger, list of effects produced
  child_a/            a child loop, owned by my_loop (A8), which reads its siblings (A7)
```

The owner edits `ravl_loop.md` and `config/`. `learnings/` and `runs/` are written by
the library and can be deleted; the loop will rebuild them over subsequent runs.

## Related

- What this repository is a part of: [`../../purpose.md`](../../purpose.md)
- Position on the alignment stack: [`../../situates.md`](../../situates.md)
- The values behind these axioms: [`../../principles.md`](../../principles.md)
- Decision records: [`../../decisions/`](../../decisions/README.md)
