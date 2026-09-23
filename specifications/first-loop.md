# The first loop

The specification has reached the point where further conceptual refinement is not
productive. From here, real loops drive it: each loop that is run either confirms the
model or produces a correction to it, recorded as a decision record. This document
defines the first loop and what the library must do to run it.

## Selection criteria

The first loop must:

1. Produce an outcome that **recurs**, so that a second run has something to learn from
   the first.
2. Have a **verifier that already exists** in some form, so the red–green cycle starts
   at green on the verifier and red on the loop.
3. Be **cheap to run many times** while the library is being built.
4. Need **no private data**, so the loop and its runs can be committed to this
   repository as the first worked example.
5. Exercise the **LLM-driven to code-driven transition**, because that transition is the
   economic claim of the whole project and was never demonstrated by RavlGPT. If it
   cannot be made to work on a simple loop, the project stops.

## The loop

**Intent:** A file `report.md` in the loop directory contains today's date, the number
of open decision records in this repository, and the title of each, one per line,
sorted by number.

**Verifier:**

- `report.md` exists and was modified during this run.
- The first line is today's date in ISO 8601.
- The count on the second line equals the number of files matching
  `.about/decisions/[0-9]*.md` whose front matter has `status: Proposed`.
- Each subsequent line is one title, and the titles match the `# Decision Record NNNN:`
  headings of those files, in numeric order.

This is deliberately trivial as a task. Its value is that:

- it recurs (run it daily, or on every commit);
- the world changes between runs (decision records are added and accepted), so world
  failures and solution failures both occur naturally;
- the procedure is identical every run while the data varies, which is exactly the case
  A2 says should move to code-driven;
- the verifier is mechanical and can be checked without an LLM;
- an LLM-driven Act will produce a correct report on the first or second attempt, and a
  code-driven Act is ~20 lines of Python;
- nothing in it is private.

## What the library must do to run it

The smallest runner that gets this loop through one run, in build order. Each step is
one commit and one decision record if it settles anything the model left open.

| Step | Library capability | Observable result |
|---|---|---|
| 1 | `ravl new <dir>` writes a template `ravl.md` | The file exists with intent and verifier sections |
| 2 | `ravl run <dir>` with Reflect and LLM-driven Act only; Verify and Learn are stubs that record "not implemented" | `report.md` is produced; `runs/<id>/trace.json` records each phase, the cost ledger, and the effect claimed |
| 3 | Runtime confirms the claimed effect exists before Verify | A run whose Act claims a write that did not happen is recorded as such |
| 4 | Verify runs the criteria above mechanically | Trace records pass or fail with the failing criterion |
| 5 | Learn classifies the result (world/solution, questions 6–9 in the model) and writes steer to `learnings/steer/` | Second run's Reflect reads the first run's steer, visible in the trace |
| 6 | Learn evaluates question 10 and, when the signals are met, generates `learnings/generated/act.py` with PEP 723 metadata; whitelist check; execution constraints applied | After N passing runs the mode changes; the trace shows the LLM call count drop to zero |
| 7 | Learn moves back to LLM-driven on a solution failure of generated code | Rename a decision file to break the procedure; the next run is LLM-driven again, and the run after that has new code |
| 8 | `ravl set <dir> lock` and `never-lock` | The owner setting overrides the learned mode, visible in the trace |
| 9 | `ravl list`, `ravl show`, `ravl runs` | The development cycle is observable from the terminal |

Steps 1–5 are the minimum for the red–green cycle on a spec. Step 6 is the kill
criterion. Steps 7–9 make the result usable.

Not built for the first loop: children, budgets beyond a per-run token cap, read radius,
`ravl.py` loops, the MCP surface, configuration beyond `config/mode`. Each of those is
introduced by the first loop that needs it.

## The second loop

Not chosen yet. The candidate class is a **recurring maintenance outcome**: a service
that must be up, a job that must have run, a repository that must be in sync. Each of
those is currently a hand-written watchdog script somewhere. The point of the second
loop is to replace one such script with a loop and observe whether the loop repairs
itself where the script only reported. This introduces children and budgets. It is
specified after the first loop has run to step 7.

## How specification proceeds from here

- A run that behaves as the model predicts confirms the model. Nothing is written.
- A run that behaves otherwise, and the library is at fault, is a bug.
- A run that behaves otherwise, and the model is at fault, produces a decision record
  that supersedes or amends the relevant axiom. The model is edited to match.
- A question the model does not answer, encountered while building, is written to
  `specifications/speculative/` first and promoted to a decision record when resolved.
