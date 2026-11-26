---
status: Proposed
date: 2026-11-26
deciders: [k@wetware.works]
history:
  - "2026-11-26: Proposed — written by the implementing agent after the owner asked for existing scheduled jobs to become loops that carry their purpose and their implementation, repair themselves within limits, and then come to him; implemented in 0.2.0; not yet reviewed by the decider"
---

# Decision Record 0017: A specification may carry its implementation; repair is bounded, then the owner decides

## Context

Most recurring work already exists as a script that something runs on a schedule. The
script has no stated purpose and no test of its result, so when it stops producing the
outcome nothing notices, and when it is noticed a person repairs it. Making such a job a
loop should not require discarding the script and waiting for an LLM to re-derive it,
and it should not add a second loop beside the job to watch it.

The model allows the specification to contain code (A1) and names `ravl.py` as the form.
`ravl.py` is not built, and the existing implementations are shell scripts.

## Decision

1. `ravl.md` may have an **Act** section holding a fenced `act` block: a shell script
   that is the owner's implementation of Act. A loop with one starts code-driven.
2. **The implementation runs on every run in which no repair attempt is due.** No LLM
   is called while it meets the verifier. A loop that must do its work on every run
   says so with a criterion that Act completed in this run; the runtime writes the file
   `act-ok` in the run directory when Act finishes without error, for a check to test.
3. **When the implementation stops meeting the verifier, Learn classifies the failure
   once.** A world failure changes nothing: the implementation keeps running on every
   run. A solution failure makes the next Act an LLM-driven repair attempt. A repeat of
   the same failure of code (same failing criteria, same exit status) reuses the
   earlier classification and calls no LLM.
4. **A repair attempt** is given the specification, the implementation's last output and
   the attempt number. It repairs the cause within what its owner permits, then runs
   the implementation so that the run produces the outcome. It may not edit the Act
   block; a change to it is proposed to the owner.
5. **When a repair attempt passes Verify, the implementation is Act again** on the next
   run. No code is generated over an owner's implementation.
6. **After `learn.max_repair_attempts` failed attempts on one failing condition
   (default 2), the loop holds and the owner is asked.** While it holds, the
   implementation still runs on every run. That is how the loop finds out that the
   cause was removed; it then clears the hold and closes the question without the
   owner having to answer.
7. **No failure stays unreported.** A loop that has failed for `learn.escalate_hours`
   (default 24) with no question open for its condition, whatever the classification,
   writes one.
8. Learn's LLM call counts against the same rolling budget as Act's. When the budget is
   spent, the failure is recorded unclassified and the owner is asked.

## Alternatives considered

| Option | Why not |
|---|---|
| Keep the job as it is and add a separate loop that checks its outcome | Two things per outcome: the job, and its watcher. The purpose sits in one place and the implementation in another, and the watcher needs its own schedule. |
| Convert the job to a bare intent and let an LLM re-derive the code | Discards an implementation that works, spends LLM calls to recover it, and puts generated code where the owner's code was. |
| Let the repair attempt rewrite the Act block | The implementation is part of the specification, which only the owner changes (A8). |
| Unlimited repair attempts within the budget | The owner hears nothing until a budget runs out, and the same failed repair is paid for repeatedly. |
| **Chosen: implementation in the specification; classify once; bounded repair; then the owner** | The job, its purpose and its test are one directory. A healthy run costs what the job cost before, plus the checks. |

## Consequences

- Converting a scheduled job is: write the intent and verifier, put the command the
  scheduler ran into the Act block, and point the scheduler at `ravl run`.
- A script the Act block calls is outside the specification. Whether a repair attempt
  may change it is for the owner's configuration of the LLM command to permit or deny,
  as with anything else the agent can reach.
- `ravl.py` remains unbuilt. If it is built, an `act` block and `ravl.py` are two ways
  to state the same thing and one should be retired.
- A wrong "world" classification leaves a broken implementation running unrepaired
  until `escalate_hours` passes; the owner is then asked. This is the cost of not
  starting a repair on every transient failure.

## Related

- `0002-execution-mode-learned-and-owner-settable`
- `0005-structural-change-is-proposed-by-loop-decided-by-owner`
- `0015-reflect-runs-the-verifier-and-act-is-skipped-when-the-outcome-holds`
- `0016-learn-may-hold-the-next-act-and-asks-the-owner-once-per-condition`
