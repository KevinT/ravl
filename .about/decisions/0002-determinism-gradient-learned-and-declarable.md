---
status: Accepted
date: 2026-09-23
deciders: [k@wetware.works]
history:
  - 2026-09-23: Accepted — replaces RavlGPT's separate code-generation and manual lock mechanisms with a single learned-and-declarable property
---

# Decision Record 0002: Position on the determinism gradient is learned and declarable

## Context

RavlGPT had two separate mechanisms: code generation up front (Act was always an
attempt to produce Python), and a manual `--lock` flag to freeze a verified attempt.
In use, generating code was valuable — it moved a loop from imperative and
non-deterministic to declarative, deterministic, fast and cheap — and locking was
valuable when an agentic run drifted from the wanted outcome because the intent was
under-specified. But neither mechanism knew about the other, and neither knew when it
should apply.

Tool-using models can now perform Act directly. Sometimes a model is not needed at all.

## Decision

1. Every loop has a **position on a gradient** from *agentic* (a model acts directly)
   to *crystallised* (generated code runs with no model). Act begins agentic.
2. **Learn moves the loop rightward** when Verify passes consistently, the procedure is
   repeatable across runs, and the agentic path costs more than the outcome warrants.
   Crystallisation binds only to the resources that actually contributed.
3. **Learn moves the loop leftward** when Verify fails on crystallised code *and* the
   failure is attributed to the solution rather than the world. A model re-enters and
   re-derives.
4. The owner may **pin** the position: `lock` (run exactly this) or `never-lock`
   (judgement is needed every run). A declaration always overrides an inference.
5. Every run records a **cost ledger** — tokens by model, latency, network calls,
   compute — so the case for moving right is made with numbers.

## Alternatives considered

| Option | Why not |
|---|---|
| Always generate code (RavlGPT) | Wastes a capable model's ability to act directly; forces derivation before the intent is understood. |
| Never generate code; always agentic | Forfeits determinism, speed and cost savings on repeatable work; the "self-optimising" effect disappears. |
| Manual lock only | Puts the judgement of *when* on the owner every time; the system can usually infer it. |
| **Chosen: learned position, owner-declarable** | Self-optimising by default; owner control preserved; the two old mechanisms become one property. |

## Consequences

- "Lock" is the natural end-state of learning for repeatable loops, and a valid manual
  answer for under-specified ones.
- Some loops will never converge and should be proposed as `never-lock`
  (`0005-structural-change-is-proposed-by-loop-decided-by-owner`).
- Attribution (world vs solution) becomes a first-class step in Learn.

## Related

- `0000-rebuild-from-concepts-not-from-code`
- `0005-structural-change-is-proposed-by-loop-decided-by-owner`
- `0007-execution-learnings-are-generation-constraints`
