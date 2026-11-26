---
status: Proposed
date: 2026-11-26
deciders: [k@wetware.works]
history:
  - "2026-11-26: Proposed — the owner asked for `ravl config`, said ravl must not assume that Hermes or Claude is installed, asked that setup be as smooth as possible by supporting the standard options, and pointed at Hermes Agent's handling of providers as something to reuse. He approved building 'detection and the installed-agent backends first' before reading this text. Implemented in 0.4.0 for two programs, of which Claude Code has been run end to end and Codex has not; the backend for a bare API key and the sandbox are separate records still to be written"
---

# Decision Record 0019: Agent programs are backends shipped in the package and chosen with `ravl config`

## Context

`0013-the-llm-is-a-command-the-owner-configures` makes the LLM a command the owner
names, and puts adapters for particular agents outside the package, under `contrib/`.
Two things follow that the owner does not want. A fresh `uv tool install ravl` has no
adapter at all, so its first run reports that no LLM is configured. And the owner must
find an adapter's path and write its argv into a file by hand.

Act needs more than a model. It needs an agent: something that runs commands and edits
files until the work is done. ravl has no agent of its own. Agents that people already
have installed (Claude Code, Codex and others) each bring their own sign-in, their own
tools and, in some cases, their own sandbox.

Hermes Agent (MIT licence) has a worked answer to "which model, with which credential".
Three parts of its design are used here: a registry in which each provider is one
entry of data; a fixed order in which a credential is looked for; and a setup step that
shows what is already on the machine and lets the user pick from it. No Hermes code is
copied in this step.

## Decision

1. **A backend is a named adapter shipped inside the package**, under `ravl.backends`.
   It is run as a separate process and keeps the contract of `0013`: the prompt on
   standard input, one JSON object with the reply and the usage on standard output, and
   the phase in `RAVL_PHASE`.
2. **The core still knows no agent.** `[llm] backend = "<name>"` resolves to the command
   `python -m ravl.backends <name>` without the core reading the name. The registry and
   the adapters are imported only by that process and by `ravl config`.
3. **`[llm] command` remains and takes precedence.** An owner who wants an agent or a
   wrapper that ravl does not ship still names any command.
4. **The first backends are agent programs the owner already has**: `claude` (Claude
   Code) and `codex` (Codex CLI). ravl stores no credential for them; each program uses
   its own sign-in. `[llm] model`, and `[llm.<phase>] model`, are passed to the program
   as its model option.
5. **`ravl config` shows what is set and what it found**: for each backend, whether the
   program is on `PATH` and whether its sign-in is present. It finds this out by looking
   at `PATH` and at the existence of the program's sign-in file. It starts no program
   and reads no credential. On a terminal with nothing configured it offers the found
   programs as a numbered choice. `ravl config set <name> [--model M]` writes the choice.
6. **ravl never chooses a backend by itself.** Until the owner has chosen, a run does no
   Act and says how to configure one. An agent is not started with its approval prompts
   off on a machine whose owner has not asked for that.
7. **In Act the agent runs with its approval prompts off**, because nobody is present to
   answer them. In every other phase it is given no tools, or a read-only sandbox.

## Alternatives considered

| Option | Why not |
|---|---|
| Keep adapters in `contrib/` and document the path | The install is not complete on its own, and the path differs on every machine. |
| Build one agent into ravl and use only API keys | Leaves out the subscription sign-ins people already have, which can be used only by running the vendor's own program, and makes ravl maintain an agent before it has users. It is the next step, not the first. |
| Pick the first agent found, with no question | Starts an agent with full permissions that the owner never selected. |
| Find out whether a program is signed in by running it | On a machine where the program is a lazy-install shim, running it starts an installation. This happened during this work. Looking at files starts nothing. |
| Read the other program's credential and call the API directly | A subscription credential is issued for the vendor's own program. Running that program is the supported use. |
| **Chosen: adapters in the package, found without execution, chosen by the owner** | One install is complete. Setup is one command that shows what is there. The core stays ignorant of which agent runs. |

## Consequences

- `0013` point 5 changes: adapters for particular agents ship in the package under
  `ravl.backends`. `contrib/backends/claude-code` stays as an example of a custom command.
- **ravl does not confine a run yet.** With `claude`, Act can change anything the user
  can. With `codex`, the program's own sandbox limits writes to the loop directory and
  its temporary directory, so a loop whose intent names a path elsewhere cannot write
  there. A sandbox that belongs to ravl, one per run covering the loop and its children,
  is the record after next.
- The `codex` adapter was written from the program's help text. It has been run only as
  far as Codex refusing an unsigned-in call, which shows that its options are accepted.
  It has not produced a reply. `ravl config` says so.
- A machine with no agent program installed still has no backend. The backend for a bare
  API key, with a small agent inside ravl, is the next record. The order in which a
  credential is looked for is decided there: ravl's own setting, then the environment,
  then sign-ins already on the machine.
- On macOS, Claude Code keeps its sign-in in the system keychain and not in a file, so
  `ravl config` reports "no sign-in found" for a program that is signed in. The wording
  says a sign-in was not found, not that the program is signed out.

## Related

- `0006-core-is-environment-blind`
- `0012-one-install-per-host-and-the-command-line-first`
- `0013-the-llm-is-a-command-the-owner-configures`
