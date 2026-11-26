"""The learning store, the read rule set by directory placement, and constraint enforcement."""

from conftest import ACT_WRITE, MAINTAIN, PRODUCE, PROGRAM, act, learn
from ravl import codegen
from ravl.store import readable


def _tree(h):
    """container/{parent/{child}, sibling}, plus a loop in the directory above."""
    tree = h.tmp / "tree"
    above = h.loop("tree", MAINTAIN, parent=h.tmp)          # h.tmp/tree is itself a loop
    parent = h.loop("parent", MAINTAIN, parent=tree)
    sibling = h.loop("sibling", MAINTAIN, parent=tree)
    child = h.loop("child", MAINTAIN, parent=parent)
    grandchild = h.loop("grandchild", MAINTAIN, parent=child)
    return above, parent, sibling, child, grandchild


def test_read_radius_is_siblings_and_children_never_above(h):
    above, parent, sibling, child, grandchild = _tree(h)
    assert readable(parent, 1) == [(sibling, "sibling"), (child, "child")]
    assert readable(parent, 2) == [(sibling, "sibling"), (child, "child"), (grandchild, "descendant")]
    assert readable(parent, 0) == []
    assert readable(child, 1) == [(grandchild, "child")]          # no siblings; the parent is not readable
    assert above not in [p for p, _ in readable(parent, 5)]


def test_learnings_are_stored_apart_and_written_only_in_the_loops_own_directory(h):
    above, parent, sibling, child, _ = _tree(h)
    h.behave({"act": act(["touch flag"], ["flag"]),
              "learn": learn(domain=[{"text": "The flag is removed at midnight.", "scope": "portable"},
                                     {"text": "This loop's flag lives beside ravl.md.", "scope": "local"}],
                             execution=[{"text": "Use pathlib, not os.system.", "forbid": r"os\.system"}])})
    h.run(parent)
    store = h.store(parent)
    assert [d["text"] for d in store.domain()] == ["The flag is removed at midnight.",
                                                   "This loop's flag lives beside ravl.md."]
    assert store.constraints()[0]["forbid"] == r"os\.system"
    assert (parent / "learnings" / "domain" / "learnings.jsonl").is_file()
    assert (parent / "learnings" / "execution" / "constraints.jsonl").is_file()
    assert "The flag is removed at midnight." in store.steer_text("siblings.md")
    assert "lives beside" not in store.steer_text("siblings.md")
    for other in (above, sibling, child):
        assert not (other / "learnings").exists()


def test_sibling_reads_portable_learnings_only_and_ancestors_are_never_shown(h):
    above, parent, sibling, child, _ = _tree(h)
    learned = learn(domain=[{"text": "PORTABLE-FACT", "scope": "portable"},
                            {"text": "LOCAL-FACT", "scope": "local"}])
    h.behave({"act": act(["touch flag"], ["flag"]), "learn": learned})
    h.run(parent)
    h.behave({"act": act(["touch flag"], ["flag"]),
              "learn": learn(domain=[{"text": "ABOVE-FACT", "scope": "portable"}])})
    h.run(above)

    h.behave({"act": act(["touch flag"], ["flag"]), "learn": learn()})
    h.run(sibling)
    prompt = h.prompt("act")
    assert "PORTABLE-FACT" in prompt and "LOCAL-FACT" not in prompt and "ABOVE-FACT" not in prompt

    h.run(child)
    prompt = h.prompt("act")  # a child reads neither its parent nor anything above
    assert "PORTABLE-FACT" not in prompt and "ABOVE-FACT" not in prompt


def test_a_parent_sees_its_childrens_state_and_their_questions_for_the_owner(h):
    _, parent, _, child, _ = _tree(h)
    h.behave({"act": act([], [], needs_owner="x"),
              "learn": learn(classification="world", hold=True, question="CHILD-NEEDS-A-DECISION")})
    h.run(child)
    h.behave({"act": act(["touch flag"], ["flag"]), "learn": learn()})
    h.run(parent)
    prompt = h.prompt("act")
    assert "child loop; last verify: fail" in prompt
    assert "question for you as its owner (q-001): CHILD-NEEDS-A-DECISION" in prompt


def test_subtree_budget_counts_descendants(h):
    _, parent, _, child, _ = _tree(h)
    (parent / "config").mkdir()
    (parent / "config" / "loop.toml").write_text("[budget]\nllm_calls_per_window = 2\n")
    h.behave({"act": act([], []), "learn": learn(classification="solution", fault="derivation")})
    h.run(child)  # two LLM calls spent in the parent's subtree
    trace = h.run(parent)
    assert trace["reflect"]["budget"]["llm_calls_in_window"] == 2
    assert trace["act"]["driver"] == "blocked" and trace["act"]["budget"] is True


def test_generated_code_with_a_dependency_off_the_whitelist_is_rejected(h):
    program = PROGRAM.replace("dependencies = []", 'dependencies = ["requests>=2"]')
    loop = h.loop("produce", PRODUCE)
    h.behave({"act": ACT_WRITE, "learn": learn(), "codegen": program})
    traces = [h.run(loop) for _ in range(3)]
    result = traces[2]["learn"]["codegen"]
    assert result["result"] == "rejected" and "requests" in result["problems"][0]
    assert not (loop / "learnings" / "generated" / "act.py").exists()
    assert h.store(loop).state()["mode"] == "llm"

    (loop / "config").mkdir()
    (loop / "config" / "loop.toml").write_text('[codegen]\nwhitelist = ["requests"]\n')
    assert codegen.validate(codegen.extract_program(program) or "", ["Requests"], []) == []


def test_generated_code_that_violates_an_execution_constraint_never_runs(h):
    loop = h.loop("produce", PRODUCE)
    h.behave({"act": ACT_WRITE, "codegen": PROGRAM,
              "learn": learn(execution=[{"text": "Do not write with pathlib.", "forbid": r"write_text"}])})
    traces = [h.run(loop) for _ in range(3)]
    result = traces[2]["learn"]["codegen"]
    assert result["result"] == "rejected"
    assert result["problems"] == ["violates execution constraint: Do not write with pathlib."]
    assert not (loop / "learnings" / "generated" / "act.py").exists()
    assert (loop / "runs" / traces[2]["run_id"] / "codegen-rejected.py").is_file()


def test_a_constraint_learned_after_generation_stops_existing_code_before_it_runs(h):
    loop = h.loop("produce", PRODUCE)
    h.behave({"act": ACT_WRITE, "learn": learn(), "codegen": PROGRAM})
    for _ in range(3):
        h.run(loop)
    h.store(loop).add_constraints([{"text": "Do not write with pathlib.", "forbid": "write_text"}])
    (loop / "out.txt").unlink()
    h.behave({"act": ACT_WRITE, "learn": learn(classification="solution", fault="derivation")})
    trace = h.run(loop)
    assert trace["act"]["driver"] == "code" and trace["act"]["ok"] is False
    assert not (loop / "out.txt").exists()                       # rejected before running
    assert "code-driven -> LLM-driven" in trace["learn"]["mode_change"]


def test_validation_requires_parseable_code_with_pep723_metadata():
    assert codegen.validate("def broken(:\n", [], [])[0].startswith("does not parse")
    assert codegen.validate("print('x')\n", [], []) == ["no readable PEP 723 `# /// script` block"]
    assert codegen.dependencies(codegen.extract_program(PROGRAM) or "") == []
