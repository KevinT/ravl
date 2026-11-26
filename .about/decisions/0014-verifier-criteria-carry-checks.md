---
status: Proposed
date: 2026-11-26
deciders: [kevint@gmail.com]
history:
  - "2026-11-26: Proposed — written by the implementing agent while building the runner (first-loop steps 1 to 8), under the owner's instruction to build; implemented in 0.1.0; not yet reviewed by the decider"
  - "2026-11-26: Point 3 narrowed by 0018-a-loop-with-no-verifier-assumes-one-that-its-parent-edits: a loop with no criteria derives them from the intent on its first run, and records no-verifier only when that derivation does not succeed"
---

# Decision Record 0014: Verifier criteria carry checks, and only checks are verified

## Context

The model says the verifier is the owner's criteria in plain language (A1) and that
Verify compares the effect against them. It did not say how a plain-language criterion
is evaluated. The first loop requires a verifier that "can be checked without an LLM",
and a loop that maintains a service has to be able to report its state when no LLM is
reachable.

## Decision

1. The Verifier section of `ravl.md` is a list of criteria, one per bullet, in plain
   language. A criterion may carry a fenced `check` block: a shell script run from the
   loop directory. Exit status 0 passes the criterion; any other status or a timeout
   fails it.
2. Verify runs the checks and nothing else. No LLM takes part in Verify.
3. A criterion with no check is recorded as `unchecked`. It neither passes nor fails,
   and the owner's steer lists it. A loop in which no criterion has a check has no
   verifier: its runs record `no-verifier` and ask the owner for one. This is the red
   phase of A1, not a failure.
4. A check's output is kept in the trace as evidence and is what Act is shown for a
   failing criterion.
5. A criterion is identified by its text, not its position, so reordering criteria does
   not change the identity of a failing condition.
6. Checks receive `RAVL_LOOP_DIR`, `RAVL_RUN_DIR`, `RAVL_RUN_ID`, `RAVL_RUN_STARTED` and
   `RAVL_PHASE`. The file `started` in the run directory is written when the run starts,
   so a check can test that a file was written during this run.

## Alternatives considered

| Option | Why not |
|---|---|
| An LLM judges each plain-language criterion | Verify would cost a call on every run, would vary between runs, and would fail when the LLM is unavailable, which is one of the conditions a maintenance loop exists to report. No loop that is run needs it yet (principle 2). |
| A separate verifier program beside `ravl.md` | Splits the owner's specification over two files; the criterion and the test that decides it drift apart. |
| **Chosen: plain-language criterion with an optional check beneath it** | One file; the criterion states what is wanted and the check states how it is decided. |

## Consequences

- An owner who can state a criterion but not yet a check can run the loop and see the
  criterion reported as unchecked.
- A check is code the owner wrote and is run without review by the library. It is part
  of the specification and is covered by the rule that only the owner edits it.
- Criteria that need judgement are not served. If a loop that is run needs one, an
  LLM-judged criterion is specified then, as a separate decision.

## Related

- `0001-one-attempt-per-run`
- `0005-structural-change-is-proposed-by-loop-decided-by-owner`
