---
title: Principles of ravl
description: The values the library must serve and the lines it must not cross — the axiology of ravl.
tags: [ravl, principles, axiology]
---

# Principles of `ravl`

These are judgements, not mechanisms. When a design choice is unclear, it is settled
here first, then in the mental model, then in code.

## Whom it serves

1. **The owner of a loop is sovereign over what the loop is.** Intent, verifier,
   gradient pins (`lock` / `never-lock`), decomposition and retirement belong to the
   owner — a human, a tool-using agent, or a parent loop. The loop proposes; it never
   decides these for itself.
2. **Built for a real purpose first, a hypothetical never.** Every capability must trace
   to a loop someone actually runs. Speculative generality is the weight this project
   was rebuilt to shed.
3. **Augment, do not replace.** A loop makes its owner faster and better informed. It
   surfaces what it does not know as questions for the owner rather than guessing past
   them.

## What it must never do

4. **Never retry inside a run.** One attempt per run is the unit of feedback. A loop is
   a tool that longer-running processes call, not a long-running process itself.
5. **Never write another loop's learnings.** Self-write only. Reading is sideways and
   down, never up.
6. **Never mix the two kinds of knowledge.** What a loop learns about its *domain* and
   what it learns about *making its own machinery work* are kept apart in storage, in
   diagnosis and in how they steer the next run.
7. **Never know its environment.** No knowledge store, organisation, host or agent
   runtime is named in the core. Surfaces and resources are handed in.
8. **Never leak a user.** No private user's loop names, domain content or run artefacts
   may enter this repository, including its history.

## How it must behave

9. **Trust is placement.** Which loops may inform each other is decided by where they
   sit on the filesystem, and by nothing else.
10. **Human-readable everything.** Intent and verifier in plain language; learnings,
    traces and steer in formats a person can open and understand without tooling.
11. **Cost is a first-class observation.** Every run records what it consumed. The case
    for crystallising a loop into code is made with these numbers.
12. **The core is small.** Anything that a capable model can do at run time from a clear
    contract is not written as framework code. Framework code exists for the things a
    model must not be trusted to improvise: the phase contract, the learning store and
    its trust topology, the verification harness, the safety boundaries.
13. **Say "LLM", not "AI".** The object is a large language model; the library
    describes what it does with one.
