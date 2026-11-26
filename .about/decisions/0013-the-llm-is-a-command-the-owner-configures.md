---
status: Proposed
date: 2026-11-26
deciders: [k@wetware.works]
history:
  - "2026-11-26: Proposed — written by the implementing agent while building the runner (first-loop steps 1 to 8), under the owner's instruction to build; implemented in 0.1.0; not yet reviewed by the decider"
  - "2026-11-26: Point 5 changed by 0019-agent-programs-are-backends-chosen-with-ravl-config: adapters for particular agents ship in the package under ravl.backends and are named with `[llm] backend`; a command still takes precedence"
---

# Decision Record 0013: The LLM is a command the owner configures

## Context

Act, Learn and code generation each need an LLM.
[`0006-core-is-environment-blind`](0006-core-is-environment-blind.md) forbids the core
from naming a model provider or an agent runtime. LLM-driven Act also has to change
files and run commands, which a text-completion call cannot do.

## Decision

1. The LLM is an argv list in configuration (`[llm] command`). The library starts it
   with the loop directory as working directory, writes the prompt to its standard
   input, and reads the response from its standard output. `llm.act`, `llm.learn` and
   `llm.codegen` may each name a different command.
2. The response is plain text, or one JSON object `{"text": ..., "usage": {"model",
   "input_tokens", "output_tokens", "cost_usd"}}`. `usage` is optional and is what the
   cost ledger records. A non-zero exit status, a timeout or an empty response is a
   failed call.
3. The command that performs Act is expected to be an agent: it does the work itself,
   with whatever tools and permissions its owner gave it, and ends its reply with a JSON
   report of the effects it claims, a summary, the procedure it followed, the resources
   it used and anything it needs from the owner. The runtime confirms the claimed file
   effects before Verify.
4. The library passes `RAVL_PHASE` (`act`, `learn`, `codegen`), `RAVL_LOOP_DIR`,
   `RAVL_RUN_DIR` and `RAVL_RUN_ID` in the command's environment so that an adapter can
   grant tools in Act and none in the other phases.
5. Adapters for particular agents live outside the core (`contrib/backends/`) and in
   their users' own repositories.

## Alternatives considered

| Option | Why not |
|---|---|
| A provider SDK in the core | Names an environment in the core; Act would also need a tool-use loop written in the library. |
| A plugin interface in Python | More surface than a process boundary, and ties adapters to the library's internals. |
| **Chosen: a command with a prompt on stdin** | The smallest contract that any agent CLI, script or test stand-in can meet. |

## Consequences

- What LLM-driven Act is permitted to do is decided by how the owner configures the
  command, not by the library. The library's own boundaries are the prompt contract,
  effect confirmation, and the checks on generated code.
- Token counts are as accurate as the adapter reports them; a command that reports no
  usage leaves the ledger with call counts and wall time only.
- The test suite uses a scripted command in place of an LLM.

## Related

- `0006-core-is-environment-blind`
- `0001-one-attempt-per-run`
