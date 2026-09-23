# A RAVL loop — the mental model

> How to reason about a loop: what it is, where it sits on the determinism gradient,
> how it learns, whom it trusts, and who owns it. Read this before writing a loop,
> reading one's learnings, or changing the library.

## The four phases

```
REFLECT ──► ACT ──► VERIFY ──► LEARN
 observe     do      check      steer
```

| Phase | Does | Must not |
|---|---|---|
| **Reflect** | Gather the current state of the world, the resource inventory for this run, and every piece of *steer* addressed to this loop. Synthesise them into context. | Decide or act. |
| **Act** | Apply bounded agency toward the intent — by a model acting directly, by crystallised code, or a mix. Produce the **effect**. | Re-gather, verify, or learn. |
| **Verify** | Judge the effect against the owner's criteria. Judge *domain* quality only; the run trace already knows whether the machinery worked. | Take new actions or update anything. |
| **Learn** | Attribute what happened, decide whether the loop moves on the gradient, and write **steer** for named readers. | Act, re-analyse the world, or write outside its own loop. |

One run = one pass through the four phases. Nothing loops back inside a run.

## Axioms

### A1 — A loop is a purpose with a verifier, developed by running it

The owner holds two things: the **intent** (what good looks like) and the
**verifier** (how we would know). Everything else — structure, code, strategy — is
derived from those two and can be thrown away and re-derived.

The spec is grown, not written once. Run on bare intent; see where it drifts; sharpen
the intent, add a verification; run again — until it passes consistently. This is
red–green–refactor in plain language. The library's job is to make each turn of that
cycle fast and to show the owner clearly what it understood.

The owner may be a human or a tool-using agent. Nothing below distinguishes them.

### A2 — Position on the determinism gradient is learned and declarable

```
 agentic ─────────────────────────────────────────► crystallised
 a model acts directly                               generated code runs; no model
 slow · costly · adaptive · non-deterministic         fast · cheap · rigid · deterministic
```

Every loop is somewhere on this line, and moves:

- **Rightward** (crystallise) when Verify keeps passing, the procedure is repeatable,
  and the agentic path costs more than the outcome warrants.
- **Leftward** (de-crystallise) when Verify fails on crystallised code *and* the fault is
  attributed to the solution, not the world. A model re-enters and re-derives.

The owner may **pin** the position at either end:

- `lock` — "I got the outcome I wanted; do exactly this." A legitimate answer even when
  the intent was under-specified: the outcome was right, and that is what is kept.
- `never-lock` — the purpose is inherently non-repeatable; judgement is required every
  run.

A declaration always overrides an inference. Crystallisation is a *learned property* of
the loop that the owner can overrule, not a manual mode.

### A3 — One attempt per run

The loop is the smallest possible observe → act → check → learn cycle, so that feedback
is immediate and every failure is visible as a failure. There is no internal retry.

Longer behaviour is composition: a loop's Act may invoke other loops. A loop is a tool
that long-running agents call, not a long-running process. A group of loops (see A7)
may exhibit long-running behaviour collectively; no single loop does.

### A4 — Two kinds of knowledge, never mixed

| | Domain learning (problem space) | Execution learning (solution space) |
|---|---|---|
| **About** | What is true of the task and its world | What makes the machinery of *this loop* work |
| **Example** | "Fixture data lags the match by ~6h" | "This package is published as `scikit-learn`, not `sklearn`" |
| **Written by** | Learn, from Verify's judgement | Learn, from the run trace |
| **Read by** | Reflect, to shape context for Act | The generation contract, as a **constraint** |

Execution learnings are constraints injected into how the next Act is derived, not
hints offered to a prompt. A known answer that is not enforced is a failure of the
library, not of the model.

Both kinds are recorded as context alongside the loop by default; configuration may
relocate them. They are never stored in the same file.

### A5 — The core knows nothing of its environment; each run knows its resources

The library never names a knowledge store, an organisation, a host or an agent runtime.
**Surfaces** (a CLI, an agent skill, a tool-call) and **resources** (files, APIs, a
memory system reached over MCP) are derivatives on the boundary of the core, handed in
at run time.

Each run receives a **resource inventory** and reasons over it — including whether a
resource not yet used might improve the result. Resource relevance is itself learned:
an agentic run considers every resource in the inventory; as the loop crystallises,
Learn records which resources actually contributed and the crystallised code binds only
to those. Crystallisation is subtraction. A loop that fetches a sports score does not
consult a memory system on every run because it once learned that doing so added nothing.

### A6 — Three write channels; only Learn writes meaning

| Channel | Written by | Content | Purpose |
|---|---|---|---|
| **Effect** | Act | The loop's actual purpose — the file, the report, the API call | The reason the loop exists |
| **Trace** | The runtime, every phase | Raw record of what happened, including partial state on stall or crash; the **cost ledger** | Audit and forensics |
| **Steer** | Learn only | Synthesised guidance, each item addressed to a specific reader | The next run's context |

The trace is what survives a crash. A run that dies in Act still leaves "attempt 7 died
here, doing this" for the next Reflect. Learn is the only phase permitted to say what a
run *means*.

Steer has three addressees:

| Addressee | Learn leaves | Which answers |
|---|---|---|
| **This loop's next Reflect** | Attribution, gradient move, resource relevance, sharpened focus | "What do I do differently this time?" |
| **The parent's Reflect** | Outcome summary and open questions for the owner | "Is this child healthy; what does it need from me?" |
| **Siblings' Reflect** | Domain patterns tagged portable vs local | "Does something learned over there apply here?" |

Two rules inside A6:

- **Attribution before adjustment.** Every failure is classed **world** (API down, data
  absent, transient) or **solution** (approach wrong) before any gradient move. World
  failures never de-crystallise. Solution failures on crystallised code pull left.
  Solution failures on agentic runs sharpen the spec — and raise a question for the owner
  if the ambiguity is theirs to resolve.
- **Steer is small and addressed.** Raw artefacts stay in the trace. What flows forward
  reads like "priority: X; avoid: Y; resource Z was irrelevant" — never five failure logs.

### A7 — Learning topology is inferred from placement

```
parent/
  ravl_loop.md            reads: own + descendants' steer
  child_a/  ravl_loop.md  reads: own + siblings' (child_b) steer
  child_b/  ravl_loop.md  reads: own + siblings' (child_a) steer
```

- **Write:** self only, always.
- **Read:** sideways (siblings — loops sharing a parent directory) and down
  (descendants). **Never up.**
- Reading siblings is expected, not merely permitted: sibling steer is an input to
  Reflect.

Because trust is placement, two groups that must never inform each other are never
placed under a common parent, and the core needs no vocabulary for who they are.

**How a parent influences a child.** Steer never flows down. A parent that learns
something its children should know acts as their **owner**: on its next Act it edits
the children's *specification* (intent or verifier). Development flows down;
evidence flows up. This is the default; a deployment may switch it off.

This topology is what allows a group of loops to behave like a school: each reacts to
its neighbours' steer, none has a global view, and coherence is emergent.

### A8 — Every loop has exactly one owner

The owner is whoever holds the intent and verifier. It is inferred from placement: a
loop under a parent directory is owned by that parent loop; a root loop is owned by
whoever runs it (a human or an agent). No registry, no config field.

Only the owner may: change intent or verifier; pin the gradient (`lock`, `never-lock`);
decompose or merge; retire. The loop's role in all of these is to **propose**, as
questions addressed to its owner. A parent loop, being an agent, may decide at once; a
human decides on their own cadence. Same mechanism, different latency.

A consequence: a group of loops cannot restructure itself from the bottom. Leaves
propose, parents decide, and the root's owner decides for the root.

## The decision framework

The questions a loop asks itself, in the order it asks them.

### On every run, Reflect asks

1. **Where am I on the gradient, and was that declared or learned?** Declared wins.
2. **What steer is addressed to me?** Own last Learn; siblings'; descendants'. Nothing
   from above.
3. **What is in this run's resource inventory, and which resources have past runs
   actually used?** Agentic → consider all. Crystallised → the bound set only.
4. **Did the last run complete?** A stall or crash in the trace is the first fact of
   this run, not a gap in learning.

### After Verify, Learn asks — in order, skipping nothing

5. **Did the run complete, and did the effect happen?** From the trace. A crash is an
   execution fact before it is anything else.
6. **Did Verify pass?** If there is no verifier yet, say so: this is a red-phase loop
   still being grown (A1), not an unhealthy one.
7. **If not — world or solution?** Attribution first (A6). World → record; no move.
   Solution → continue.
8. **If solution — is the fault in the spec or in the derivation?** Ambiguous intent →
   raise a question to the owner; no move. Wrong derivation → pull left; a model
   re-derives next run.
9. **If passed — is this loop repeatable enough to move right?** Four signals:
   consecutive passes; run-to-run variance of the *effect* for like inputs; stability of
   the inputs between runs; and **cost of the agentic path** (tokens by model, latency,
   network calls, compute). Data may vary while the procedure does not — crystallise the
   procedure, not the answer.
10. **Should this loop never lock?** If repeatability fails to converge over many runs,
    propose `never-lock` to the owner rather than trying forever.
11. **Which resources contributed?** Mark relevance; crystallisation binds only to these.
12. **Is this loop two loops?** Signals: one part converges right while another stays
    left; verification criteria that fail independently of one another. Propose a split
    to the owner. Never restructure the filesystem.
13. **What here is portable to siblings, and what is local?** Tag before writing steer.
14. **If I have children — does their collective steer imply a spec change?** Then the
    next Act edits their specification (A7). Deployment may disable.

### Questions a loop never asks

- "Should I retry now?" (A3)
- "May I write into that loop's learnings?" (A7)
- "What does the loop above me know?" (A7)
- "Was the domain output good?" — while the run is an execution failure (A4)
- "Should I split myself / lock myself forever?" — it proposes; the owner decides (A8)

## Reading a loop's directory

```
my_loop/
  ravl_loop.md        the owner's intent and verifier — the only thing the owner edits by hand
  config/             declarations: gradient pins, learning-store location, overrides
  learnings/
    domain/           what is true of the task (A4)
    execution/        what makes this loop's machinery work (A4)
    steer/            addressed guidance from the last Learn (A6)
  runs/               one directory per attempt: trace, cost ledger, effect manifest
  child_a/            a child loop — owned by my_loop (A8), reads its siblings (A7)
```

Owner-edited content is at the top. Everything below `learnings/` and `runs/` is the
library's, regenerable, and safe to delete.

## Related

- What this repository is a part of: [`../../purpose.md`](../../purpose.md)
- Where it sits on the stack: [`../../situates.md`](../../situates.md)
- The values behind these axioms: [`../../principles.md`](../../principles.md)
- Decisions that fixed the open forks: [`../../decisions/`](../../decisions/README.md)
