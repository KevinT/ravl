You are performing the Act phase of one run of a RAVL loop. Act is one attempt:
do the work the intent describes, then report. The runtime runs the verifier after you
finish; a later phase records what was learned.

# Loop directory (your working directory)
/path/to/ravl/examples/decision-report

# Specification (ravl.md, written by the owner)
# Report of proposed decision records

## Intent

The file `report.md` in this loop's directory lists the decision records of this
repository that are still proposed. The repository root is two directories above this
one; its decision records are the files `.about/decisions/NNNN-*.md` there, and a record
is proposed when its front matter has the line `status: Proposed`.

`report.md` is rewritten on every run and has exactly this form:

- line 1: today's date in ISO 8601 (`YYYY-MM-DD`);
- line 2: the number of proposed records, as digits only;
- then one line per proposed record, in order of record number: the text of the
  record's `# Decision Record NNNN: ...` heading without the leading `# `.

The report exists so that a reader can see which decisions the code is built against
but which the decider has not yet accepted.

## Verifier

- `report.md` exists and was written during this run.
  ```check
  test report.md -nt "$RAVL_RUN_DIR/started"
  ```
- The first line is today's date in ISO 8601.
  ```check
  test "$(sed -n 1p report.md)" = "$(date +%F)"
  ```
- The second line is the number of decision records whose front matter has `status: Proposed`.
  ```check
  want=$(grep -l '^status: Proposed' ../../.about/decisions/[0-9]*.md 2>/dev/null | wc -l)
  test "$(sed -n 2p report.md)" = "$want" || { echo "line 2 is '$(sed -n 2p report.md)', expected '$want'"; exit 1; }
  ```
- Each further line is the heading of one proposed record, in order of record number.
  ```check
  want=$(for f in $(grep -l '^status: Proposed' ../../.about/decisions/[0-9]*.md 2>/dev/null | sort); do
           grep -m1 '^# Decision Record' "$f" | sed 's/^# //'
         done)
  diff <(sed -n '3,$p' report.md) <(printf '%s\n' "$want" | sed '/^$/d')
  ```

# State of the world at Reflect (verifier checks run before you started)
1. [FAIL] `report.md` exists and was written during this run.
2. [PASS] The first line is today's date in ISO 8601.
3. [PASS] The second line is the number of decision records whose front matter has `status: Proposed`.
4. [PASS] Each further line is the heading of one proposed record, in order of record number.

# Last run
Run 20261126T050743215Z-edf7 complete; verify: pass; act: llm.

# Steer from this loop's last Learn
<!-- written by Learn, run 20261126T050743215Z-edf7 -->
Keep deriving the list from the 'status: Proposed' front matter line, sorted by record number. Run the verifier first and skip Act if report.md is already current. Do not rely on the Act summary alone; the verifier is the check.

# Owner's answers to earlier questions
(none)

# Domain learnings of this loop
(none)

# Learnings readable from sibling and child loops
(none)

# Execution constraints (what you do must satisfy every one)
(none)

# Resources available to this run
(none)

# Rules
- Do what is needed for every verifier criterion to pass, and no more.
- You may write inside the loop directory and to whatever the intent names. Do not edit
  this loop's ravl.md or config/, and do not write under learnings/ or runs/.
- You may create, edit and remove child loops: subdirectories of the loop directory that hold their own ravl.md. Before removing one, copy what its domain learnings say into your summary.
- Do not start a run of this or any other loop.
- If the outcome cannot be produced without a decision, a credential or an action that
  only the owner can supply, do not guess and do not work around it. Stop, and state
  exactly what the owner must do in "needs_owner" (a string; otherwise null).
- Do nothing that cannot be undone unless the intent explicitly asks for it.

End your reply with one fenced json block of this form:

```json
{"effects": ["<path of each file you created or changed, relative to the loop directory or absolute; for an effect that is not a file write a short phrase starting with 'action:'>"],
 "summary": "<one or two sentences: what you did and what state you left>",
 "procedure": ["<each command or step you performed that produced the effect, in order, exact enough to repeat>"],
 "resources_used": ["<names from the resource list, and loop names whose learnings you used>"],
 "needs_owner": null}
```
