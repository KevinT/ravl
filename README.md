# ravl

**Reflect · Act · Verify · Learn** — a small library and protocol for loops that run
once, check their own result, and leave guidance for their next run. For outcomes that
recur: each run should cost less and fail less than the one before.

> Pre-release, version 0.4.0. The runner covers build steps 1 to 9 of
> [`specifications/first-loop.md`](specifications/first-loop.md): one loop, run from the
> command line, moving between LLM-driven and code-driven execution. Decisions 0012 to
> 0019 are implemented and still proposed. Read the model first.

## Install and run

```sh
uv tool install git+https://github.com/KevinT/ravl     # one installation per host
uv tool upgrade ravl                                   # later, to update it
ravl config                                            # shows the agent programs it found; choose one
ravl new my-loop                                       # writes my-loop/ravl.md
$EDITOR my-loop/ravl.md                                # intent, and criteria with checks
ravl run my-loop                                       # one run: Reflect, Act, Verify, Learn
ravl list                                              # every loop below here, with its state
```

`ravl run` needs an LLM for Act and Learn, and for Act it must be an agent: a program that
can change files and run commands. ravl has no agent of its own. It ships backends for
agent programs you may already have, each of which uses its own sign-in:

| Backend | Program | State |
|---|---|---|
| `claude` | Claude Code | run end to end |
| `codex` | Codex CLI | written from the program's help text; not yet run against a signed-in Codex |

`ravl config` shows which of them are on `PATH` and whether a sign-in was found. It starts
no program and reads no credential. `ravl config set claude --model sonnet` writes the
choice to `~/.config/ravl/config.toml`. ravl never chooses one by itself.

```toml
[llm]
backend = "claude"
model = "sonnet"

[llm.learn]            # optional: another model for one phase
model = "haiku"
```

For any other agent, name a command in place of a backend. It reads a prompt on standard
input and writes its reply on standard output; `RAVL_PHASE` tells it which phase it is in.
[`contrib/backends/claude-code`](contrib/backends/claude-code) is an example.

```toml
[llm]
command = ["/path/to/an/agent-adapter"]
```

In Act the agent runs with its approval prompts off, because nobody is present to answer
them. **ravl does not confine a run yet.** Until it does, run loops you have not read
inside a sandbox of your own.

A specification is one file. A criterion with a `check` block is decided by the block's
exit status; no LLM takes part in Verify.

```markdown
# Nightly export

## Intent

`export.csv` in this directory holds yesterday's orders, one per line.

## Verifier

- `export.csv` was written during this run.
  ```check
  test export.csv -nt "$RAVL_RUN_DIR/started"
  ```
```

### Turning an existing scheduled job into a loop

Put the command the scheduler ran into an `act` block and point the scheduler at
`ravl run <dir>`. The implementation runs on every run with no LLM. When it stops
meeting the verifier, the failure is classified once; a solution failure gets up to two
LLM-driven repair attempts, and then the owner is asked. While the loop waits, the
implementation still runs, so a cause removed by hand is noticed on the next run.

```markdown
## Act

```act
/usr/local/bin/export-orders --yesterday > export.csv
```

## Verifier

- The export ran to completion in this run.
  ```check
  test -e "$RAVL_RUN_DIR/act-ok"
  ```
- `export.csv` has at least one order.
  ```check
  test "$(wc -l < export.csv)" -ge 1
  ```
```

What a run does:

| Situation at Reflect | Act | LLM calls |
|---|---|---|
| Every check passes | nothing | 0 |
| A check fails; loop is LLM-driven | the agent does the work once | Act and Learn |
| A check fails; loop is code-driven | generated `act.py` runs | 0, or Learn if Verify then fails |
| Same failure as last run and Learn set a hold | nothing; the open question stands | 0 |

After three consecutive LLM-driven passes Learn asks for a program that performs Act,
checks it (parses, declared dependencies on the whitelist, no recorded execution
constraint violated) and switches the loop to code-driven. A solution failure of that
code switches it back. `ravl set <dir> lock | never-lock | learned` overrides this.
[`examples/decision-report`](examples/decision-report) is the first loop, with its runs
and learnings committed: three LLM-driven runs, then code-driven runs with no LLM call.

Tests: `uv run pytest`.

## Start here

| Question | Read |
|---|---|
| What is this a part of, and what are its trust boundaries? | [`.about/purpose.md`](.about/purpose.md) |
| How do I reason about a loop? | [`.about/mental-models/ravl-loop/model.md`](.about/mental-models/ravl-loop/model.md) |
| What must the library never do? | [`.about/principles.md`](.about/principles.md) |
| Where does it sit on the alignment stack, and what is that? | [`.about/situates.md`](.about/situates.md) |
| Why was it decided this way? | [`.about/decisions/`](.about/decisions/README.md) |
| What gets built first, and what is the kill criterion? | [`specifications/first-loop.md`](specifications/first-loop.md) |
| What is carried from RavlGPT, adapted, or left behind? | [`specifications/reference/ravlgpt-guardrails.md`](specifications/reference/ravlgpt-guardrails.md) |
| How is it installed and run? | [`0012-one-install-per-host-and-the-command-line-first`](.about/decisions/0012-one-install-per-host-and-the-command-line-first.md) (proposed), from [`distribution.md`](specifications/speculative/proposals/distribution.md) |
| I am an agent working in this repo | [`AGENTS.md`](AGENTS.md) |

## Repository layout

```
.about/            purpose, principles, position on the stack, the mental model, decisions
src/ravl/          the library and the `ravl` command
tests/             phase contract, learning store, read rule, verification, constraints
examples/          public, invented loops with their runs and learnings
src/ravl/backends/ adapters for agent programs, run as a separate process; not core
contrib/backends/  an example of a custom command adapter
specifications/    what is being built next
  first-loop.md    the first loop and the build order for the runner
  reference/       guardrails for consulting RavlGPT
  speculative/     proposals not yet decided; promoted to .about/decisions/ when resolved
```

## Lineage

`ravl` re-derives the concepts first developed in
[KevinT/RavlGPT](https://github.com/KevinT/RavlGPT). That repository is kept whole as
evidence; no code is ported from it
([`0000-rebuild-from-concepts-not-from-code`](.about/decisions/0000-rebuild-from-concepts-not-from-code.md)).

## Licence

[Mozilla Public License 2.0](LICENSE).
