---
status: Proposed
date: 2026-11-26
deciders: [k@wetware.works]
history:
  - "2026-11-26: Proposed — points 1, 2, 5 and 7 are the owner's statements in conversation (the file name and layout in point 2 are the implementing agent's); points 3 and 4 are choices the agent put to him and he approved with 'go'; point 6 is the agent's addition and was not put to him. Points 1 to 4 and 6 are implemented in 0.3.0. Point 5 for a parent that is a loop is not built: no loop has a parent loop yet. Not yet read by the decider in this written form"
---

# Decision Record 0018: A loop with no verifier assumes one from the intent, and its parent edits it

## Context

The owner of the first ravl system began by writing each loop in full, with separate Act
and Verify steps. He then found that in many cases the LLM expanded a short statement of
purpose and outcome better than he wrote the long form, and that the short form left him
less to reason about. He moved to short prompts on purpose.

`0014-verifier-criteria-carry-checks` works against that. It has the owner write a shell
check for each criterion, and a loop with no check records `no-verifier` and asks for
one. A loop written as three sentences of intent therefore cannot be judged until its
owner writes the part he chose to stop writing.

The first system also shows what to avoid. It re-derived the criteria from the intent on
every run. One loop's six runs were judged against 9, 9, 11, 8, 11 and 9 criteria, so a
pass on one run and a pass on the next did not mean the same thing.

## Decision

1. **When the specification gives no verification criteria, the loop assumes some from
   the intent.** The first run asks the LLM for criteria before Act, and writes them to
   `verifier.md` beside `ravl.md`.
2. **`verifier.md` is written to be read and improved.** It holds the outcome as the
   LLM understood it, what it assumed where the intent was silent, and the criteria: one
   per bullet in plain language, each with a `check` script where a mechanical test is
   possible. Its heading says it is assumed and unreviewed.
3. **Derived once, then held.** A run that finds `verifier.md` uses it as written. It is
   derived again only if the file is deleted.
4. **A loop does not change the criteria it is judged by.** The runner compares
   `verifier.md` after an LLM-driven Act with its content at the start of the run, writes
   the original back if they differ, and keeps the changed text in the run directory as
   a proposal. This is the rule `0005-structural-change-is-proposed-by-loop-decided-by-owner`
   already states, applied to this file.
5. **The parent improves the verifier.** A parent may add, remove or reword criteria and
   checks, using what it has observed of the loop's learnings and outcomes
   (`0004-parents-develop-children-by-editing-spec`). The edit is to `verifier.md`, or
   to a Verifier section in `ravl.md`.
6. **A Verifier section in `ravl.md` takes precedence.** When it holds any criterion,
   `verifier.md` is not read and nothing is derived. An owner who wants to write the
   criteria still can.
7. **Every loop has a parent.** A loop inside another loop's directory has that loop as
   its parent. A loop with no loop above it has the person who owns the tree as its
   parent. There is no loop without a parent, and "root loop" names only a position in
   the directory tree.

## Alternatives considered

| Option | Why not |
|---|---|
| Keep `0014` point 3: no checks means no verifier, ask the owner | Puts back the writing and reasoning the owner removed by moving to short prompts. |
| Re-derive the criteria on every run | What the first system did. The number and content of criteria changed between runs, so results were not comparable and a loop could pass by being judged more loosely. |
| Write the assumed criteria into `ravl.md` | The loop would be editing its own specification. Keeping them in a second file leaves `ravl.md` as only what the parent wrote. |
| Let the loop refine its own criteria as it learns | A loop that fails could pass by weakening its test. The loop proposes; the parent edits. |
| **Chosen: assume once into a separate file; the parent edits it** | The owner writes a few sentences. The criteria are visible, stable between runs, and changed only by someone other than the loop they judge. |

## Consequences

- The first run of a bare intent makes one more LLM call, charged to the loop's budget.
- The checks in `verifier.md` are shell scripts written by an LLM and run on the host on
  every run. Nobody has read them before the first run uses them. The owner's
  configuration of where a loop runs is what bounds this, as it bounds Act.
- The criteria are derived with no tools, from the text of the specification alone. A
  check can therefore name a file or a command that the later Act does not produce or
  that the host does not have. The first run shows this as a failing check, and the
  parent corrects the file.
- A criterion with no check is recorded as unchecked, as before. Judging such a
  criterion with an LLM is not part of this record.
- When no LLM is configured, the call fails, or the reply holds no criteria, nothing is
  written and the run records `no-verifier` as in `0014`.
- `0014` point 3 is narrowed: "no verifier yet" now means the derivation has not
  succeeded, not that the owner has yet to write checks.

## Related

- `0004-parents-develop-children-by-editing-spec`
- `0005-structural-change-is-proposed-by-loop-decided-by-owner`
- `0014-verifier-criteria-carry-checks`
