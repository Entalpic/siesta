# Copyright 2025 Entalpic
from pathlib import Path

from siesta.utils.agentic import (
    _build_substitutions,
    _normalize_package_name,
    copy_agentic_skill,
    render_reference_template,
    setup_agentic_exploration,
    write_agentic_reference_files,
)


def test_normalize_package_name_replaces_hyphens():
    assert _normalize_package_name("my-cool-project") == "my_cool_project"


def test_normalize_package_name_leaves_clean_name():
    assert _normalize_package_name("clean") == "clean"


def test_build_substitutions_fills_known_slots():
    subs = _build_substitutions("foo-bar", tests=True, docs=True)
    assert subs["[🙋 Project name]"] == "foo-bar"
    assert subs["[🙋 package name]"] == "foo_bar"
    assert subs["[🙋 test command]"] == "uv run pytest"
    # docs command line is non-empty (exact wording is implementation detail).
    assert subs["[🙋 docs command]"]


def test_build_substitutions_drops_lines_when_feature_disabled():
    # When tests/docs are disabled the placeholder maps to None — the line gets dropped.
    subs = _build_substitutions("foo", tests=False, docs=False)
    assert subs["[🙋 test command]"] is None
    assert subs["[🙋 docs command]"] is None


def test_render_reference_template_substitutes_known_placeholders():
    text = "# [🙋 Project name]\nsrc/[🙋 package name]/\n"
    out = render_reference_template(
        text,
        {"[🙋 Project name]": "foo-bar", "[🙋 package name]": "foo_bar"},
    )
    assert out == "# foo-bar\nsrc/foo_bar/\n"


def test_render_reference_template_drops_lines_for_none_values():
    # Lines containing a None-mapped placeholder are removed entirely.
    text = "keep this line\n- Test: [🙋 test command]\n- Lint: ruff\n"
    out = render_reference_template(text, {"[🙋 test command]": None})
    assert "Test:" not in out
    assert "keep this line" in out
    assert "Lint: ruff" in out


def test_render_reference_template_preserves_unknown_placeholders():
    # Researcher-owned placeholders must round-trip unchanged.
    text = "[🙋 One sentence: what this project is investigating.]\n"
    out = render_reference_template(text, {"[🙋 Project name]": "foo"})
    assert out == text


def test_write_agentic_reference_files_creates_human_and_agent(tmp_path):
    subs = _build_substitutions("my-proj", tests=True, docs=True)
    write_agentic_reference_files(tmp_path, subs, overwrite=False)

    human = tmp_path / "Human.md"
    agent = tmp_path / "AGENT.md"
    assert human.exists()
    assert agent.exists()

    agent_text = agent.read_text()
    # Project name substituted.
    assert "# my-proj" in agent_text
    # Package name substituted.
    assert "src/my_proj/" in agent_text
    # Test command filled.
    assert "uv run pytest" in agent_text
    # Researcher-owned placeholders preserved.
    assert "🙋" in agent_text


def test_write_agentic_reference_files_drops_lines_when_disabled(tmp_path):
    subs = _build_substitutions("my-proj", tests=False, docs=False)
    write_agentic_reference_files(tmp_path, subs, overwrite=False)

    agent_text = (tmp_path / "AGENT.md").read_text()
    # Disabled feature lines should be gone (the placeholder bullet itself is dropped).
    assert "[🙋 test command]" not in agent_text
    assert "[🙋 docs command]" not in agent_text
    # And the substituted version should not appear either.
    assert "Test: `uv run pytest`" not in agent_text


def test_copy_agentic_skill_creates_expected_layout(tmp_path):
    copy_agentic_skill(tmp_path, overwrite=False)
    skill_dir = tmp_path / ".claude" / "skills" / "agentic-exploration"
    assert (skill_dir / "SKILL.md").exists()
    assert (skill_dir / "doc-hierarchy.md").exists()
    assert (skill_dir / "references" / "human.md").exists()
    assert (skill_dir / "references" / "agent.md").exists()
    # Templates are intentionally bundled (lifecycle scaffolds, not init-time files).
    assert (skill_dir / "templates").is_dir()
    template_names = {p.name for p in (skill_dir / "templates").iterdir()}
    assert "research-plan-template.md" in template_names
    assert "plan-template.md" in template_names
    assert "todo-template.md" in template_names
    assert "notes-template.md" in template_names
    assert "handoff-template.md" in template_names


def test_setup_agentic_exploration_no_lifecycle_files_at_init(tmp_path):
    setup_agentic_exploration(
        project_path=tmp_path,
        project_name="demo",
        tests=True,
        docs=True,
    )
    # Init-time surface only — lifecycle docs are NOT pre-created.
    for lifecycle in (
        "research_plan.md",
        "plan.md",
        "TODO.md",
        "notes.md",
        "handoff.md",
    ):
        assert not (tmp_path / lifecycle).exists(), (
            f"lifecycle file {lifecycle} must not be created at init"
        )
    assert (tmp_path / "Human.md").exists()
    assert (tmp_path / "AGENT.md").exists()
    assert (
        tmp_path / ".claude" / "skills" / "agentic-exploration" / "SKILL.md"
    ).exists()


def test_setup_agentic_exploration_accepts_str_path(tmp_path: Path):
    # resolve_path accepts both Path and str — make sure the public API does too.
    setup_agentic_exploration(
        project_path=str(tmp_path),
        project_name="demo",
        tests=True,
        docs=True,
    )
    assert (tmp_path / "AGENT.md").exists()
