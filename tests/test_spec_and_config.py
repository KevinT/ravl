import pytest

from ravl import cli, config, spec


def test_template_from_new_has_intent_and_one_checked_criterion(tmp_path):
    assert cli.main(["new", str(tmp_path / "loop")]) == 0
    s = spec.load(tmp_path / "loop")
    assert s.intent.startswith("Describe the outcome")
    assert [c.check for c in s.criteria] == ["false"]
    assert cli.main(["new", str(tmp_path / "loop")]) == 2  # never overwrites a specification


def test_criteria_with_and_without_checks(tmp_path):
    (tmp_path / "ravl.md").write_text(
        "# T\n\n## Intent\n\nSomething.\n\n## Verifier\n\n"
        "- First criterion\n  continues here.\n  ```check\n  test -f a\n  test -f b\n  ```\n"
        "- Second has no check.\n"
        "- Third.\n  ```sh\n  ## not a heading, not a check\n  ```\n\n## Notes\n\n- not a criterion\n")
    s = spec.load(tmp_path)
    assert [c.text for c in s.criteria] == ["First criterion continues here.", "Second has no check.", "Third."]
    assert s.criteria[0].check == "test -f a\ntest -f b"
    assert s.criteria[1].check is None and s.criteria[2].check is None


def test_criterion_identity_follows_its_text_not_its_position(tmp_path):
    (tmp_path / "ravl.md").write_text("# T\n## Verifier\n- alpha\n- beta\n")
    first = {c.text: c.id for c in spec.load(tmp_path).criteria}
    (tmp_path / "ravl.md").write_text("# T\n## Verifier\n- beta\n- alpha\n")
    assert {c.text: c.id for c in spec.load(tmp_path).criteria} == first


def test_missing_specification_is_an_error(tmp_path):
    with pytest.raises(spec.SpecError):
        spec.load(tmp_path)


def test_three_levels_later_overrides_earlier(tmp_path):
    user = tmp_path / "user.toml"
    user.write_text('[llm]\ncommand = ["user-llm"]\n[budget]\nllm_calls_per_window = 5\n')
    tree = tmp_path / "tree"
    loop = tree / "group" / "loop"
    (loop / "config").mkdir(parents=True)
    (tree / "ravl.toml").write_text('[budget]\nllm_calls_per_window = 7\n[resources]\ndocs = "the docs"\n')
    (loop / "config" / "loop.toml").write_text("[read]\nradius = 2\n")
    cfg = config.load(loop, user)
    assert cfg["llm"]["command"] == ["user-llm"]
    assert cfg["budget"]["llm_calls_per_window"] == 7
    assert cfg["read"]["radius"] == 2
    assert cfg["resources"] == {"docs": "the docs"}
    assert cfg["mode"] == "learned"


def test_tree_may_require_a_newer_library(tmp_path):
    (tmp_path / "ravl.toml").write_text('min_version = "99.0.0"\n')
    with pytest.raises(config.ConfigError, match="uv tool upgrade ravl"):
        config.load(tmp_path, tmp_path / "none.toml")


def test_owner_mode_setting_is_validated(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "mode").write_text("sometimes\n")
    with pytest.raises(config.ConfigError):
        config.owner_mode(tmp_path)
