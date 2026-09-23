---
title: Principles of ravl
description: The values the library must serve and the constraints it must not violate.
tags: [ravl, principles, axiology]
---

# Principles of `ravl`

These are value judgements, not mechanisms. When a design choice is unclear, it is
settled against this list first, then against the mental model, then in code.

## Whom it serves

1. **The owner of a loop has sole authority over what the loop is.** Intent, verifier,
   execution-mode settings (`lock`, `never-lock`), splitting, merging and retirement
   are the owner's decisions. The owner may be a human, an LLM-driven agent, or a
   parent loop. The loop proposes these changes; it does not make them.
2. **Every capability is justified by a loop someone actually runs.** Capabilities
   built for hypothetical use are not added.
3. **The library assists the owner; it does not replace the owner's judgement.** When
   a loop lacks information, it writes a question for the owner rather than guessing.

## Constraints

4. **No retry inside a run.** One attempt per run. A loop is a tool that a
   longer-running process may call; it is not itself a long-running process.
5. **No writes to another loop's learnings.** A loop writes only into its own
   directory. It reads from siblings and descendants, never from ancestors.
6. **Domain knowledge and execution knowledge are kept separate** in storage, in
   diagnosis, and in how each is used on the next run.
7. **The core names no environment.** No knowledge store, organisation, host or agent
   runtime appears in the core. Surfaces and resources are supplied at run time.
8. **No private user's content enters this repository**, including its history: no
   loop names, domain content or run artefacts from anyone's actual use of `ravl`.

## Behaviour

9. **Read permissions between loops are determined by directory placement** and by
   nothing else.
10. **Every file is human-readable.** Intent and verifier are plain language. Learnings,
    traces and steer use formats a person can open and read without tooling.
11. **Every run records its cost**: tokens by model, wall time, network calls, compute.
    The decision to generate code for a loop is made using these figures.
12. **The core is small.** Work that a capable LLM can perform at run time from a clear
    contract is not implemented as library code. Library code exists for the parts an
    LLM must not be allowed to improvise: the phase contract, the learning store and its
    read/write rules, the verification harness, and the safety boundaries.
13. **Use "LLM", not "AI".** The technical object is a large language model.
