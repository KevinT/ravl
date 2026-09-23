---
title: Where ravl sits on the alignment stack
description: The layers of the cognitive alignment stack that ravl occupies, and how the .about/ folder relates to the code.
tags: [ravl, alignment-stack, situates]
---

# Where `ravl` sits on the alignment stack

This repository applies a six-layer **cognitive alignment stack**. The stack is stated
here in full so that a reader with no other context can interpret the `.about/` folder.
The stack comes from the author's personal cognitive infrastructure, which is not a
dependency of this repository.

```
        [ SPIRIT ]        the ideal state a thing is oriented toward
   ·········(human)······  the human sits between Spirit and Axiology
        [ AXIOLOGY ]      values and judgement: what matters, what is out of bounds
        [ EPISTEMOLOGY ]  the methods by which knowledge is acquired and tested
        [ ONTOLOGY ]      the model of what exists: objects, relations, interactions
        [ TECHNOLOGY ]    automation that acts on reality using the layers above it
   ─────────────────────
        [ REALITY ]       the territory itself; singular, continuous, never fully known
```

Two rules govern the stack:

- **Constraints propagate downward; evidence propagates upward.** Values constrain
  methods; methods constrain models; models constrain automation. Observations from
  reality inform the layers above but do not override them.
- **Each inference connects adjacent layers only.** A claim about what to value is not
  settled by a fact about what the code does, and the reverse. Each layer is changed by
  the layer next to it.

## The artefact and its description

- **The artefact** — the `ravl` package, its protocol schemas, its tests — is at
  **Technology**. It acts on reality (files, APIs, LLM calls) on behalf of a loop.
- **`.about/`** — this folder — describes the artefact from **Ontology** upward:
  - [`mental-models/ravl-loop/model.md`](mental-models/ravl-loop/model.md) is the
    **Ontology**: what a loop is, its parts, and their relations.
  - The **decision framework** in that model is the **Epistemology**: the ordered
    questions by which a loop turns a run into recorded knowledge.
  - [`principles.md`](principles.md) is the **Axiology**: what the library must not do,
    whom it serves, who has authority over what.
  - [`purpose.md`](purpose.md) states what the whole is part of and the outcome it is
    built for.

## The layers inside a running loop

A loop's own specification and state also map onto the stack:

| Layer | In a loop |
|---|---|
| Axiology | The **verifier**: the owner's criteria for a correct result |
| Epistemology | The **learnings**: what this loop has recorded and how the next run uses it |
| Ontology | The **intent**: the owner's description of the task and its parts |
| Technology | The **run**: performed by an LLM acting directly or by generated code |
| Reality | The **effect**: the file written, the call made, the change in the world |

The owner occupies the position above the verifier. This is why changes to a loop's
intent, verifier, execution-mode setting, or structure are made by the owner, and why
the loop's role is limited to proposing them.
