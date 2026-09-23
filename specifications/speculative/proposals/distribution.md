# Proposal: distribution of `ravl`

Status: speculative. Not a decision. If accepted, this becomes decision record 0008.

## Problem

RavlGPT was distributed in two ways at once: as a Git submodule checked out at
`.ravl/` inside each consumer repository, and as a host-wide `uv tool install`. The two
consumer projects that used it in practice both used the submodule, with a `ravl`
symlink to a wrapper script inside it, a virtual environment created by the framework
inside the consumer repository, and a `RAVL_LEARNINGS_DIR` environment variable to
relocate state. The recorded problems were:

- A command that worked from the submodule did not work from the host-wide install.
- Two installations meant two possible answers to "which version of the framework is
  running".
- Updating the framework required a manual submodule pull and a commit in the consumer
  repository.
- The consumer repository's `.gitignore` had to carry a hand-maintained list of which
  framework-written files to track and which to ignore.
- Each consumer repository built its own agent instructions and slash commands that
  pointed into `./.ravl/docs`.

## Proposal

`ravl` is distributed as one ordinary Python package. Nothing from the framework is
checked into a consumer repository.

Three things are kept separate, each with one location:

| Thing | Location | Versioned by |
|---|---|---|
| The library (`ravl` package) | PyPI, or `git+https://github.com/KevinT/ravl` | The consumer's `pyproject.toml`, like any dependency |
| Loops (`ravl_loop.md` and `config/`) | The consumer's repository, in any directory | The consumer, in Git |
| State (`runs/`, `learnings/`) | Beside each loop by default; relocatable by configuration | Not committed by default; the consumer opts specific learnings in |

### Two ways to install, one mechanism

- **Host-wide:** `uv tool install ravl` puts a `ravl` command on the path. `ravl run
  <dir>` runs any directory that contains a `ravl_loop.md`. No project setup is needed.
  This is the fast path for local, personal loops.
- **Project dependency:** `uv add ravl` in the consumer's `pyproject.toml`. The same
  `ravl` command is available through `uv run ravl`, and `import ravl` is available for
  programmatic use.

Both resolve the same package through the same package manager. `ravl --version`
reports one pinned version in either case. This removes the condition that caused the
recorded confusion: two installations of different code.

### Removed from RavlGPT's distribution

Submodule; `.ravl/` directory in the consumer; `ravl` symlink; `ravl-wrapper`;
`install.sh`; `RAVL_LEARNINGS_DIR` and similar environment variables;
framework-managed virtual environments inside the consumer tree; the
`ravl-sync-claude` and `ravl-sync-opencode` generators.

### Agent surface

The consumer projects wrote their own agent instructions for `ravl` because none were
shipped. The package ships:

- An agent-readable protocol document that a Claude Code skill, Hermes skill, or Cowork
  plugin references directly.
- A `ravl mcp` command that starts an MCP server exposing `list`, `run`, `show-steer`
  and `answer-question` as tools.

This is how loops are run from an agent session instead of a console. It is the same
package as the command-line tool, so it does not add a second distribution channel.

## Open point: dependencies of generated code

When a loop becomes code-driven, the generated program may import packages that the
consumer has not installed. RavlGPT handled this with a dependency whitelist and a
virtual environment it managed inside the consumer repository.

Proposed replacement: generated programs carry
[PEP 723 inline script metadata](https://peps.python.org/pep-0723/) declaring their
dependencies, and are executed with `uv run <script>`. `uv` creates and caches an
isolated environment per script from that metadata.

Effects:

- The whitelist is retained. The library validates the declared dependencies against
  it before execution.
- The framework no longer creates or manages virtual environments.
- The dependencies of a generated program are visible in the program file itself.
- `uv` becomes a runtime requirement for code-driven execution.

This point needs the owner's view before it is decided. The alternatives are: keep a
framework-managed environment per loop (RavlGPT's approach), or require the consumer to
install every dependency a generated program may need.

## Decision required

1. Accept one package as the only distribution channel.
2. Accept or reject PEP 723 + `uv run` for generated-code dependencies.
