# RavlGPT guardrails: what comes with, what is adapted, what is left

RavlGPT (`github.com/KevinT/RavlGPT`, 2025–Jan 2026) is the upstream of `ravl`. Much of
it was arrived at by running loops and correcting what failed, so it holds evidence
that would be expensive to regenerate. It also holds ~30k lines that compensated for
model limits that no longer apply, and integration code specific to the author's past
uses. This document is the rule for consulting it during implementation.

## The rule

Before building any component, check whether RavlGPT had one. If it did, classify it
with the three tests below, in order, and record the classification in the table at
the bottom of this file. Read RavlGPT for *what it learned*, never for code to copy.

**Test 1 — Does it violate an axiom or a decision record?** If yes: **leave**. Note
what it was for; the need may be real even though the mechanism is wrong.

**Test 2 — Did it exist to compensate for a model that could not interpret plain
language, hold context, or use tools?** If yes: **leave**. The model now does that work.

**Test 3 — Does it encode something learned from running real loops?** Prompt wording
that was corrected after a failure, a verification rule added after a false pass, a
constraint discovered the hard way. If yes: **adapt** — re-express it against the
current model, in the current vocabulary, and record where it came from.

Anything that passes all three tests unchanged **comes with** as a concept. No Python
is ported.

## Classification of RavlGPT components

Sizes are lines of Python at the last commit, for scale.

### Comes with (as concepts, re-derived)

| Component | What it is | Where it lands in `ravl` |
|---|---|---|
| `docs/RAVL_VISION.md`, `docs/RAVL_PROTOCOL.md` | The four phases, one attempt per run, learning across runs | Model, A1–A3 |
| `docs/learning_separation.md` | Domain vs execution learning, stored apart | Model, A4; decision 0007 |
| `docs/free_form_interpretation.md` | Plain-language spec is the source; structure is inferred | Model, A1 |
| `docs/health_checks.md` and the `execution_health_check` loop | A loop whose subject is the framework's own runs | First candidate for a `ravl.py` example once the runner exists |
| Whitelist of allowed packages for generated code | Safety boundary on generated code | Kept, applied to PEP 723 declarations (distribution proposal) |
| Lock a verified attempt and run it unchanged | Owner-set execution mode | Model, A2 `lock`; decision 0002 |
| Known-knowns / known-unknowns | Facts learned; questions for the owner | Model, A4 (execution learnings) and A6 (steer to owner) |

### Adapt (something was learned; the mechanism changes)

| Component | Size | What it learned | What changes |
|---|---|---|---|
| Seven prompt templates (`act_phase`, `verify_phase`, `synthesize_run`, `learn_regeneration_analysis`, `synthesize_domain_learnings`, `interpret_freeform_markdown`, `data_ingestion_codegen`) | — | Wording corrected over many runs; what to ask Verify to judge; what Learn must classify | Read each before writing the equivalent phase prompt. Drop the hardcoded field names (RACI, Notion, Google) they accumulated. The Learn prompt must be restructured around the world/solution classification, which the originals did not make. |
| `execution_learning_manager.py`, `loop_learning_manager.py` | 499, 482 | The storage split and the access pattern | Storage format may be reused as a starting point; the enforcement step (execution learning → constraint on generated code) was missing and is the point of decision 0007. |
| `dependency_validator.py` | 489 | Which packages generated code tried to import and were refused | Whitelist contents come with. The validator becomes a check on PEP 723 metadata, not on import statements. |
| `markdown_parser.py` | 523 | Which sections a loop spec turned out to need | Section list informs the `ravl.md` template. The parser is replaced by giving the model the file. |
| `prompt_normalizer.py` | 452 | Deduplicating 40–70% of tokens across phase prompts | The saving is real. Re-measure with the current model before deciding whether any of it is needed; models with larger context may make it irrelevant. |
| Cost tracking inside the LLM provider layer | — | Which figures were worth recording | Becomes the cost ledger in the trace (A6, A9). |
| `ravl_list.py`, `loop_discovery.py` | 754, 1042 | What a person wants to see about a set of loops at a glance | Informs `ravl list` output. Discovery by scanning for `ravl.*` replaces the registry logic. |
| Verification that a claimed file write actually happened | — | Models report success without producing the effect | Becomes a trace check: effect claimed by Act is confirmed by the runtime before Verify runs. |

### Leave

| Component | Size | Reason (test that failed) |
|---|---|---|
| `dsl_inference_engine.py` | 859 | Test 2. Regex keyword matching to infer structure from a spec (`if 'notion' in act_lower`). The model reads the spec. |
| `run_markdown_ravl.py`, `markdown_ravl_executor.py`, `act_orchestrator.py`, `reflection_orchestrator.py`, `learning_coordinator.py` | 1142, 1081, 441, 422, 485 | Test 2. Layered execution paths (freeform → enhanced → DSL → codegen → cache) that existed because no single path worked reliably. One path now. |
| `data_ingress_executor.py` | 855 | Test 1 (A5). Encodes specific data sources into the framework. |
| `integrations/` (Google Docs/Sheets/Slides trackers, HiBob, ClickUp) | ~2k | Test 1 (A5, decision 0006). Resources belong to the surface or the spec, not the core. |
| `venv_manager.py` | 435 | Test 1 (distribution proposal). Framework-managed environments inside the consumer tree. |
| `ravl_setup.py`, `ravl_clone.py`, `install.sh`, wrapper and symlink | ~2.2k | Test 1 (distribution proposal). Submodule distribution. |
| `ravl-sync-claude`, `ravl-sync-opencode` | — | Test 1 (distribution proposal). Replaced by a shipped protocol document and `ravl mcp`. |
| `config_service.py` | 562 | Test 2 in part, Test 1 in part. Multi-source config with environment variables. Replaced by the three-level resolution in the distribution proposal. |
| Mixins and helper pattern (`MIXINS.md`, `HELPER_PATTERN.md`, `PATH_DETECTION_PATTERNS.md`) | — | Test 2. Internal structure of code that is not being carried. |
| Loop learnings and run artefacts under `ravl_loops/` | — | Test 1 (no private content in the repository). Evidence only; read, never copy. |

### Not yet classified

Add rows here when a component is encountered that is not listed above. Classify it
before building its replacement.

## What RavlGPT's own evidence says to look at first

The self-diagnosis at
`ravl_loops/ravl/framework/health_checks/child_loops/execution_health_check/learnings/latest_run.json`
(12 Jan 2026) records a learning that was captured and then ignored for seven
consecutive attempts. Decision 0007 is the response. When the first loop reaches the
point of generating code, this file is the test case: the same class of failure must be
impossible.
