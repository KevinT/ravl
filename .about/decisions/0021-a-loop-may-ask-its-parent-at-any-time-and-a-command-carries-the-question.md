---
status: Proposed
date: 2026-11-26
deciders: [kevint@gmail.com]
history:
  - "2026-11-26: Proposed — a loop whose checks pass but which lacks a fact only its parent has could not ask for it, and a recorded question reached nobody until someone listed the loops. The owner asked for both to be built. Implemented in 0.6.0"
---

# Decision Record 0021: A loop may ask its parent at any time, and a configured command carries the question

## Context

`0016-learn-may-hold-the-next-act-and-asks-the-owner-once-per-condition` records a
question only when the verifier fails. That covers a loop that is stuck. It does not
cover a loop that is working on an assumption: a loop whose checks pass can be acting on
a guess about its parent's situation (what a thing is, which of two readings is meant,
whether a result is what was wanted), and it had no way to ask.

A recorded question was also only a line in the loop's own files. The model says the
loop does not know who its parent is or where the parent's files are, and that the
parent reads the question. A parent who is a person does not read a directory. In the
first system eight questions were open and none was answered.

## Decision

1. **Act may ask one question in its report**, in a field `ask`, and goes on with the
   work on its best assumption. **Learn may ask about a run that passed.** These are
   recorded whether or not the outcome holds.
2. **Such a question waits until it is answered.** It is not closed when the outcome
   holds or when the failing condition changes, which is what closes a question raised
   by a failure. The same wording is recorded once.
3. **At most `ask.max_open` questions (default 3) wait in one loop.** Past that, a
   question a loop asks of its own accord is not recorded, and the run's trace counts
   it. A question raised by a failing condition is always recorded.
4. **Questions already waiting, and answers already given, are in the Act and Learn
   prompts**, so they are not asked again.
5. **A command the owner configures carries the question.** `[ask] command` in any
   settings file is the argv of a program. For each waiting question not yet sent, it is
   run with one JSON object on standard input: the loop's directory and title, the
   question's id and text, when and in which run it was asked, and the `ravl answer`
   argv that records a reply. Exit status 0 means sent, and the question is not sent
   again. Any other result is recorded on the question and tried again later.
6. **Delivery happens at the end of every run and on `ravl ask [DIR]`**, which sends
   the waiting questions of every loop under a directory and makes no LLM call.
   `ravl ask --list` shows each open question and whether it was sent.
7. **The answer comes back through `ravl answer`**, run by a person or by whatever
   receives the reply. The core does not know where a question went.
8. **An answer makes an LLM-driven loop perform Act once, even when every check
   passes.** The checks cannot see what the answer changes, so without this a loop whose
   outcome holds would never read it. The Act prompt lists the answers given since the
   last Act, and each is marked as read by the run that was shown it.

## Alternatives considered

| Option | Why not |
|---|---|
| Keep asking only on failure | A loop that passes on a wrong assumption never corrects it, and "ask when you do not know" in an intent cannot be acted on. |
| Let a loop ask without limit | A loop that asks every run fills its parent's attention. The first system's unanswered questions show what a parent does with a long list. |
| Build message delivery into the core (a chat service, e-mail) | The core is environment-blind (`0006-core-is-environment-blind`). Which channel reaches a parent is a fact about one installation. |
| Have the command return the answer and wait for it | A person answers in minutes or days. A run cannot wait, and nothing schedules a run when the answer arrives. Sending and answering are separate steps. |
| Deliver only from inside a run | A run confined to its own directory cannot reach a messaging service. `ravl ask` sends from outside the run. |
| **Chosen: `ask` in Act and Learn, a limit per loop, a configured command, `ravl ask`, `ravl answer`** | A loop can ask what only its parent knows, the parent is told once, and the core names no channel. |

## Consequences

- An answer changes nothing until the next run reads it. Whatever receives the reply
  may start a run after recording it; ravl does not.
- A code-driven loop, and a loop whose specification carries its implementation, do not
  act on an answer by itself: generated code and the owner's script take no answers. The
  answer is read when such a loop next makes an LLM-driven attempt.
- A parent that is itself a loop is shown its children's waiting questions at Reflect
  (`A7`). Whether it answers them, and which questions should go past it to a person,
  is not decided here and has not been observed.
- The ask command runs as the user, outside any confinement of Act, with the question
  text on its standard input. The text is written by a model, so a command must treat
  it as data and never pass it to a shell.
- `max_open` is per loop. A tree of many loops can still put many questions to one
  person; a limit across a tree is not built.

## Related

- `0006-core-is-environment-blind`
- `0013-the-llm-is-a-command-the-owner-configures`
- `0016-learn-may-hold-the-next-act-and-asks-the-owner-once-per-condition`
- `0018-a-loop-with-no-verifier-assumes-one-that-its-parent-edits`
