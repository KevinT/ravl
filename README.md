# ravl

**Reflect · Act · Verify · Learn** — a small library and protocol for loops that run
once, check their own result, and leave guidance for their next run. For outcomes that
recur: each run should cost less and fail less than the one before.

> Pre-release. There is no code yet; the repository holds the agreed model the code
> will be built against, and the specification of the first loop. Read the model first.

## Start here

| Question | Read |
|---|---|
| What is this a part of, and what are its trust boundaries? | [`.about/purpose.md`](.about/purpose.md) |
| How do I reason about a loop? | [`.about/mental-models/ravl-loop/model.md`](.about/mental-models/ravl-loop/model.md) |
| What must the library never do? | [`.about/principles.md`](.about/principles.md) |
| Where does it sit on the alignment stack, and what is that? | [`.about/situates.md`](.about/situates.md) |
| Why was it decided this way? | [`.about/decisions/`](.about/decisions/README.md) |
| What gets built first, and what is the kill criterion? | [`specifications/first-loop.md`](specifications/first-loop.md) |
| What is carried from RavlGPT, adapted, or left behind? | [`specifications/reference/ravlgpt-guardrails.md`](specifications/reference/ravlgpt-guardrails.md) |
| How is it installed and run? | [`specifications/speculative/proposals/distribution.md`](specifications/speculative/proposals/distribution.md) (proposal) |
| I am an agent working in this repo | [`AGENTS.md`](AGENTS.md) |

## Repository layout

```
.about/            purpose, principles, position on the stack, the mental model, decisions
specifications/    what is being built next
  first-loop.md    the first loop and the build order for the runner
  reference/       guardrails for consulting RavlGPT
  speculative/     proposals not yet decided; promoted to .about/decisions/ when resolved
```

## Lineage

`ravl` re-derives the concepts first developed in
[KevinT/RavlGPT](https://github.com/KevinT/RavlGPT). That repository is kept whole as
evidence; no code is ported from it
([`0000-rebuild-from-concepts-not-from-code`](.about/decisions/0000-rebuild-from-concepts-not-from-code.md)).

## Licence

[Mozilla Public License 2.0](LICENSE).
