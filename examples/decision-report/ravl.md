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
