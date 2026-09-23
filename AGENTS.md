# Agent instructions

You are working in `ravl`. Before changing anything, read in this order:

1. [`.about/purpose.md`](.about/purpose.md) — what this is a part of; trust boundaries.
2. [`.about/mental-models/ravl-loop/model.md`](.about/mental-models/ravl-loop/model.md)
   — the ontology of a loop and the decision framework. Code is judged against it; if
   they disagree, the model wins and the code is fixed.
3. [`.about/principles.md`](.about/principles.md) — what the library must never do.
4. [`.about/decisions/README.md`](.about/decisions/README.md) — decisions in force.
   Walk up the tree from any file to collect every record that governs it.
5. [`specifications/first-loop.md`](specifications/first-loop.md) — what is being built
   now, in what order, and the kill criterion.
6. [`specifications/reference/ravlgpt-guardrails.md`](specifications/reference/ravlgpt-guardrails.md)
   — before building any component, check whether RavlGPT had one and apply the three
   tests. Read RavlGPT for what it learned; never copy its code.

## Conventions

- **Write in plain technical language.** Name the mechanism. No metaphor, no
  personification of software, no rhetorical constructions. If a sentence has to be
  decoded, rewrite it.
- **`.about/` is the map; the code is the thing.** `purpose.md` answers "what is this
  a part of"; `README.md` answers "what are its parts". Do not duplicate one into the
  other; point.
- **Decide before building.** A design change gets a decision record in
  `.about/decisions/` (Proposed) before code. Records are numbered from `0000` per
  scope and referenced by full slug.
- **Small core.** Anything a capable model can do at run time from a clear contract is
  not framework code. Ask "must a model be prevented from improvising this?" — only if
  yes does it belong in the library.
- **No private users in the repo.** No loop names, domain content or run artefacts from
  anyone's actual use of `ravl`, in files or in history. Examples are public and
  invented.
- **Say "LLM", not "AI".**
- **Specification is driven by loops from here.** A run that contradicts the model
  produces a decision record and a model edit, not a workaround in code. Open
  questions go to `specifications/speculative/` first.
- **Tests reach the core.** The phase contract, learning store, trust topology,
  verification harness and constraint enforcement are covered before any surface is.
