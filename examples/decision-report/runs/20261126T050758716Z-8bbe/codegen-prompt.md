An LLM has performed the Act phase of this RAVL loop on consecutive runs and the
verifier passed each time. Decide whether the procedure is the same from run to run. If it
is, write a program that performs Act without an LLM.

# Specification (ravl.md)
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

# The passing LLM-driven runs
## Run 20261126T050726191Z-dce7
Summary: Wrote report.md with today's date, the count 5, and the headings of proposed decision records 0012-0016. The file was not checked against the verifier.
Procedure:
- cd /home/trek/Source/personal/ventures/ravl/examples/decision-report
- { date +%F; grep -l '^status: Proposed' ../../.about/decisions/[0-9]*.md | wc -l; for f in $(grep -l '^status: Proposed' ../../.about/decisions/[0-9]*.md | sort); do grep -m1 '^# Decision Record' "$f" | sed 's/^# //'; done; } > report.md
Effects: report.md

## Run 20261126T050743215Z-edf7
Summary: Rewrote report.md with today's date, the count of proposed decision records (5), and one heading line per proposed record in order of record number.
Procedure:
- cd to the loop directory
- n=$(grep -l '^status: Proposed' ../../.about/decisions/[0-9]*.md | wc -l)
- wrote date +%F, $n, then for each sorted file with status: Proposed the first '# Decision Record' heading without '# ' into report.md
Effects: report.md

## Run 20261126T050758716Z-8bbe
Summary: Rewrote report.md with today's date, the count 5, and the headings of proposed decision records 0012-0016. I did not run the verifier checks.
Procedure:
- cd /home/trek/Source/personal/ventures/ravl/examples/decision-report
- Wrote report.md from: date +%F; grep -l '^status: Proposed' ../../.about/decisions/[0-9]*.md | wc -l; for each matching file (sorted), grep -m1 '^# Decision Record' | sed 's/^# //'
- cat report.md to confirm content
Effects: report.md

# Execution constraints (the program is rejected if it violates one)
(none)

# Resources that contributed to the passing runs
(none)

# Contract for the program
- One Python file. It starts with PEP 723 inline metadata:
  # /// script
  # requires-python = ">=3.11"
  # dependencies = []
  # ///
- Dependencies may only be chosen from this whitelist: none (standard library only).
- It runs with the loop directory as working directory and takes no arguments.
- It is safe to run when the outcome already partly holds, and it does only what the
  intent describes.
- It exits 0 when it has done the work and non-zero when it could not.
- Its last line of standard output is a JSON object: {"effects": [...], "summary": "..."}.
- Input data may differ between runs; encode the procedure, not one run's data.

If the procedure is not the same from run to run, or it needs judgement that code cannot
supply, reply with only this JSON object: {"repeatable": false, "reason": "<one sentence>"}

Otherwise reply with the program in one fenced python block and nothing else.
