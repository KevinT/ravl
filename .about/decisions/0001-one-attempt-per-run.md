---
status: Accepted
date: 2026-09-23
deciders: [k@wetware.works]
history:
  - 2026-09-23: Accepted — carried from RavlGPT as a fundamental design constraint, reaffirmed
---

# Decision Record 0001: One attempt per run

## Context

Many agent frameworks optimise for running as long as possible, retrying internally
until a goal is met. Internal retries hide failure patterns: the caller sees only the
eventual success, and the framework learns "try again" rather than *why*.

## Decision

A run makes exactly one pass through Reflect → Act → Verify → Learn and stops. There is
no retry, backoff or loop inside a run. A failure is recorded and becomes the next run's
context. A loop is a tool that longer-running processes may call; it is never itself a
long-running process.

Longer behaviour, where wanted, is composition: a loop's Act may invoke other loops,
and a group of loops may exhibit long-running behaviour collectively.

## Alternatives considered

| Option | Why not |
|---|---|
| Bounded internal retry (N attempts) | Every retry that succeeds erases the evidence of the failures before it. |
| Long-running agent with the protocol as an inner loop | Inverts the design: the loop becomes a step, and feedback stops being immediate. |
| **Chosen: one attempt, failures flow forward** | Smallest possible feedback cycle; every failure visible as a failure; learning is global across runs rather than local within one. |

## Consequences

- A newly written loop will often fail its first several runs. That is the intended
  development mode (mental model, A1).
- Any "swarm" or long-running behaviour is a property of composition and the learning
  topology (`0003-trust-is-placement`), not of the run.

## Related

- `0000-rebuild-from-concepts-not-from-code`
