---
title: Purpose of ravl
description: What the ravl repository is a part of, its trust boundaries, and why it exists as a distinct thing.
tags: [ravl, purpose, alignment-stack]
---

# Purpose of `ravl`

`ravl` is a small, stand-alone library and protocol for **learning loops**: units of
work that run once, check their own result against declared criteria, and leave
addressed guidance for their next run. The name is the protocol — Reflect, Act,
Verify, Learn. It is for outcomes that recur; each time an outcome is produced again,
the loop that produces it should cost less and fail less than the time before.

## What this repository is a part of

- **Upstream — the concepts.** The RAVL protocol and its vision were first worked out
  in [KevinT/RavlGPT](https://github.com/KevinT/RavlGPT) (2025–2026). That repository is
  kept whole as evidence: its documents, run artefacts and self-diagnoses show what the
  idea achieved and where it fell short. `ravl` re-derives the concepts against a stated
  mental model; it ports none of the earlier code.
- **Downstream — anyone's loops.** `ravl` is consumed by people and by LLM-driven agents
  who write loops in plain language and run them. The primary customer is the author,
  working backwards from real purposes. It is built in public so others can contribute.
- **Sideways — distribution surfaces.** A command-line tool, an agent skill, a
  tool-call interface: each is a *surface* through which the core is used, derived from
  the core, never part of it. The core receives no information about which surface invoked it.

## Trust boundaries

The core is **environment-blind**. It has no knowledge of any particular knowledge
store, organisation, host, or agent runtime. Resources a run may use (files, APIs, a
memory system reached over MCP) are handed to the run as an inventory by the surface
that invoked it.

Trust between loops is **inferred from where they sit on the filesystem**, not
configured. A loop reads learnings from its siblings and descendants, never from
above, and writes only its own. Two groups of loops that must never inform each other
are simply never placed under a common parent. Nothing about any private user of this
library — no names, no domain content, no run artefacts — belongs in this repository.

## Why it exists as a distinct thing

The idea is separable from any one memory system, agent framework or scheduler, and is
useful to all of them: a bounded feedback cycle that a longer-running agent can call as
a tool. Keeping it distinct keeps it small, keeps the trust story provable, and lets it
be shared without sharing anything it was used for.

## Where to read next

- How to reason about a loop: [`mental-models/ravl-loop/model.md`](mental-models/ravl-loop/model.md)
- Where this artefact sits on the alignment stack: [`situates.md`](situates.md)
- How the library must behave: [`principles.md`](principles.md)
- Decisions in force: [`decisions/`](decisions/README.md)
- What is in the repository and how to run it: [`../README.md`](../README.md)
