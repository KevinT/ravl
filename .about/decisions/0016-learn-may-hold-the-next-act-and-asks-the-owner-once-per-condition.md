---
status: Proposed
date: 2026-11-26
deciders: [k@wetware.works]
history:
  - "2026-11-26: Proposed — written by the implementing agent while building the runner (first-loop steps 1 to 8), under the owner's instruction to build; implemented in 0.1.0; not yet reviewed by the decider"
---

# Decision Record 0016: Learn may hold the next Act, and asks the owner once per failing condition

## Context

[`0001-one-attempt-per-run`](0001-one-attempt-per-run.md) makes a failed run the input to
the next. A loop that is run on a schedule and fails for a reason only its owner can
remove (an expired credential, a decision) would otherwise have an LLM attempt the same
repair on every run and write the same question each time. The model gives Learn the
steer to the next Reflect ("what to do differently on this run") and the per-subtree
budget, but named no mechanism for "do not attempt again yet".

## Decision

1. The identity of a failing condition is the set of failing criteria. Check output,
   times and counts are not part of it.
2. When Learn classifies a failure it may set a **hold**: the next runs perform no Act
   while the same condition persists. A hold is set when Learn judges that another
   attempt cannot succeed until the owner acts or the world changes, or when Act itself
   reported that it needs the owner.
3. A hold ends when the set of failing criteria changes, when the owner answers a
   question, when the outcome holds again, or after `learn.hold_hours` (default 24).
   A held run calls no LLM; it records the failure and the classification carried by
   the hold.
4. A question for the owner is recorded once per condition. While a question for a
   condition is open, no second one is written for it. When the outcome holds again,
   or the failing condition changes, the open questions for the old condition are
   closed with the reason.
5. When Act cannot run at all (no LLM command configured, budget spent, mode locked
   with no code), the run is a world failure and the question is written by the library
   without an LLM, naming the failing criteria and the reason.
6. When the LLM is unreachable in both Act and Learn, the failure is recorded as a
   world failure and the question says that the failure could not be classified.

## Alternatives considered

| Option | Why not |
|---|---|
| Attempt Act on every run until the budget is spent | Spends the whole budget on a condition that cannot change, and leaves none for a different failure. |
| Back-off timers inside the library | A second scheduling mechanism; A3 keeps scheduling outside. A hold is a fact in the loop's steer that the next externally started run reads. |
| A new question on every failed run | The owner receives the same text repeatedly and stops reading it. |
| **Chosen: hold keyed on the failing condition; one question per condition** | Detection continues on every run at the cost of the checks; LLM calls and owner attention are spent once per condition. |

## Consequences

- A failure that needs the owner is reported once and then re-attempted once per
  `hold_hours`, so a condition that has silently cleared on the world's side but still
  needs a repair is picked up within that time.
- A loop in a hold still reports `fail` on every run; a surface that lists loops shows
  the hold and the open question.
- Splitting one criterion into two changes the condition identity and re-opens the
  question. This is accepted: the owner changed the verifier.

## Related

- `0001-one-attempt-per-run`
- `0010-loops-create-and-remove-children-within-budget`
- `0015-reflect-runs-the-verifier-and-act-is-skipped-when-the-outcome-holds`
