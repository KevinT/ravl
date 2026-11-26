---
status: Proposed
date: 2026-11-26
deciders: [k@wetware.works]
history:
  - "2026-11-26: Proposed — the owner said the command's output was bare beside the first system's, which printed each phase in colour as it ran, and named two agent consoles as references. Built in 0.5.0 and shown to him as screenshots before any release"
---

# Decision Record 0020: The terminal display is a surface, fed by an observer on the run

## Context

`ravl run` printed nothing until a run ended, and then one block of plain text. A run
whose Act is an agent takes minutes. The first system printed a banner for each of the
four phases as it started, with detail lines in colour and the time each phase took.

The purpose of this repository puts every surface outside the core: the core receives
no information about which surface invoked it. The package also had no dependency.

## Decision

1. **On a terminal, a run is shown as it happens.** Each phase is one line headed by its
   letter (R, A, V, L). While the phase runs the line carries a spinner and the time so
   far. When it ends the line carries its result, followed by the criteria with a mark
   each, the effects Act claimed, the classification, the steer for the next run, and a
   closing line with the verdict and the cost. A question for the loop's parent is
   drawn in a box with the command that answers it.
2. **`list`, `show`, `config` and `runs <id>` are drawn the same way.** `ravl runs DIR
   RUN_ID` draws a finished run from its trace; `--json` prints the trace.
3. **Output that is not a terminal is unchanged**: the plain text as before, and the
   trace with `--json`. Anything that reads the command's output keeps working.
4. **The runner reports to an observer and knows nothing of the display.**
   `run(..., observe=f)` calls `f` at the start, around each phase and at the end. The
   observer is handed copies, and an error inside it is discarded. The core imports
   nothing from the display.
5. **The display is drawn with `rich`**, the package's first dependency. It is imported
   only when standard output is a terminal.

## Alternatives considered

| Option | Why not |
|---|---|
| Colour the existing end-of-run block | Leaves minutes of silence during Act, which is the main complaint. |
| Write colour and a spinner by hand, with no dependency | Terminal width, wrapping, colour support and redrawing a line are each small and all already solved; the hand-written version would be the larger and worse one. |
| Print phase lines from inside the runner | Puts a surface in the core. A second surface (a tool-call interface, a web view) would need the same events and could not get them. |
| A full-screen interface | A run is four steps and a result. Lines that scroll can be read afterwards and pasted. |
| **Chosen: an observer on the run; a `rich` display for terminals only** | The run is visible while it happens, scripts see no change, and the core has one new parameter. |

## Consequences

- The package has a dependency. An install is no longer a single pure-Python wheel.
- A phase's duration is known to the display, which timed it, and not to the trace. A
  run drawn again from its trace shows the total only.
- The display chooses what to leave out: at Reflect it lists failing criteria on one
  line each with no check output, and at Verify it prints failing criteria whole with
  the last lines their checks printed.

## Related

- `0006-core-is-environment-blind`
- `0012-one-install-per-host-and-the-command-line-first`
