---
status: Accepted
date: 2026-09-23
deciders: [k@wetware.works]
history:
  - 2026-09-23: Accepted — after a review of RavlGPT's mission, achievement and code, chose a fresh repository over an in-place refactor
---

# Decision Record 0000: Rebuild from concepts, not from code

## Context

RavlGPT (2025–2026) established the RAVL protocol — Reflect, Act, Verify, Learn — and
a set of durable concepts: one attempt per run, problem-space vs solution-space
learning, owner-owns-intent / system-owns-generated, dependency whitelisting, lockable
loops, known-unknowns surfaced to a human.

Its implementation grew to ~30k lines of framework Python doing work that a capable
model now does from a clear contract: keyword-regex "DSL inference", prompt
deduplication to fit 2025 context windows, several layered execution paths. Its own
last health-check run diagnosed the central failure precisely: an execution learning
was recorded but never enforced on subsequent generation across seven attempts. Test
coverage did not reach the core; the suite was partly failing. Run artefacts and
integration code from a private user of the framework had accumulated inside the
"generic" repository.

## Decision

1. `ravl` is a **new repository**. RavlGPT is kept whole, unchanged, as upstream
   evidence and is linked from `.about/purpose.md`.
2. The concepts are carried over as **agreed documents** — a mental model, principles,
   and these decision records — not as code. No Python is ported. Anything RavlGPT got
   right is re-derived against the model.
3. The core is deliberately small: the phase contract, the learning store and its trust
   topology, the verification harness, and the safety boundaries. Everything a capable
   model can do at run time from a clear contract is not framework code.
4. No content from any private user of RavlGPT — loop names, domain content, run
   artefacts — enters this repository or its history.

## Alternatives considered

| Option | Why not |
|---|---|
| Refactor RavlGPT in place | The test suite does not cover the core, so there is nothing to refactor against. Most of the code is the part to be removed. A change of that size is a rewrite. |
| Branch of RavlGPT | Shares no files with `main`, so gains nothing from branching, but inherits a history containing private-user artefacts and invites reuse of modules that should not survive. |
| Continue RavlGPT under the same name | "GPT" describes a 2023 vendor product, not the thing; the protocol name is the product. |
| **Chosen: new repository, concepts as documents** | The repository history contains no private-user content from the first commit; the core is small; RavlGPT is preserved as evidence. |

## Consequences

- Early `ravl` will do less than RavlGPT did for a while. That is intended.
- Every capability must justify itself against a loop someone actually runs.
- Anyone comparing the two should read RavlGPT's `RAVL_VISION.md` and
  `RAVL_PROTOCOL.md` as the ancestors of `.about/mental-models/ravl-loop/model.md`.

## Related

All other records in this scope depend on this one.
