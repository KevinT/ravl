You are performing the Learn phase of one run of a RAVL loop. You classify what
happened and write guidance for later runs. You take no action and change nothing.

# Intent
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

# Execution mode of this run
llm (an LLM performed Act)

# Verifier before Act
1. [FAIL] `report.md` exists and was written during this run.
2. [PASS] The first line is today's date in ISO 8601.
3. [PASS] The second line is the number of decision records whose front matter has `status: Proposed`.
4. [PASS] Each further line is the heading of one proposed record, in order of record number.

# Act record
{
  "ok": true,
  "error": null,
  "reported": true,
  "summary": "Rewrote report.md with today's date, the count 5, and the headings of proposed decision records 0012-0016. I did not run the verifier checks.",
  "procedure": [
    "cd /home/trek/Source/personal/ventures/ravl/examples/decision-report",
    "Wrote report.md from: date +%F; grep -l '^status: Proposed' ../../.about/decisions/[0-9]*.md | wc -l; for each matching file (sorted), grep -m1 '^# Decision Record' | sed 's/^# //'",
    "cat report.md to confirm content"
  ],
  "resources_used": [],
  "needs_owner": null,
  "effects": [
    {
      "claim": "report.md",
      "confirmed": true
    }
  ]
}

# Verifier after Act
1. [PASS] `report.md` exists and was written during this run.
2. [PASS] The first line is today's date in ISO 8601.
3. [PASS] The second line is the number of decision records whose front matter has `status: Proposed`.
4. [PASS] Each further line is the heading of one proposed record, in order of record number.

# Steer written by the previous Learn
<!-- written by Learn, run 20261126T050743215Z-edf7 -->
Keep deriving the list from the 'status: Proposed' front matter line, sorted by record number. Run the verifier first and skip Act if report.md is already current. Do not rely on the Act summary alone; the verifier is the check.

# Already recorded: domain learnings
(none)

# Already recorded: execution constraints
(none)

# Decide, in this order
1. Did Verify pass? If it passed, classification is null.
2. If it failed: is the cause WORLD (an external service is down, data is absent, a
   credential has expired, a transient error, something only the owner can supply) or
   SOLUTION (the approach taken was wrong)?
3. If SOLUTION: is the fault in the SPECIFICATION (the intent or verifier is ambiguous or
   wrong, so the owner must change it) or in the DERIVATION (the intent is clear and this
   attempt was a wrong way to meet it)?
4. Should the next run attempt Act again, or hold? Hold when another attempt cannot
   succeed until the owner acts or the world changes.
5. What should the owner be asked? Ask only when a decision or action by the owner is
   needed. State what happened, what was tried, and the exact action or decision needed.
6. What did this run establish that is not already recorded below? Most runs establish
   nothing new; then both lists are empty. Do not restate the specification, and do not
   rephrase an entry that is already recorded.
   - domain: a fact about the task or its subject that a later run could not cheaply
     rediscover. Mark it "portable" if it would hold for sibling loops, else "local".
   - execution: a constraint on how the work is carried out, recorded only when something
     in this run failed, or nearly failed, because of the machinery. Give "forbid" (a
     regular expression) only when it matches the faulty form in generated code and
     nothing a correct program would contain; otherwise null.
7. Which listed resources and neighbouring loops' learnings contributed to the result?

Reply with one JSON object and nothing else:

{"classification": "world" | "solution" | null,
 "fault": "specification" | "derivation" | null,
 "reason": "<one sentence>",
 "steer": "<at most three sentences for this loop's next Reflect: what to prioritise, what to avoid>",
 "hold": true | false,
 "question": "<question for the owner>" | null,
 "domain": [{"text": "...", "scope": "portable" | "local"}],
 "execution": [{"text": "...", "forbid": "<regex>" | null}],
 "contributed": ["<resource or loop name>"]}
