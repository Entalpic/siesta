# Copyright 2025 Entalpic
"""Integration tests for ``siesta agents`` CLI commands.

Commands are driven through the root ``app`` (as other CLI tests do) after
changing into a ``tmp_path``-based working directory so all filesystem writes
are isolated.
"""

import sys
from pathlib import Path

from siesta.cli.main_app import app
from siesta.utils.agents import IMPORT_LINE
from siesta.utils.common import logger

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run(*args):
    """Run the siesta CLI and return the SystemExit code (0 on success)."""
    try:
        app(list(args))
        return 0
    except SystemExit as e:
        return e.code if e.code is not None else 0


def confirm_yes(_message: str, default: bool = True) -> bool:
    """Auto-accept confirmation prompts in tests."""
    return True


def confirm_no(_message: str, default: bool = True) -> bool:
    """Auto-decline confirmation prompts in tests."""
    return False


# ---------------------------------------------------------------------------
# add skill
# ---------------------------------------------------------------------------


class TestAddSkill:
    def test_installs_skill_cursor(self, tmp_path_chdir):
        run("agents", "add", "skill", "grill-with-docs", "--cursor", "--local")
        assert (
            tmp_path_chdir / ".cursor" / "skills" / "grill-with-docs" / "SKILL.md"
        ).exists()

    def test_prints_skill_path_relative_to_cwd(self, tmp_path_chdir, capsys):
        run("agents", "add", "skill", "grill-with-docs", "--cursor", "--local")
        output = capsys.readouterr().out
        assert "Written: .cursor/skills/grill-with-docs" in output
        assert str(tmp_path_chdir) not in output

    def test_installs_skill_claude(self, tmp_path_chdir):
        run("agents", "add", "skill", "grill-with-docs", "--claude", "--local")
        assert (
            tmp_path_chdir / ".claude" / "skills" / "grill-with-docs" / "SKILL.md"
        ).exists()

    def test_installs_skill_both_providers(self, tmp_path_chdir):
        run("agents", "add", "skill", "grill-with-docs", "--both", "--local")
        assert (
            tmp_path_chdir / ".cursor" / "skills" / "grill-with-docs" / "SKILL.md"
        ).exists()
        assert (
            tmp_path_chdir / ".claude" / "skills" / "grill-with-docs" / "SKILL.md"
        ).exists()

    def test_all_flag_installs_all(self, tmp_path_chdir):
        from siesta.utils.agents import available_skills

        run("agents", "add", "skill", "--all", "--cursor")
        for skill in available_skills():
            assert (tmp_path_chdir / ".cursor" / "skills" / skill).is_dir()

    def test_all_and_names_mutual_exclusion(self, tmp_path_chdir):
        code = run("agents", "add", "skill", "grill-with-docs", "--all", "--cursor")
        assert code != 0

    def test_unknown_skill_name_aborts(self, tmp_path_chdir):
        code = run("agents", "add", "skill", "nonexistent-skill", "--cursor")
        assert code != 0

    def test_skips_existing_by_default(self, tmp_path_chdir):
        dest = tmp_path_chdir / ".cursor" / "skills" / "grill-with-docs"
        dest.mkdir(parents=True)
        (dest / "SKILL.md").write_text("mine")
        run("agents", "add", "skill", "grill-with-docs", "--cursor")
        assert (dest / "SKILL.md").read_text() == "mine"

    def test_force_overwrites_existing(self, tmp_path_chdir):
        dest = tmp_path_chdir / ".cursor" / "skills" / "grill-with-docs"
        dest.mkdir(parents=True)
        (dest / "SKILL.md").write_text("old")
        run("agents", "add", "skill", "grill-with-docs", "--cursor", "--force")
        assert (dest / "SKILL.md").read_text() != "old"

    def test_backup_creates_bak(self, tmp_path_chdir):
        dest = tmp_path_chdir / ".cursor" / "skills" / "grill-with-docs"
        dest.mkdir(parents=True)
        (dest / "SKILL.md").write_text("old")
        run(
            "agents",
            "add",
            "skill",
            "grill-with-docs",
            "--cursor",
            "--force",
            "--backup",
        )
        bak = tmp_path_chdir / ".cursor" / "skills" / "grill-with-docs.bak"
        assert bak.is_dir()

    def test_no_op_when_no_args_non_interactive(self, tmp_path_chdir, monkeypatch):
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        code = run("agents", "add", "skill")
        assert code != 0

    def test_global_scope_writes_to_home(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        (tmp_path / "repo").mkdir(exist_ok=True)
        monkeypatch.chdir(tmp_path / "repo")
        run("agents", "add", "skill", "grill-with-docs", "--claude", "--global")
        assert (
            tmp_path / ".claude" / "skills" / "grill-with-docs" / "SKILL.md"
        ).exists()


# ---------------------------------------------------------------------------
# add rule
# ---------------------------------------------------------------------------


class TestAddRule:
    def test_cursor_rule_is_mdc(self, tmp_path_chdir):
        run("agents", "add", "rule", "python-docstrings", "--cursor")
        assert (tmp_path_chdir / ".cursor" / "rules" / "python-docstrings.mdc").exists()

    def test_claude_rule_is_md(self, tmp_path_chdir):
        run("agents", "add", "rule", "python-docstrings", "--claude")
        assert (tmp_path_chdir / ".claude" / "rules" / "python-docstrings.md").exists()

    def test_claude_rule_translated_has_paths(self, tmp_path_chdir):
        run("agents", "add", "rule", "python-docstrings", "--claude")
        content = (
            tmp_path_chdir / ".claude" / "rules" / "python-docstrings.md"
        ).read_text()
        assert "paths:" in content
        assert '"**/*.py"' in content

    def test_cursor_rule_has_alwaysapply(self, tmp_path_chdir):
        run("agents", "add", "rule", "python-docstrings", "--cursor")
        content = (
            tmp_path_chdir / ".cursor" / "rules" / "python-docstrings.mdc"
        ).read_text()
        assert "alwaysApply" in content

    def test_all_flag(self, tmp_path_chdir):
        from siesta.utils.agents import available_rules

        run("agents", "add", "rule", "--all", "--cursor")
        for rule in available_rules():
            assert (tmp_path_chdir / ".cursor" / "rules" / f"{rule}.mdc").exists()

    def test_unknown_rule_aborts(self, tmp_path_chdir):
        code = run("agents", "add", "rule", "nonexistent-rule", "--cursor")
        assert code != 0

    def test_skips_existing_by_default(self, tmp_path_chdir):
        dest = tmp_path_chdir / ".cursor" / "rules" / "python-docstrings.mdc"
        dest.parent.mkdir(parents=True)
        dest.write_text("mine")
        run("agents", "add", "rule", "python-docstrings", "--cursor")
        assert dest.read_text() == "mine"

    def test_force_overwrites(self, tmp_path_chdir):
        dest = tmp_path_chdir / ".cursor" / "rules" / "python-docstrings.mdc"
        dest.parent.mkdir(parents=True)
        dest.write_text("old")
        run("agents", "add", "rule", "python-docstrings", "--cursor", "--force")
        assert dest.read_text() != "old"


# ---------------------------------------------------------------------------
# add constitution
# ---------------------------------------------------------------------------


class TestAddConstitution:
    def test_default_writes_agents_and_claude(self, tmp_path_chdir):
        run("agents", "add", "constitution")
        assert (tmp_path_chdir / "AGENTS.md").exists()
        assert (tmp_path_chdir / "CLAUDE.md").exists()
        assert (tmp_path_chdir / "CLAUDE.md").read_text().strip() == IMPORT_LINE

    def test_cursor_only_no_claude_md(self, tmp_path_chdir):
        run("agents", "add", "constitution", "--cursor")
        assert (tmp_path_chdir / "AGENTS.md").exists()
        assert not (tmp_path_chdir / "CLAUDE.md").exists()

    def test_claude_only_writes_both(self, tmp_path_chdir):
        run("agents", "add", "constitution", "--claude")
        assert (tmp_path_chdir / "AGENTS.md").exists()
        assert (tmp_path_chdir / "CLAUDE.md").exists()

    def test_global_cursor_only_skips_with_warning(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        run("agents", "add", "constitution", "--cursor", "--global")
        assert not (tmp_path / "AGENTS.md").exists()

    def test_global_claude_writes_to_dot_claude(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        run("agents", "add", "constitution", "--claude", "--global")
        assert (tmp_path / ".claude" / "AGENTS.md").exists()
        assert (tmp_path / ".claude" / "CLAUDE.md").exists()

    def test_unknown_constitution_aborts(self, tmp_path_chdir):
        code = run("agents", "add", "constitution", "nonexistent-constitution")
        assert code != 0

    def test_existing_agents_skipped_by_default(self, tmp_path_chdir):
        (tmp_path_chdir / "AGENTS.md").write_text("mine")
        run("agents", "add", "constitution", "--cursor")
        assert (tmp_path_chdir / "AGENTS.md").read_text() == "mine"

    def test_force_overwrites_agents(self, tmp_path_chdir):
        (tmp_path_chdir / "AGENTS.md").write_text("old")
        run("agents", "add", "constitution", "--cursor", "--force")
        assert (tmp_path_chdir / "AGENTS.md").read_text() != "old"

    def test_claude_md_import_already_present_no_duplicate(self, tmp_path_chdir):
        (tmp_path_chdir / "CLAUDE.md").write_text(f"{IMPORT_LINE}\n\nmy stuff")
        run("agents", "add", "constitution", "--claude")
        content = (tmp_path_chdir / "CLAUDE.md").read_text()
        assert content.count(IMPORT_LINE) == 1

    def test_force_prepends_import_to_existing_claude_md(self, tmp_path_chdir):
        (tmp_path_chdir / "CLAUDE.md").write_text("existing content")
        run("agents", "add", "constitution", "--claude", "--force")
        content = (tmp_path_chdir / "CLAUDE.md").read_text()
        assert content.startswith(IMPORT_LINE)
        assert "existing content" in content

    def test_backup_flag_preserves_old_agents(self, tmp_path_chdir):
        (tmp_path_chdir / "AGENTS.md").write_text("old agents")
        run("agents", "add", "constitution", "--cursor", "--force", "--backup")
        assert (tmp_path_chdir / "AGENTS.md.bak").read_text() == "old agents"

    def test_local_and_global_abort(self, tmp_path_chdir):
        code = run("agents", "add", "constitution", "--local", "--global")
        assert code != 0


# ---------------------------------------------------------------------------
# remove skill
# ---------------------------------------------------------------------------


class TestRemoveSkill:
    def test_removes_skill_after_confirmation(self, tmp_path_chdir, monkeypatch):
        monkeypatch.setattr(logger, "confirm", confirm_yes)
        run("agents", "add", "skill", "grill-with-docs", "--cursor", "--local")
        dest = tmp_path_chdir / ".cursor" / "skills" / "grill-with-docs"
        assert dest.exists()
        run("agents", "remove", "skill", "grill-with-docs", "--cursor")
        assert not dest.exists()

    def test_declining_confirmation_skips_removal(self, tmp_path_chdir, monkeypatch):
        monkeypatch.setattr(logger, "confirm", confirm_no)
        run("agents", "add", "skill", "grill-with-docs", "--cursor", "--local")
        dest = tmp_path_chdir / ".cursor" / "skills" / "grill-with-docs"
        run("agents", "remove", "skill", "grill-with-docs", "--cursor")
        assert dest.exists()

    def test_non_interactive_without_names_aborts(self, tmp_path_chdir, monkeypatch):
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        code = run("agents", "remove", "skill")
        assert code != 0

    def test_missing_skill_aborts(self, tmp_path_chdir, monkeypatch):
        monkeypatch.setattr(logger, "confirm", confirm_yes)
        code = run("agents", "remove", "skill", "nonexistent-skill", "--cursor")
        assert code != 0

    def test_global_scope_targets_home(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setattr(logger, "confirm", confirm_yes)
        (tmp_path / "repo").mkdir(exist_ok=True)
        monkeypatch.chdir(tmp_path / "repo")
        run("agents", "add", "skill", "grill-with-docs", "--claude", "--global")
        dest = tmp_path / ".claude" / "skills" / "grill-with-docs"
        assert dest.exists()
        run("agents", "remove", "skill", "grill-with-docs", "--claude", "--global")
        assert not dest.exists()


# ---------------------------------------------------------------------------
# remove rule
# ---------------------------------------------------------------------------


class TestRemoveRule:
    def test_removes_rule_after_confirmation(self, tmp_path_chdir, monkeypatch):
        monkeypatch.setattr(logger, "confirm", confirm_yes)
        run("agents", "add", "rule", "python-docstrings", "--claude")
        dest = tmp_path_chdir / ".claude" / "rules" / "python-docstrings.md"
        assert dest.exists()
        run("agents", "remove", "rule", "python-docstrings", "--claude")
        assert not dest.exists()

    def test_declining_confirmation_skips_removal(self, tmp_path_chdir, monkeypatch):
        monkeypatch.setattr(logger, "confirm", confirm_no)
        run("agents", "add", "rule", "python-docstrings", "--claude")
        dest = tmp_path_chdir / ".claude" / "rules" / "python-docstrings.md"
        run("agents", "remove", "rule", "python-docstrings", "--claude")
        assert dest.exists()


# ---------------------------------------------------------------------------
# remove constitution
# ---------------------------------------------------------------------------


class TestRemoveConstitution:
    def test_removes_catalog_agents_after_confirmation(
        self, tmp_path_chdir, monkeypatch
    ):
        monkeypatch.setattr(logger, "confirm", confirm_yes)
        run("agents", "add", "constitution", "--cursor")
        agents = tmp_path_chdir / "AGENTS.md"
        assert agents.exists()
        run("agents", "remove", "constitution", "--cursor")
        assert not agents.exists()

    def test_skips_user_agents_without_force(self, tmp_path_chdir, monkeypatch):
        monkeypatch.setattr(logger, "confirm", confirm_yes)
        (tmp_path_chdir / "AGENTS.md").write_text("my custom constitution")
        run("agents", "remove", "constitution", "--cursor")
        assert (tmp_path_chdir / "AGENTS.md").read_text() == "my custom constitution"

    def test_removes_user_agents_with_force(self, tmp_path_chdir, monkeypatch):
        monkeypatch.setattr(logger, "confirm", confirm_yes)
        (tmp_path_chdir / "AGENTS.md").write_text("my custom constitution")
        run("agents", "remove", "constitution", "--cursor", "--force")
        assert not (tmp_path_chdir / "AGENTS.md").exists()

    def test_removes_import_stub_claude_md(self, tmp_path_chdir, monkeypatch):
        monkeypatch.setattr(logger, "confirm", confirm_yes)
        run("agents", "add", "constitution", "--claude")
        claude = tmp_path_chdir / "CLAUDE.md"
        assert claude.exists()
        run("agents", "remove", "constitution", "--claude")
        assert not claude.exists()

    def test_removes_only_import_from_mixed_claude_md(
        self, tmp_path_chdir, monkeypatch
    ):
        monkeypatch.setattr(logger, "confirm", confirm_yes)
        (tmp_path_chdir / "CLAUDE.md").write_text(f"{IMPORT_LINE}\n\nmy stuff")
        run("agents", "remove", "constitution", "--claude")
        content = (tmp_path_chdir / "CLAUDE.md").read_text()
        assert IMPORT_LINE not in content
        assert "my stuff" in content


# ---------------------------------------------------------------------------
# quickstart
# ---------------------------------------------------------------------------


class TestQuickstart:
    def test_quickstart_installs_all_both_local(self, tmp_path_chdir):
        run("agents", "quickstart", "--both", "--local")
        assert (
            tmp_path_chdir / ".cursor" / "skills" / "grill-with-docs" / "SKILL.md"
        ).exists()
        assert (tmp_path_chdir / ".cursor" / "rules" / "python-docstrings.mdc").exists()
        assert (tmp_path_chdir / ".claude" / "rules" / "mirror-providers.md").exists()
        assert (tmp_path_chdir / "AGENTS.md").exists()
        assert (tmp_path_chdir / "CLAUDE.md").exists()

    def test_quickstart_cursor_only(self, tmp_path_chdir):
        run("agents", "quickstart", "--cursor")
        assert (
            tmp_path_chdir / ".cursor" / "skills" / "grill-with-docs" / "SKILL.md"
        ).exists()
        assert not (tmp_path_chdir / ".claude" / "skills").exists()

    def test_quickstart_force_overwrites(self, tmp_path_chdir):
        rule = tmp_path_chdir / ".cursor" / "rules" / "python-docstrings.mdc"
        rule.parent.mkdir(parents=True)
        rule.write_text("old")
        run("agents", "quickstart", "--cursor", "--force")
        assert rule.read_text() != "old"
