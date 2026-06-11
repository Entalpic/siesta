# Copyright 2025 Entalpic
"""Unit tests for siesta.utils.agents — catalog discovery, translation, path
helpers, selection resolution, and conflict-aware writers.
"""

import sys
from pathlib import Path

import pytest

from siesta.utils.agents import (
    DEFAULT_CONSTITUTION,
    IMPORT_LINE,
    _display_path,
    _split_frontmatter,
    _split_globs,
    asset_search_paths,
    available_constitutions,
    available_rules,
    available_skills,
    base_dir,
    collect_confirmed_removals,
    constitution_paths,
    detect_installed_rules,
    detect_installed_skills,
    install_constitution,
    install_quickstart,
    install_rule,
    install_skill,
    load_quickstart,
    mdc_to_claude,
    remove_constitution,
    remove_constitution_file,
    remove_path,
    remove_rule,
    remove_skill,
    resolve_providers,
    resolve_remove_selection,
    resolve_scope,
    resolve_selection,
    rule_target,
    scope_display_label,
    skill_target,
    write_dir,
    write_file,
)
from siesta.utils.common import logger

# ---------------------------------------------------------------------------
# Catalog discovery
# ---------------------------------------------------------------------------


def test_available_skills_returns_list():
    skills = available_skills()
    assert isinstance(skills, list)
    assert "grill-with-docs" in skills


def test_available_rules_returns_list():
    rules = available_rules()
    assert isinstance(rules, list)
    assert "python-docstrings" in rules
    assert "mirror-providers" in rules
    # Names are stems — no extension.
    for name in rules:
        assert not name.endswith(".mdc")


def test_available_constitutions_returns_list():
    constitutions = available_constitutions()
    assert isinstance(constitutions, list)
    assert DEFAULT_CONSTITUTION in constitutions


# ---------------------------------------------------------------------------
# Provider + scope resolution
# ---------------------------------------------------------------------------


class TestResolveProviders:
    def test_both_flag(self):
        assert resolve_providers(False, False, True) == ["cursor", "claude"]

    def test_default_both_when_no_flags(self):
        assert resolve_providers(False, False, False) == ["cursor", "claude"]

    def test_cursor_only(self):
        assert resolve_providers(True, False, False) == ["cursor"]

    def test_claude_only(self):
        assert resolve_providers(False, True, False) == ["claude"]

    def test_both_explicit_flags(self):
        # --cursor --claude without --both also means both
        assert resolve_providers(True, True, False) == ["cursor", "claude"]


class TestResolveScope:
    def test_default_local(self):
        assert resolve_scope(False, False) == "local"

    def test_local_flag(self):
        assert resolve_scope(True, False) == "local"

    def test_global_flag(self):
        assert resolve_scope(False, True) == "global"

    def test_both_flags_aborts(self):
        with pytest.raises(SystemExit):
            resolve_scope(True, True)


class TestBaseDir:
    def test_local_cursor(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert base_dir("cursor", "local") == tmp_path / ".cursor"

    def test_local_claude(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert base_dir("claude", "local") == tmp_path / ".claude"

    def test_global_cursor(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert base_dir("cursor", "global") == tmp_path / ".cursor"

    def test_global_claude(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert base_dir("claude", "global") == tmp_path / ".claude"


# ---------------------------------------------------------------------------
# Target paths
# ---------------------------------------------------------------------------


class TestTargetPaths:
    def test_display_path_is_relative_to_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        dest = tmp_path / ".cursor" / "rules" / "python-docstrings.mdc"
        assert _display_path(dest) == str(
            Path(".cursor") / "rules" / "python-docstrings.mdc"
        )

    def test_display_path_walks_up_to_paths_outside_cwd(self, tmp_path, monkeypatch):
        repo = tmp_path / "repo"
        repo.mkdir()
        monkeypatch.chdir(repo)
        dest = tmp_path / ".claude" / "skills" / "grill-with-docs"
        assert _display_path(dest) == str(
            Path("..") / ".claude" / "skills" / "grill-with-docs"
        )

    def test_skill_target_cursor_local(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        dest = skill_target("cursor", "local", "grill-with-docs")
        assert dest == tmp_path / ".cursor" / "skills" / "grill-with-docs"

    def test_skill_target_claude_global(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        dest = skill_target("claude", "global", "grill-with-docs")
        assert dest == tmp_path / ".claude" / "skills" / "grill-with-docs"

    def test_rule_target_cursor_is_mdc(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        dest = rule_target("cursor", "local", "python-docstrings")
        assert dest.suffix == ".mdc"
        assert dest.name == "python-docstrings.mdc"

    def test_rule_target_claude_is_md(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        dest = rule_target("claude", "local", "python-docstrings")
        assert dest.suffix == ".md"
        assert dest.name == "python-docstrings.md"


# ---------------------------------------------------------------------------
# .mdc -> Claude .md translation
# ---------------------------------------------------------------------------


class TestSplitFrontmatter:
    def test_no_frontmatter(self):
        fm, body = _split_frontmatter("# Hello\nworld")
        assert fm == {}
        assert body == "# Hello\nworld"

    def test_parses_frontmatter(self):
        text = (
            "---\ndescription: foo\nglobs: '**/*.py'\nalwaysApply: false\n---\n\n# Body"
        )
        fm, body = _split_frontmatter(text)
        assert fm["description"] == "foo"
        assert fm["globs"] == "**/*.py"
        assert fm["alwaysApply"] is False
        assert body == "# Body"

    def test_incomplete_fence_returns_empty(self):
        text = "---\nnot closed"
        fm, body = _split_frontmatter(text)
        assert fm == {}


class TestMdcToClaude:
    def test_alwaysapply_true_drops_paths(self):
        text = "---\ndescription: x\nalwaysApply: true\n---\n\n# Body"
        result = mdc_to_claude(text)
        assert "paths:" not in result
        assert "# Body" in result

    def test_globs_string_becomes_paths_list(self):
        text = (
            "---\ndescription: x\nglobs: '**/*.py'\nalwaysApply: false\n---\n\n# Body"
        )
        result = mdc_to_claude(text)
        assert "paths:" in result
        assert '"**/*.py"' in result
        assert "description" not in result
        assert "alwaysApply" not in result

    def test_globs_comma_separated_splits(self):
        text = (
            "---\ndescription: x\n"
            "globs: .cursor/rules/**,.claude/rules/**\n"
            "alwaysApply: false\n---\n\n# Body"
        )
        result = mdc_to_claude(text)
        assert '".cursor/rules/**"' in result
        assert '".claude/rules/**"' in result

    def test_no_globs_alwaysapply_false_drops_paths(self):
        text = "---\ndescription: x\nalwaysApply: false\n---\n\n# Body"
        result = mdc_to_claude(text)
        assert "paths:" not in result

    def test_no_frontmatter_passes_through(self):
        text = "# Just a rule"
        assert mdc_to_claude(text) == "# Just a rule"

    def test_real_python_docstrings_rule(self):
        """The bundled python-docstrings rule should translate to paths."""
        from importlib.resources import files

        src = files("siesta") / "agents_assets" / "rules" / "python-docstrings.mdc"
        raw = Path(str(src)).read_text(encoding="utf-8")
        result = mdc_to_claude(raw)
        assert "paths:" in result
        assert '"**/*.py"' in result
        assert "alwaysApply" not in result
        assert "description" not in result

    def test_brace_glob_kept_intact(self):
        # A single brace-expansion glob must not be split on its inner comma.
        text = "---\nglobs: '**/*.{py,js}'\nalwaysApply: false\n---\n\n# Body"
        result = mdc_to_claude(text)
        fm, _ = _split_frontmatter(result)
        assert fm["paths"] == ["**/*.{py,js}"]

    def test_brace_glob_mixed_with_list(self):
        # Top-level commas separate; brace groups stay intact.
        text = "---\nglobs: 'a.py,**/*.{ts,tsx}'\nalwaysApply: false\n---\n\n# Body"
        result = mdc_to_claude(text)
        fm, _ = _split_frontmatter(result)
        assert fm["paths"] == ["a.py", "**/*.{ts,tsx}"]

    def test_glob_with_quote_is_valid_yaml(self):
        # A glob containing a double-quote must round-trip as valid YAML.
        weird = '**/*".py'
        text = f"---\nglobs: '{weird}'\nalwaysApply: false\n---\n\n# Body"
        result = mdc_to_claude(text)
        fm, _ = _split_frontmatter(result)
        assert fm["paths"] == [weird]


class TestSplitGlobs:
    def test_plain_comma_list(self):
        assert _split_globs("a,b,c") == ["a", "b", "c"]

    def test_brace_group_not_split(self):
        assert _split_globs("**/*.{py,js}") == ["**/*.{py,js}"]

    def test_strips_whitespace_and_drops_empties(self):
        assert _split_globs(" a , , b ") == ["a", "b"]


# ---------------------------------------------------------------------------
# Selection resolution
# ---------------------------------------------------------------------------


class TestResolveSelection:
    def test_explicit_names(self):
        result = resolve_selection(
            ["python-docstrings"],
            False,
            ["python-docstrings", "mirror-providers"],
            False,
            "rule",
            "local",
        )
        assert result == ["python-docstrings"]

    def test_all_flag_returns_all(self):
        available = ["a", "b", "c"]
        result = resolve_selection([], True, available, False, "rule", "local")
        assert result == available

    def test_names_and_all_aborts(self):
        with pytest.raises(SystemExit):
            resolve_selection(["a"], True, ["a", "b"], False, "rule", "local")

    def test_unknown_name_aborts(self):
        with pytest.raises(SystemExit):
            resolve_selection(["unknown"], False, ["a", "b"], False, "rule", "local")

    def test_non_interactive_no_stdin_aborts(self, monkeypatch):
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        with pytest.raises(SystemExit):
            resolve_selection([], False, ["a"], False, "rule", "local")

    def test_interactive_without_tty_aborts(self, monkeypatch):
        # Explicit -i with no terminal must abort, not fall through to a prompt.
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        with pytest.raises(SystemExit):
            resolve_selection([], False, ["a"], True, "rule", "local")

    def test_checkbox_prompt_includes_scope(self, monkeypatch):
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        prompts: list[str] = []

        def capture_checkbox(message: str, choices: list[str]) -> list[str]:
            prompts.append(message)
            return choices

        monkeypatch.setattr(logger, "checkbox", capture_checkbox)
        resolve_selection([], False, ["a-skill"], False, "skill", "global")
        assert prompts == ["Select skills to add — global (user home):"]


# ---------------------------------------------------------------------------
# Conflict-aware writers
# ---------------------------------------------------------------------------


class TestWriteFile:
    def test_writes_new_file(self, tmp_path):
        src = tmp_path / "src.txt"
        dest = tmp_path / "dest" / "out.txt"
        src.write_text("hello")
        action = write_file(src, dest)
        assert action == "write"
        assert dest.read_text() == "hello"

    def test_skips_existing_non_interactive(self, tmp_path):
        dest = tmp_path / "out.txt"
        dest.write_text("original")
        src = tmp_path / "src.txt"
        src.write_text("new")
        action = write_file(src, dest, force=False, interactive=False)
        assert action == "skip"
        assert dest.read_text() == "original"

    def test_force_overwrites(self, tmp_path):
        dest = tmp_path / "out.txt"
        dest.write_text("original")
        src = tmp_path / "src.txt"
        src.write_text("new")
        action = write_file(src, dest, force=True)
        assert action == "overwrite"
        assert dest.read_text() == "new"

    def test_force_backup_creates_bak(self, tmp_path):
        dest = tmp_path / "out.txt"
        dest.write_text("original")
        src = tmp_path / "src.txt"
        src.write_text("new")
        action = write_file(src, dest, force=True, backup=True)
        assert action == "backup_write"
        assert dest.read_text() == "new"
        assert (tmp_path / "out.txt.bak").read_text() == "original"

    def test_content_override(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("ignored")
        dest = tmp_path / "out.txt"
        write_file(src, dest, content_override="custom content")
        assert dest.read_text() == "custom content"


class TestWriteDir:
    def test_copies_directory(self, tmp_path):
        src = tmp_path / "src_dir"
        src.mkdir()
        (src / "file.txt").write_text("data")
        dest = tmp_path / "dest_dir"
        action = write_dir(src, dest)
        assert action == "write"
        assert (dest / "file.txt").read_text() == "data"

    def test_skips_existing_non_interactive(self, tmp_path):
        src = tmp_path / "src_dir"
        src.mkdir()
        (src / "file.txt").write_text("new")
        dest = tmp_path / "dest_dir"
        dest.mkdir()
        (dest / "old.txt").write_text("old")
        action = write_dir(src, dest, force=False, interactive=False)
        assert action == "skip"
        assert (dest / "old.txt").exists()

    def test_force_backup_renames(self, tmp_path):
        src = tmp_path / "src_dir"
        src.mkdir()
        (src / "new.txt").write_text("new")
        dest = tmp_path / "dest_dir"
        dest.mkdir()
        (dest / "old.txt").write_text("old")
        action = write_dir(src, dest, force=True, backup=True)
        assert action == "backup_write"
        assert (dest / "new.txt").exists()
        bak = tmp_path / "dest_dir.bak"
        assert bak.is_dir()
        assert (bak / "old.txt").read_text() == "old"


# ---------------------------------------------------------------------------
# install_skill
# ---------------------------------------------------------------------------


class TestInstallSkill:
    def test_installs_for_both_providers(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        summary = install_skill("grill-with-docs", ["cursor", "claude"], "local")
        assert summary["written"] == [
            str(Path(".cursor") / "skills" / "grill-with-docs"),
            str(Path(".claude") / "skills" / "grill-with-docs"),
        ]
        assert (
            tmp_path / ".cursor" / "skills" / "grill-with-docs" / "SKILL.md"
        ).exists()
        assert (
            tmp_path / ".claude" / "skills" / "grill-with-docs" / "SKILL.md"
        ).exists()

    def test_skips_existing_cursor(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        dest = tmp_path / ".cursor" / "skills" / "grill-with-docs"
        dest.mkdir(parents=True)
        (dest / "SKILL.md").write_text("existing")
        summary = install_skill("grill-with-docs", ["cursor"], "local")
        assert str(Path(".cursor") / "skills" / "grill-with-docs") in summary["skipped"]
        assert (dest / "SKILL.md").read_text() == "existing"


# ---------------------------------------------------------------------------
# install_rule
# ---------------------------------------------------------------------------


class TestInstallRule:
    def test_cursor_gets_mdc(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        summary = install_rule("python-docstrings", ["cursor"], "local")
        dest = tmp_path / ".cursor" / "rules" / "python-docstrings.mdc"
        assert dest.exists()
        assert summary["written"] == [
            str(Path(".cursor") / "rules" / "python-docstrings.mdc")
        ]
        content = dest.read_text()
        assert "alwaysApply" in content

    def test_claude_gets_translated_md(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        install_rule("python-docstrings", ["claude"], "local")
        dest = tmp_path / ".claude" / "rules" / "python-docstrings.md"
        assert dest.exists()
        content = dest.read_text()
        assert "paths:" in content
        assert "alwaysApply" not in content

    def test_cursor_verbatim_has_alwaysapply(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        install_rule("mirror-providers", ["cursor"], "local")
        dest = tmp_path / ".cursor" / "rules" / "mirror-providers.mdc"
        assert "alwaysApply" in dest.read_text()

    def test_installs_globally(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        install_rule("python-docstrings", ["claude"], "global")
        dest = tmp_path / ".claude" / "rules" / "python-docstrings.md"
        assert dest.exists()


# ---------------------------------------------------------------------------
# install_constitution
# ---------------------------------------------------------------------------


class TestInstallConstitution:
    def test_both_providers_local(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        summary = install_constitution(
            DEFAULT_CONSTITUTION, ["cursor", "claude"], "local"
        )
        assert (tmp_path / "AGENTS.md").exists()
        assert (tmp_path / "CLAUDE.md").exists()
        assert (tmp_path / "CLAUDE.md").read_text().strip() == IMPORT_LINE
        assert summary["written"] == ["AGENTS.md", "CLAUDE.md"]

    def test_cursor_only_writes_agents_md(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        install_constitution(DEFAULT_CONSTITUTION, ["cursor"], "local")
        assert (tmp_path / "AGENTS.md").exists()
        assert not (tmp_path / "CLAUDE.md").exists()

    def test_claude_only_writes_both_files(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        install_constitution(DEFAULT_CONSTITUTION, ["claude"], "local")
        assert (tmp_path / "AGENTS.md").exists()
        assert (tmp_path / "CLAUDE.md").exists()

    def test_global_cursor_only_warns_and_skips(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        summary = install_constitution(DEFAULT_CONSTITUTION, ["cursor"], "global")
        assert not (tmp_path / "AGENTS.md").exists()
        assert summary["written"] == []

    def test_global_claude_writes_to_dot_claude(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        install_constitution(DEFAULT_CONSTITUTION, ["claude"], "global")
        assert (tmp_path / ".claude" / "AGENTS.md").exists()
        assert (tmp_path / ".claude" / "CLAUDE.md").exists()

    def test_existing_agents_md_skipped_by_default(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "AGENTS.md").write_text("my existing agents")
        summary = install_constitution(
            DEFAULT_CONSTITUTION, ["cursor"], "local", force=False
        )
        assert "AGENTS.md" in str(summary["skipped"])
        assert (tmp_path / "AGENTS.md").read_text() == "my existing agents"

    def test_existing_agents_md_overwritten_with_force(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "AGENTS.md").write_text("old")
        install_constitution(DEFAULT_CONSTITUTION, ["cursor"], "local", force=True)
        assert (tmp_path / "AGENTS.md").read_text() != "old"

    def test_existing_claude_md_already_has_import_no_op(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "CLAUDE.md").write_text(f"{IMPORT_LINE}\n\nExtra content")
        install_constitution(DEFAULT_CONSTITUTION, ["claude"], "local")
        content = (tmp_path / "CLAUDE.md").read_text()
        assert content.count(IMPORT_LINE) == 1

    def test_existing_claude_md_without_import_skipped_non_interactive(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("existing content, no import")
        install_constitution(
            DEFAULT_CONSTITUTION, ["claude"], "local", force=False, interactive=False
        )
        content = (tmp_path / "CLAUDE.md").read_text()
        assert IMPORT_LINE not in content

    def test_existing_claude_md_import_prepended_with_force(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("existing content")
        summary = install_constitution(
            DEFAULT_CONSTITUTION, ["claude"], "local", force=True, interactive=False
        )
        content = (tmp_path / "CLAUDE.md").read_text()
        assert content.startswith(IMPORT_LINE)
        assert "existing content" in content
        assert "CLAUDE.md (import prepended)" in summary["written"]

    def test_agents_md_backed_up_with_backup_flag(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "AGENTS.md").write_text("old agents")
        install_constitution(
            DEFAULT_CONSTITUTION, ["cursor"], "local", force=True, backup=True
        )
        assert (tmp_path / "AGENTS.md.bak").read_text() == "old agents"
        assert (tmp_path / "AGENTS.md").exists()


# ---------------------------------------------------------------------------
# load_quickstart + install_quickstart
# ---------------------------------------------------------------------------


def test_load_quickstart_shape():
    result = load_quickstart()
    assert set(result.keys()) == {"skills", "rules", "constitution"}
    assert "grill-with-docs" in result["skills"]
    assert "python-docstrings" in result["rules"]
    assert "mirror-providers" in result["rules"]
    assert result["constitution"] == "entalpic-default"


class TestInstallQuickstart:
    def test_installs_all_kinds_both_local(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        install_quickstart(["cursor", "claude"], "local")
        assert (
            tmp_path / ".cursor" / "skills" / "grill-with-docs" / "SKILL.md"
        ).exists()
        assert (tmp_path / ".cursor" / "rules" / "python-docstrings.mdc").exists()
        assert (tmp_path / ".claude" / "rules" / "mirror-providers.md").exists()
        assert (tmp_path / "AGENTS.md").exists()
        assert (tmp_path / "CLAUDE.md").exists()

    def test_aborts_on_unknown_skill(self, monkeypatch):
        monkeypatch.setattr(
            "siesta.utils.agents.load_quickstart",
            lambda: {"skills": ["nope"], "rules": [], "constitution": None},
        )
        with pytest.raises(SystemExit):
            install_quickstart(["cursor"], "local")


# ---------------------------------------------------------------------------
# Detection + removal helpers
# ---------------------------------------------------------------------------


class TestDetectInstalled:
    def test_detects_non_catalog_skill(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        custom = tmp_path / ".cursor" / "skills" / "custom-skill"
        custom.mkdir(parents=True)
        assert detect_installed_skills(["cursor"], "local") == ["custom-skill"]

    def test_detects_non_catalog_rule(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rules = tmp_path / ".claude" / "rules"
        rules.mkdir(parents=True)
        (rules / "custom-rule.md").write_text("# rule")
        assert detect_installed_rules(["claude"], "local") == ["custom-rule"]

    def test_returns_sorted_names(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        for name in ("z-skill", "a-skill"):
            (tmp_path / ".cursor" / "skills" / name).mkdir(parents=True)
        assert detect_installed_skills(["cursor"], "local") == ["a-skill", "z-skill"]


class TestScopeDisplayLabel:
    def test_local(self):
        assert scope_display_label("local") == "local (current repository)"

    def test_global(self):
        assert scope_display_label("global") == "global (user home)"


class TestAssetSearchPaths:
    def test_local_cursor_skill_path(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert asset_search_paths(["cursor"], "local", "skill") == [
            str(Path(".cursor") / "skills")
        ]

    def test_global_both_providers(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.chdir(tmp_path)
        paths = asset_search_paths(["cursor", "claude"], "global", "rule")
        assert paths == [
            str(Path(".cursor") / "rules"),
            str(Path(".claude") / "rules"),
        ]


class TestResolveRemoveSelection:
    def test_explicit_missing_name_aborts(self, monkeypatch):
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        with pytest.raises(SystemExit):
            resolve_remove_selection(
                ["missing"],
                ["installed"],
                False,
                "skill",
                ["cursor"],
                "local",
            )

    def test_non_interactive_no_stdin_aborts(self, monkeypatch):
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        messages: list[str] = []

        def capture_abort(message: str) -> None:
            messages.append(message)
            raise SystemExit(1)

        monkeypatch.setattr(logger, "abort", capture_abort)
        with pytest.raises(SystemExit):
            resolve_remove_selection(
                [], ["installed"], False, "skill", ["cursor"], "global"
            )
        assert len(messages) == 1
        assert "Scope: global (user home)" in messages[0]
        assert "Searching:" in messages[0]
        assert "Detected: ['installed']" in messages[0]

    def test_interactive_without_tty_aborts(self, monkeypatch):
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        with pytest.raises(SystemExit):
            resolve_remove_selection(
                [], ["installed"], True, "skill", ["cursor"], "local"
            )

    def test_tty_without_names_shows_checkbox(self, monkeypatch):
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        prompts: list[str] = []

        def capture_checkbox(message: str, choices: list[str]) -> list[str]:
            prompts.append(message)
            return choices

        monkeypatch.setattr(logger, "checkbox", capture_checkbox)
        result = resolve_remove_selection(
            [], ["a-skill", "b-skill"], False, "skill", ["cursor"], "local"
        )
        assert result == ["a-skill", "b-skill"]
        assert prompts == ["Select skills to remove — local (current repository):"]

    def test_empty_detected_on_tty_skips_checkbox(self, monkeypatch):
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        messages: list[str] = []

        def fail_checkbox(_message: str, _choices: list[str]) -> list[str]:
            raise AssertionError("checkbox should not be called when detected is empty")

        monkeypatch.setattr(logger, "info", lambda msg: messages.append(msg))
        monkeypatch.setattr(logger, "checkbox", fail_checkbox)
        result = resolve_remove_selection([], [], False, "skill", ["cursor"], "local")
        assert result == []
        assert len(messages) == 1
        assert "No installed skills found." in messages[0]
        assert "Scope: local (current repository)" in messages[0]
        assert "Searching:" in messages[0]


class TestCollectConfirmedRemovals:
    def test_accepts_and_declines(self, tmp_path, monkeypatch):
        yes = tmp_path / "yes.txt"
        no = tmp_path / "no.txt"
        yes.write_text("yes")
        no.write_text("no")

        responses = iter([True, False])
        monkeypatch.setattr(logger, "confirm", lambda _msg: next(responses))

        confirmed, skipped = collect_confirmed_removals(
            [("yes file", yes), ("no file", no)]
        )
        assert confirmed == [yes]
        assert skipped == ["no file"]
        assert yes.read_text() == "yes"
        assert no.read_text() == "no"


class TestRemovePath:
    def test_backup_before_remove(self, tmp_path):
        target = tmp_path / "out.txt"
        target.write_text("data")
        action = remove_path(target, backup=True)
        assert action == "backed_up"
        assert not target.exists()
        assert (tmp_path / "out.txt.bak").read_text() == "data"


class TestRemoveSkillRule:
    def test_remove_skill(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        install_skill("grill-with-docs", ["cursor"], "local")
        dest = tmp_path / ".cursor" / "skills" / "grill-with-docs"
        assert dest.exists()
        summary = remove_skill("grill-with-docs", ["cursor"], "local")
        assert not dest.exists()
        assert str(Path(".cursor") / "skills" / "grill-with-docs") in summary["removed"]

    def test_remove_rule(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        install_rule("python-docstrings", ["claude"], "local")
        dest = tmp_path / ".claude" / "rules" / "python-docstrings.md"
        summary = remove_rule("python-docstrings", ["claude"], "local")
        assert not dest.exists()
        assert (
            str(Path(".claude") / "rules" / "python-docstrings.md")
            in summary["removed"]
        )


class TestRemoveConstitutionFile:
    def test_removes_catalog_agents_md(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        install_constitution(DEFAULT_CONSTITUTION, ["cursor"], "local")
        agents = tmp_path / "AGENTS.md"
        action, _ = remove_constitution_file(agents)
        assert action == "removed"
        assert not agents.exists()

    def test_skips_custom_agents_without_force(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        agents = tmp_path / "AGENTS.md"
        agents.write_text("custom")
        action, display = remove_constitution_file(agents, force=False)
        assert action == "skipped"
        # The skip reason must explain why a confirmed removal did nothing.
        assert "pass --force to remove" in display
        assert agents.exists()

    def test_removes_custom_agents_with_force(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        agents = tmp_path / "AGENTS.md"
        agents.write_text("custom")
        action, _ = remove_constitution_file(agents, force=True)
        assert action == "removed"
        assert not agents.exists()

    def test_deletes_import_stub_claude_md(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        claude = tmp_path / "CLAUDE.md"
        claude.write_text(IMPORT_LINE)
        action, _ = remove_constitution_file(claude)
        assert action == "removed"
        assert not claude.exists()

    def test_strips_import_from_mixed_claude_md(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        claude = tmp_path / "CLAUDE.md"
        claude.write_text(f"{IMPORT_LINE}\n\nbody")
        action, display = remove_constitution_file(claude)
        assert action == "modified"
        assert "import removed" in display
        assert IMPORT_LINE not in claude.read_text()
        assert "body" in claude.read_text()


class TestRemoveConstitution:
    def test_confirmed_local_removal(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        install_constitution(DEFAULT_CONSTITUTION, ["cursor", "claude"], "local")
        summary = remove_constitution(
            ["cursor", "claude"],
            "local",
            confirmed_agents=True,
            confirmed_claude=True,
        )
        assert not (tmp_path / "AGENTS.md").exists()
        assert not (tmp_path / "CLAUDE.md").exists()
        assert "AGENTS.md" in summary["removed"]
        assert "CLAUDE.md" in summary["removed"]

    def test_stripped_claude_md_recorded_as_modified(self, tmp_path, monkeypatch):
        # An edited-but-kept CLAUDE.md must not be reported as "removed".
        monkeypatch.chdir(tmp_path)
        (tmp_path / "CLAUDE.md").write_text(f"{IMPORT_LINE}\n\nbody")
        summary = remove_constitution(["claude"], "local", confirmed_claude=True)
        assert (tmp_path / "CLAUDE.md").exists()
        assert summary["removed"] == []
        assert any("CLAUDE.md" in entry for entry in summary["modified"])

    def test_constitution_paths_local(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        agents, claude = constitution_paths(["cursor", "claude"], "local")
        assert agents == tmp_path / "AGENTS.md"
        assert claude == tmp_path / "CLAUDE.md"

    def test_constitution_paths_global_claude(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        agents, claude = constitution_paths(["claude"], "global")
        assert agents == tmp_path / ".claude" / "AGENTS.md"
        assert claude == tmp_path / ".claude" / "CLAUDE.md"
