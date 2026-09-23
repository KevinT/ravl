---
title: Where ravl sits on the alignment stack
description: The layers of the cognitive alignment stack that ravl occupies, and how the .about/ folder relates to the code.
tags: [ravl, alignment-stack, situates]
---

# Where `ravl` sits on the alignment stack

This repository applies a six-layer **cognitive alignment stack**. The stack is stated
here in full so that a reader with no other context can reason about the `.about/`
contents correctly; the source of the stack is the author's personal cognitive
infrastructure, which is not a dependency of this repository.

```
        [ SPIRIT ]        the ideal state a thing is oriented toward
   ·········(human)······  the human sits at the seam between Spirit and Axiology
        [ AXIOLOGY ]      values and judgement — what matters, what is out of bounds
        [ EPISTEMOLOGY ]  the lenses through which knowledge is acquired and tested
        [ ONTOLOGY ]      the model of what exists — objects, relations, interactions
        [ TECHNOLOGY ]    automation that acts on reality using the maps above it
   ─────────────────────  (map / actuator ── territory)
        [ REALITY ]       the territory itself — singular, continuous, never fully known
```

Two rules govern how the stack is used:

- **Authority flows down; evidence flows up.** Values constrain lenses; lenses
  constrain models; models constrain automation. Results observed in reality inform
  the layers above but never override them.
- **Operate on adjacent layers only.** No single inference spans the whole stack. A
  claim about *what to value* is not settled by a fact about *what the code does*, and
  vice versa; each moves the layer next to it.

## The artefact and its map

- **The Thing** — the `ravl` package, its protocol schemas, its tests — sits at
  **Technology**. It acts on reality (files, APIs, model calls) on behalf of a loop.
- **`.about/`** — this folder — is the Thing seen from **Ontology and up**:
  - [`mental-models/ravl-loop/model.md`](mental-models/ravl-loop/model.md) is the
    **Ontology** of a loop: what a loop *is*, its parts and their relations.
  - The **decision framework** inside that model is the **Epistemology**: the questions
    a loop asks itself, and their order, to turn a run into knowledge.
  - [`principles.md`](principles.md) is the **Axiology**: what the library must never
    do, whom it serves, where authority lies.
  - [`purpose.md`](purpose.md) states what the whole is part of and the ideal it is
    oriented toward — the anchor at the top.

## Where a running loop sits

A loop's own `ravl_loop.md` is a small stack of its own:

| Layer | In a loop |
|---|---|
| Axiology | The **verifier** — the owner's statement of what good looks like |
| Epistemology | The **learnings** — what this loop has come to know, and how it reasons on the next run |
| Ontology | The **intent** — the owner's model of the task and its parts |
| Technology | The **run** — whether performed by a model acting directly or by crystallised code |
| Reality | The **effect** — the file written, the call made, the world changed |

The owner of a loop sits at the seam above its axiology. This is why structural
changes to a loop — its intent, its verifier, whether it may ever be locked, whether it
should be split — are the owner's to decide, and the loop's only to propose.
