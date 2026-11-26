---
status: Proposed
date: 2026-11-26
deciders: [k@wetware.works]
history:
  - "2026-11-26: Proposed — written by the implementing agent while building the runner (first-loop steps 1 to 8), under the owner's instruction to build; implemented in 0.1.0; not yet reviewed by the decider"
---

# Decision Record 0012: One installation per host; the command line is the first surface

## Context

RavlGPT was distributed as a Git submodule inside each consumer repository and as a
host-wide tool at once, and the two disagreed about which version ran. The proposal
[`distribution.md`](../../specifications/speculative/proposals/distribution.md) sets out
the recorded problems and a replacement. The runner had to be built against one answer.

## Decision

1. `ravl` is one Python package that provides the `ravl` command. It is installed once
   per host with `uv tool install`. A loops repository holds `ravl.md` files and
   `config/`; it has no Python project, virtual environment or copy of the library.
2. The command set is `new`, `run`, `list`, `show`, `runs`, `set`, `answer`, each
   reading and writing files in the loop directory only. `--json` emits the same
   content as data. `ravl run` exits 0 when Verify passes, 1 when it does not, 2 when
   the run could not start, 3 when another run of the loop is in progress.
3. Configuration is read from three files, later overriding earlier: the user file
   `~/.config/ravl/config.toml`, `ravl.toml` at the root of a tree of loops, and
   `config/` in the loop directory (`config/mode` for the owner's execution-mode
   setting, `config/loop.toml` for everything else). No environment variable is read.
4. `ravl.toml` may state `min_version`; an older library refuses to run and prints the
   upgrade command.
5. Generated code is one Python file with PEP 723 inline metadata. Its declared
   dependencies are checked against a whitelist before it runs. A program with no
   dependencies is run by the interpreter that runs `ravl`; one with dependencies is run
   by `uv run --script`. The library creates no virtual environment.

## Alternatives considered

| Option | Why not |
|---|---|
| Submodule in each loops repository | Two installations, two answers to "which version ran"; the recorded source of confusion. |
| Host-wide tool or project dependency, either | Recreates two installations. `uv add ravl` remains for programs that import the library. |
| Library-managed environment per loop for generated code | The library would manage environments inside the consumer tree, which RavlGPT's `venv_manager` showed to be a large surface. |
| **Chosen: one `uv tool` install; PEP 723 for generated code** | One version per host; dependencies of generated code are visible in the file. |

## Consequences

- Not built yet from the proposal: `ravl mcp`, the shipped agent protocol document, and
  the version check between a host install and a project dependency.
- Until the package is published to an index, the one installation is made from a Git
  URL or a local clone.

## Related

- `0006-core-is-environment-blind`
- `0007-execution-learnings-are-generation-constraints`
