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

Neither consumer project contained Python code of its own. Each was a directory tree of
loops plus the framework needed to run them. The framework was the only reason a
Python environment existed in those repositories.

## How loops are developed and run

The command line is the primary surface. A loop is developed by a repeated cycle:

1. Edit `ravl_loop.md`.
2. Run the loop.
3. Read what the run understood from the intent, whether Verify passed, what Learn
   wrote as steer, and any questions addressed to the owner.
4. Edit `ravl_loop.md` again.

The distribution must make step 2 and step 3 fast from any directory, with no project
setup. It must also make the answer to "which version ran" unambiguous, because the
recorded confusion came from two installations giving different answers.

## Proposal

`ravl` is distributed as one ordinary Python package that provides the `ravl`
command. Nothing from the framework is checked into a consumer repository.

Three things are kept separate, each with one location:

| Thing | Location | Versioned by |
|---|---|---|
| The library and `ravl` command | Installed once per host with `uv tool install ravl` | `uv tool upgrade ravl`; version reported by `ravl --version` |
| Loops (`ravl_loop.md` and `config/`) | Any directory, usually a Git repository | The owner, in Git |
| State (`runs/`, `learnings/`) | Beside each loop by default; relocatable by configuration | Not committed by default; the owner opts specific learnings in |

### One installation per host

`uv tool install ravl` is the only installation for running and developing loops. It
places one `ravl` command on the path, in its own isolated environment managed by
`uv`. A loops repository needs no `pyproject.toml`, no virtual environment and no
dependency declaration; it is a directory tree of `ravl_loop.md` files.

This is a deliberate narrowing from "host-wide or project dependency". Offering both
recreates the condition that produced the recorded confusion.

**Exception: programmatic use.** A Python project that calls `ravl` from its own code
(`import ravl`) adds it as a normal dependency with `uv add ravl` and pins it in
`pyproject.toml`. That project runs loops through its own code, not through the
host-wide command. If the host-wide `ravl` command is run inside such a project and
the two versions differ, the command prints both versions and stops.

**Version requirement for a loops repository.** A loops repository may declare a
minimum library version in a `ravl.toml` at its root. `ravl` reads it and refuses to
run with an older version, printing the upgrade command. This gives a loops repository
reproducibility without a Python project.

### Commands the cycle needs

The commands below are the surface the development cycle uses. Each reads or writes
files in the loop directory and nothing else; the agent surface (below) exposes the
same operations.

| Command | Effect |
|---|---|
| `ravl run <dir>` | One run of the loop in `<dir>`. Prints, in order: the execution mode and whether it was set or learned; what Reflect understood from the intent; the Verify result; the steer Learn wrote; any questions for the owner; the cost ledger. |
| `ravl list [<dir>]` | Every loop under `<dir>` (default: current directory), with its execution mode, last Verify result, and open questions. Found by scanning for `ravl_loop.md`; there is no registry. |
| `ravl show <dir>` | The loop's current state without running it: mode, last run summary, steer, open questions, cost history. |
| `ravl answer <dir>` | Interactive: presents each open question for the owner and records the answer where the next Reflect reads it. |
| `ravl set <dir> lock \| never-lock \| learned` | Owner setting for execution mode. |
| `ravl runs <dir>` | Lists runs; `ravl runs <dir> <id>` prints one trace. |
| `ravl new <dir>` | Creates a directory with a template `ravl_loop.md` that has intent and verifier sections. |

Output is written for a person reading a terminal. A `--json` flag emits the same
content as structured data for the agent surface.

### Configuration

Configuration is resolved in this order, later entries overriding earlier:

1. User-level file (`~/.config/ravl/config.toml`): LLM provider credentials and
   defaults. Set once per host.
2. Repository-level `ravl.toml` at the loops root: minimum version, learning-store
   location, whether parents may edit child specifications.
3. Loop-level `config/` in the loop directory: execution mode setting and per-loop
   overrides.

No environment variables are read except those the LLM provider libraries themselves
read for credentials.

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
- A `ravl mcp` command that starts an MCP server exposing the same operations as the
  command line: `list`, `run`, `show`, `answer`, `set`, `runs`.

This is how loops are run from an agent session instead of a console. It is the same
package as the command-line tool, so it does not add a second distribution channel.

## Open point: dependencies of generated code

When a loop becomes code-driven, the generated program may import packages that are not
installed in the `ravl` tool environment. RavlGPT handled this with a dependency
whitelist and a virtual environment it managed inside the consumer repository.

Proposed replacement: generated programs carry
[PEP 723 inline script metadata](https://peps.python.org/pep-0723/) declaring their
dependencies, and are executed with `uv run <script>`. `uv` creates and caches an
isolated environment per script from that metadata.

Effects:

- The whitelist is retained. The library validates the declared dependencies against
  it before execution.
- The framework does not create or manage virtual environments.
- The dependencies of a generated program are visible in the program file itself.
- `uv` is already present, because it installed `ravl`; no additional runtime
  requirement is introduced.

This point needs the owner's view before it is decided. The alternatives are: keep a
framework-managed environment per loop (RavlGPT's approach), or require every possible
dependency to be installed into the `ravl` tool environment.

## Decision required

1. Accept `uv tool install` as the only installation for developing and running loops,
   with `uv add` reserved for programmatic use.
2. Accept the command set above as the first surface to build.
3. Accept or reject PEP 723 + `uv run` for generated-code dependencies.
