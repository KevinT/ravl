---
status: Accepted
date: 2026-09-23
deciders: [k@wetware.works]
history:
  - 2026-09-23: Accepted — required by the no-bleed rule and by the intent to build in public while using privately
---

# Decision Record 0006: The core is environment-blind

## Context

`ravl` is built in public and used privately, sometimes in settings that must never
inform one another. Its author's own loops benefit from a personal memory system
reached over MCP; other deployments must never see that system. RavlGPT accumulated
integrations for specific services and a specific user's run artefacts inside its
"generic" core.

## Decision

1. The core names **no** knowledge store, organisation, host, scheduler or agent
   runtime.
2. **Surfaces** — a command-line tool, an agent skill, a tool-call interface — are
   derivatives on the boundary of the core. They invoke it; it does not know which one
   did.
3. **Resources** — files, APIs, memory systems over MCP, anything a run may use — are
   handed to a run as an **inventory** by the surface that invoked it. The run reasons
   over the inventory; the core does not carry a catalogue.
4. The **learning store location** is configurable (default: alongside the loop), so a
   deployment decides where knowledge lives without the core knowing why.
5. Nothing that identifies a private user — names, domain content, run artefacts — may
   enter this repository or its history.

## Alternatives considered

| Option | Why not |
|---|---|
| Built-in integrations for common services | Every integration is a place a private user's shape leaks in; a capable model can drive most services from a description in the inventory. |
| Direct coupling to the author's memory system | Would make the library unusable in any setting where that system must not be visible. |
| **Chosen: environment-blind core; surfaces and resources handed in** | Privacy becomes a deployment fact provable from outside the core; the core stays small. |

## Consequences

- The command-line tool, wizard and installer from RavlGPT become *one* surface, built
  only if a real workflow needs it; an agent-session surface may serve the same need.
- Resource relevance is learned per loop (mental model A5) so a blind core does not
  mean every run consults every resource.

## Related

- `0000-rebuild-from-concepts-not-from-code`
- `0003-trust-is-placement`
