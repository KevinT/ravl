# Option: smolagents as an LLM-driven Act backend

Status: speculative, to investigate later. Not a proposal and not a decision.

## What it is

[smolagents](https://github.com/huggingface/smolagents) (Hugging Face) is a small library
for a single LLM agent working on one task. Its `CodeAgent` acts by writing and running
Python snippets, calls tools, reads the results and continues until it decides the task
is done. It supports many model providers through LiteLLM, and runs agent code in a
restricted local interpreter with an allowed-imports list, or in a Docker or E2B sandbox.

## How it relates to ravl

It works inside one session and has no equivalent of what ravl adds across runs: no
mechanical Verify against owner criteria, no learning store, no world/solution
classification, no change of execution mode. It is therefore not a replacement for any
part of the protocol. The one place it could fit is inside Act, as an implementation of
LLM-driven execution.

Possible benefits, to be tested:

- **Model-agnostic multi-step Act.** The first loop's plan is to perform LLM-driven Act
  through a command that takes a prompt (a CLI agent). A `CodeAgent` would do the same
  with any model, including cheaper or local ones.
- **Input to the code-driven transition.** It records each step of Act as the Python it
  executed. That trace is close to what Learn needs in order to generate `act.py`
  ([`0002-execution-mode-learned-and-owner-settable`](../../../.about/decisions/0002-execution-mode-learned-and-owner-settable.md)).
  With a CLI agent's transcript, the procedure has to be reconstructed.
- **Execution constraints.** Its allowed-imports list overlaps with the package
  whitelist ravl applies to generated code
  ([`0007-execution-learnings-are-generation-constraints`](../../../.about/decisions/0007-execution-learnings-are-generation-constraints.md)).

## Constraints any use must respect

- [`0006-core-is-environment-blind`](../../../.about/decisions/0006-core-is-environment-blind.md):
  the core names no agent runtime. smolagents can only be an optional adapter behind the
  LLM-driven Act interface, never a dependency of the core.
- [`0001-one-attempt-per-run`](../../../.about/decisions/0001-one-attempt-per-run.md):
  several tool steps inside one Act are allowed; re-running Act until Verify passes is
  not. smolagents examples commonly loop until a check passes, which would violate this.
- Principle 2: a capability is added only when a loop that is actually run needs it.
- Before use, classify it with the three tests in
  [`../../reference/ravlgpt-guardrails.md`](../../reference/ravlgpt-guardrails.md),
  treating it as an external component.

## When to investigate

At build step 6 of [`../../first-loop.md`](../../first-loop.md) (generated code), if
deriving `act.py` from LLM-driven runs proves difficult because those runs leave no
usable record of the procedure. Until then the Act backend stays a command that takes a
prompt.

## Questions to answer when investigated

1. Does a `CodeAgent` step log give Learn enough to generate a correct `act.py` for the
   first loop with fewer LLM calls than reconstructing it from a CLI transcript?
2. Can its executor enforce ravl's execution constraints, or does ravl still need its
   own check before running generated code?
3. What does it add to the cost ledger (tokens per run) compared with the CLI backend on
   the same loop?
