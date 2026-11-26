"""The three prompts the library sends: Act, Learn, and code generation.

Each states a contract and the form of the reply. The wording follows the model's
decision framework; the numbered questions are those of the mental model.
"""

from __future__ import annotations

import json

ACT_REPORT = """{"effects": ["<path of each file you created or changed, relative to the loop directory or absolute; for an effect that is not a file write a short phrase starting with 'action:'>"],
 "summary": "<one or two sentences: what you did and what state you left>",
 "procedure": ["<each command or step you performed that produced the effect, in order, exact enough to repeat>"],
 "resources_used": ["<names from the resource list, and loop names whose learnings you used>"],
 "needs_owner": null}"""


def _checks(results: list[dict]) -> str:
    lines = []
    for number, result in enumerate(results, 1):
        lines.append(f"{number}. [{result['status'].upper()}] {result['text']}")
        if result.get("output") and result["status"] == "fail":
            for line in result["output"].splitlines()[-25:]:
                lines.append(f"      | {line}")
    return "\n".join(lines) or "(no criteria defined)"


def _bullets(items: list[str], empty: str = "(none)") -> str:
    return "\n".join(f"- {item}" for item in items) or empty


def _owner_act(ctx: dict) -> str:
    if not ctx.get("owner_act"):
        return ""
    return f"""# This is a repair attempt ({ctx['attempt']} of {ctx['max_attempts']})
The Act section of the specification holds the owner's implementation. It normally
performs Act on every run with no LLM. It has stopped meeting the verifier, so this run
is yours. Find why it no longer produces the outcome and repair the cause, within what
you are permitted to change. Then run the implementation yourself, exactly as the Act
block states it, so that this run produces the outcome. You may not edit the Act block;
if the repair is a change to it, give the exact change in "needs_owner". After
{ctx['max_attempts']} failed attempts the owner is asked, so a precise account of what
you found is worth more than a guess.

"""


def act(ctx: dict) -> str:
    child_rule = (
        "You may create, edit and remove child loops: subdirectories of the loop directory "
        "that hold their own ravl.md. Before removing one, copy what its domain learnings say "
        "into your summary."
        if ctx["children_editable"] else
        "Do not create, edit or remove child loops.")
    return f"""You are performing the Act phase of one run of a RAVL loop. Act is one attempt:
do the work the intent describes, then report. The runtime runs the verifier after you
finish; a later phase records what was learned.

# Loop directory (your working directory)
{ctx['loop_dir']}

# Specification (ravl.md, written by the owner)
{ctx['spec_raw'].strip()}

# State of the world at Reflect (verifier checks run before you started)
{_checks(ctx['precheck'])}

# Last run
{ctx['last_run']}

# Steer from this loop's last Learn
{ctx['steer'] or '(none)'}

# Owner's answers to earlier questions
{_bullets(ctx['answers'])}

# Domain learnings of this loop
{_bullets(ctx['domain'])}

# Learnings readable from sibling and child loops
{_bullets(ctx['neighbours'])}

# Execution constraints (what you do must satisfy every one)
{_bullets(ctx['constraints'])}

# Resources available to this run
{_bullets(ctx['resources'])}

{_owner_act(ctx)}# Rules
- Do what is needed for every verifier criterion to pass, and no more.
- You may write inside the loop directory and to whatever the intent names. Do not edit
  this loop's ravl.md or config/, and do not write under learnings/ or runs/.
- {child_rule}
- Do not start a run of this or any other loop.
- If the outcome cannot be produced without a decision, a credential or an action that
  only the owner can supply, do not guess and do not work around it. Stop, and state
  exactly what the owner must do in "needs_owner" (a string; otherwise null).
- Do nothing that cannot be undone unless the intent explicitly asks for it.

End your reply with one fenced json block of this form:

```json
{ACT_REPORT}
```
"""


def learn(ctx: dict) -> str:
    return f"""You are performing the Learn phase of one run of a RAVL loop. You classify what
happened and write guidance for later runs. You take no action and change nothing.

# Intent
{ctx['intent'] or '(none written)'}

# Execution mode of this run
{ctx['driver']} ({("the owner's implementation performed Act" if ctx.get('owner_act') else 'generated code performed Act') if ctx['driver'] == 'code' else ('an LLM made a repair attempt because the owner\'s implementation had failed' if ctx.get('owner_act') else 'an LLM performed Act')})

# Verifier before Act
{_checks(ctx['precheck'])}

# Act record
{json.dumps(ctx['act'], indent=2)[:6000]}

# Verifier after Act
{_checks(ctx['postcheck'])}

# Steer written by the previous Learn
{ctx['steer'] or '(none)'}

# Already recorded: domain learnings
{_bullets(ctx['domain'])}

# Already recorded: execution constraints
{_bullets(ctx['constraints'])}

# Decide, in this order
1. Did Verify pass? If it passed, classification is null.
2. If it failed: is the cause WORLD (an external service is down, data is absent, a
   credential has expired, a transient error, something only the owner can supply) or
   SOLUTION (the approach taken was wrong, or something on this side that a repair
   attempt could change is broken: a moved program, a changed path, stale state, a
   defect in the implementation)? Classifying a code failure as SOLUTION starts an
   LLM-driven repair attempt on the next run; classifying it as WORLD does not.
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

{{"classification": "world" | "solution" | null,
 "fault": "specification" | "derivation" | null,
 "reason": "<one sentence>",
 "steer": "<at most three sentences for this loop's next Reflect: what to prioritise, what to avoid>",
 "hold": true | false,
 "question": "<question for the owner>" | null,
 "domain": [{{"text": "...", "scope": "portable" | "local"}}],
 "execution": [{{"text": "...", "forbid": "<regex>" | null}}],
 "contributed": ["<resource or loop name>"]}}
"""


def codegen(ctx: dict) -> str:
    runs = "\n\n".join(
        f"## Run {r['run_id']}\nSummary: {r['summary']}\nProcedure:\n{_bullets(r['procedure'])}\n"
        f"Effects: {', '.join(r['effects']) or '(none recorded)'}"
        for r in ctx["runs"])
    return f"""An LLM has performed the Act phase of this RAVL loop on consecutive runs and the
verifier passed each time. Decide whether the procedure is the same from run to run. If it
is, write a program that performs Act without an LLM.

# Specification (ravl.md)
{ctx['spec_raw'].strip()}

# The passing LLM-driven runs
{runs}

# Execution constraints (the program is rejected if it violates one)
{_bullets(ctx['constraints'])}

# Resources that contributed to the passing runs
{_bullets(ctx['resources'])}

# Contract for the program
- One Python file. It starts with PEP 723 inline metadata:
  # /// script
  # requires-python = ">=3.11"
  # dependencies = []
  # ///
- Dependencies may only be chosen from this whitelist: {ctx['whitelist'] or 'none (standard library only)'}.
- It runs with the loop directory as working directory and takes no arguments.
- It is safe to run when the outcome already partly holds, and it does only what the
  intent describes.
- It exits 0 when it has done the work and non-zero when it could not.
- Its last line of standard output is a JSON object: {{"effects": [...], "summary": "..."}}.
- Input data may differ between runs; encode the procedure, not one run's data.

If the procedure is not the same from run to run, or it needs judgement that code cannot
supply, reply with only this JSON object: {{"repeatable": false, "reason": "<one sentence>"}}

Otherwise reply with the program in one fenced python block and nothing else.
"""
