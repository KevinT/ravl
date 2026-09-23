---
status: Accepted
date: 2026-09-23
deciders: [k@wetware.works]
history:
  - 2026-09-23: Accepted — replaces RavlGPT's separate code-generation and manual lock mechanisms with one learned property that the owner can override
---

# Decision Record 0002: Execution mode is learned, and the owner may set it

## Context

RavlGPT had two unrelated mechanisms. Act always attempted to generate Python code,
and a manual `--lock` flag froze a verified attempt so it ran unchanged. Both were
useful. Generated code made a loop deterministic, fast and cheap. Locking fixed the
case where an LLM-driven run produced the wanted outcome but the intent was not
specific enough to reproduce it. Neither mechanism used information from the other,
and neither had a rule for when it should apply.

LLMs with tool use can now perform Act directly. For some loops no LLM call is needed
at all once the procedure is known.

## Decision

1. Each loop has an **execution mode** on a scale from *LLM-driven* (an LLM performs
   Act directly) to *code-driven* (generated code performs Act with no LLM call). A new
   loop starts LLM-driven.
2. **Learn moves the loop toward code-driven** when Verify has passed on consecutive
   runs, the procedure is the same from run to run, and the LLM-driven path costs more
   than the outcome justifies. The generated code uses only the resources that
   contributed to the passing runs.
3. **Learn moves the loop toward LLM-driven** when Verify fails on generated code and
   Learn classifies the failure as a solution failure rather than a world failure. An
   LLM performs the next Act.
4. The owner may set the mode: `lock` (run the current generated code unchanged) or
   `never-lock` (always use an LLM). An owner setting overrides the learned mode.
5. Every run records a **cost ledger**: tokens by model, wall time, network calls,
   compute. The decision in point 2 uses these figures.

## Alternatives considered

| Option | Why not |
|---|---|
| Always generate code (RavlGPT) | Requires code to be derived before the intent is understood, and does not use the LLM's ability to act directly. |
| Never generate code | Loses determinism, speed and cost savings on repeatable work. |
| Manual lock only | Requires the owner to judge when to lock on every loop; the signals in point 2 are available to the library. |
| **Chosen: learned mode, owner-settable** | Repeatable loops become code-driven without owner action; the owner retains control; two mechanisms become one property. |

## Consequences

- For a repeatable loop, `lock` is the state Learn arrives at on its own. For an
  under-specified loop, `lock` is a manual setting the owner applies.
- A loop whose repeatability does not converge is proposed as `never-lock` to the owner
  (`0005-structural-change-is-proposed-by-loop-decided-by-owner`).
- Failure classification (world or solution) is a required step in Learn.

## Related

- `0000-rebuild-from-concepts-not-from-code`
- `0005-structural-change-is-proposed-by-loop-decided-by-owner`
- `0007-execution-learnings-are-generation-constraints`
