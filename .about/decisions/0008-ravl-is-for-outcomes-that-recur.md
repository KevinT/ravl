---
status: Accepted
date: 2026-09-23
deciders: [k@wetware.works]
history:
  - 2026-09-23: Accepted — narrows scope from "any task" to outcomes that recur, after assessing ravl against interactive agents, agent memory and multi-agent frameworks
---

# Decision Record 0008: `ravl` is for outcomes that recur

## Context

RavlGPT was presented as a general way to run any task from a plain-language spec.
Interactive agents with in-session retry now do one-off tasks faster than a loop can,
because a loop pays for its structure (trace, verifier, learnings) on every run and only
recovers that cost over repeated runs. Agent memory features overlap with a loop's
learnings for one-off work. The capabilities that no agent framework provides are: a
recurring task that becomes cheaper each time it runs, a verifier the owner wrote that
is separate from the actor, and failures that stay visible because nothing retries
them.

## Decision

`ravl` is for outcomes that recur: reports, ingestions, services that must stay up,
states of the world that must be maintained. It is not for one-off tasks, and its
documentation says so. Examples used in the repository are recurring outcomes.

## Alternatives considered

| Option | Why not |
|---|---|
| General-purpose task runner | Competes with interactive agents on their strongest ground and loses. |
| **Chosen: recurring outcomes only** | The three capabilities above all depend on repetition. Stating the scope keeps examples and design decisions on the case where the library has an advantage. |

## Consequences

- The first loop is a recurring one (`specifications/first-loop.md`).
- The LLM-driven to code-driven transition is the kill criterion for the project: if it
  cannot be demonstrated on a simple recurring loop, the advantage over an agent does
  not exist.
- Hand-written maintenance scripts (watchdogs, health checks, repair jobs) are the
  reference class of thing a loop replaces.

## Related

- `0002-execution-mode-learned-and-owner-settable`
- `0001-one-attempt-per-run`
