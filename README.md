# ravl

**Reflect · Act · Verify · Learn** — a small library and protocol for loops that run
once, check their own result, and leave guidance for their next run.

> Pre-release. There is no code yet; the repository currently holds the agreed model
> the code will be built against. Read the model first — it is short, and everything
> else follows from it.

## Start here

| Question | Read |
|---|---|
| What is this a part of, and what are its trust boundaries? | [`.about/purpose.md`](.about/purpose.md) |
| How do I reason about a loop? | [`.about/mental-models/ravl-loop/model.md`](.about/mental-models/ravl-loop/model.md) |
| What must the library never do? | [`.about/principles.md`](.about/principles.md) |
| Where does it sit on the alignment stack, and what is that? | [`.about/situates.md`](.about/situates.md) |
| Why was it decided this way? | [`.about/decisions/`](.about/decisions/README.md) |
| I am an agent working in this repo | [`AGENTS.md`](AGENTS.md) |

## Lineage

`ravl` re-derives the concepts first developed in
[KevinT/RavlGPT](https://github.com/KevinT/RavlGPT). That repository is kept whole as
evidence; no code is ported from it
([`0000-rebuild-from-concepts-not-from-code`](.about/decisions/0000-rebuild-from-concepts-not-from-code.md)).

## Licence

[Mozilla Public License 2.0](LICENSE).
