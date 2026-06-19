# Copyright 2025 Entalpic
"""Regression tests for CLI help text and documentation wording.

Asserts that ``--help`` output uses accurate terminology (Agent Assets,
Conflict Resolution, ``-i/--interactive``, Non-Interactive Resolution) and
that documentation source files contain no stale strings.

Tests are organised into classes:

* ``TestProjectQuickstartHelp``   — ``project quickstart --help``
* ``TestDocsInitHelp``            — ``docs init --help``
* ``TestAgentsQuickstartHelp``    — ``agents quickstart --help``
* ``TestSelfPatHelp``             — PAT-related ``self`` sub-command help
* ``TestDocSourceStaleness``      — grep documentation source files for stale strings
"""

from pathlib import Path

import pytest

from siesta.cli.main_app import app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_help(capsys, *args: str) -> str:
    """Invoke ``app`` with ``--help`` and return captured stdout."""
    with pytest.raises(SystemExit):
        app([*args, "--help"], exit_on_error=False)
    return capsys.readouterr().out


# ---------------------------------------------------------------------------
# project quickstart --help
# ---------------------------------------------------------------------------


class TestProjectQuickstartHelp:
    def test_mentions_agent_assets(self, capsys):
        out = _get_help(capsys, "project", "quickstart")
        assert "Agent Assets" in out

    def test_mentions_interactive_flag(self, capsys):
        out = _get_help(capsys, "project", "quickstart")
        assert "-i" in out or "--interactive" in out

    def test_no_with_defaults_flag(self, capsys):
        out = _get_help(capsys, "project", "quickstart")
        assert "--with-defaults" not in out

    def test_no_raw_rst_admonitions(self, capsys):
        out = _get_help(capsys, "project", "quickstart")
        assert ".. note::" not in out
        assert ".. tip::" not in out
        assert ".. important::" not in out

    def test_overwrite_semantics(self, capsys):
        out = _get_help(capsys, "project", "quickstart")
        # Conflict Resolution tri-state semantics must be described
        assert "overwrite" in out.lower()
        assert "skip" in out.lower()

    def test_no_prompt_the_user_for_cli_defaulted_flags(self, capsys):
        out = _get_help(capsys, "project", "quickstart")
        # None should not be described as solely "prompt the user" for
        # flags that are filled from CLI_DEFAULTS in non-interactive mode.
        # Acceptable: "CLI default", "non-interactive", "prompts when -i"
        # Not acceptable: "None (i.e. prompt the user)" without mentioning defaults.
        assert "None (i.e. prompt the user)" not in out


# ---------------------------------------------------------------------------
# docs init --help
# ---------------------------------------------------------------------------


class TestDocsInitHelp:
    def test_no_with_defaults_flag(self, capsys):
        out = _get_help(capsys, "docs", "init")
        assert "--with-defaults" not in out

    def test_no_raw_rst_admonitions(self, capsys):
        out = _get_help(capsys, "docs", "init")
        assert ".. warning::" not in out
        assert ".. important::" not in out
        assert ".. tip::" not in out

    def test_non_interactive_resolution_described(self, capsys):
        out = _get_help(capsys, "docs", "init")
        # Non-interactive resolution: abort in non-TTY
        assert (
            "non-interactive" in out.lower()
            or "non-TTY" in out
            or "abort" in out.lower()
        )

    def test_overwrite_skip_semantics(self, capsys):
        out = _get_help(capsys, "docs", "init")
        assert "overwrite" in out.lower()
        assert "skip" in out.lower()

    def test_prevent_wording_absent(self, capsys):
        out = _get_help(capsys, "docs", "init")
        # Old wording "Prevent dependencies prompt by forcing" should be gone
        assert "Prevent" not in out


# ---------------------------------------------------------------------------
# agents quickstart --help
# ---------------------------------------------------------------------------


class TestAgentsQuickstartHelp:
    def test_mentions_quickstart_config(self, capsys):
        out = _get_help(capsys, "agents", "quickstart")
        assert "Quickstart Config" in out

    def test_mentions_providers(self, capsys):
        out = _get_help(capsys, "agents", "quickstart")
        assert "Provider" in out or "Cursor" in out or "Claude" in out

    def test_mentions_local_default_scope(self, capsys):
        out = _get_help(capsys, "agents", "quickstart")
        assert "--local" in out or "local" in out.lower()

    def test_mentions_conflict_resolution(self, capsys):
        out = _get_help(capsys, "agents", "quickstart")
        assert "Conflict Resolution" in out or "overwrite" in out.lower()


# ---------------------------------------------------------------------------
# self set-github-pat --help  /  self show-github-pat --help
# ---------------------------------------------------------------------------


class TestSelfPatHelp:
    def test_set_pat_no_cli_arg_entry(self, capsys):
        out = _get_help(capsys, "self", "set-github-pat")
        # PATs are never accepted via CLI arguments
        assert (
            "hidden prompt" in out.lower()
            or "hidden" in out.lower()
            or "getpass" in out.lower()
            or "prompt" in out.lower()
        )

    def test_set_pat_mentions_keyring_storage(self, capsys):
        out = _get_help(capsys, "self", "set-github-pat")
        assert "keyring" in out.lower()

    def test_set_pat_github_capitalization(self, capsys):
        out = _get_help(capsys, "self", "set-github-pat")
        assert "Github PAT" not in out
        assert "GitHub" in out or "PAT" in out

    def test_show_pat_masked_default(self, capsys):
        out = _get_help(capsys, "self", "show-github-pat")
        assert (
            "mask" in out.lower() or "hidden" in out.lower() or "redact" in out.lower()
        )

    def test_show_pat_explicit_confirmation(self, capsys):
        out = _get_help(capsys, "self", "show-github-pat")
        assert (
            "confirm" in out.lower()
            or "explicit" in out.lower()
            or "full" in out.lower()
        )


# ---------------------------------------------------------------------------
# Documentation source file staleness checks
# ---------------------------------------------------------------------------


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class TestDocSourceStaleness:
    """Assert that documentation source files contain no stale strings."""

    DOC_FILES = [
        _REPO_ROOT / "README.md",
        _REPO_ROOT / "src/siesta/__init__.py",
        _REPO_ROOT / "src/siesta/cli/__init__.py",
        _REPO_ROOT / "docs/source/_templates/autoapi/index.rst",
        _REPO_ROOT / "docs/source/guide/index.rst",
        _REPO_ROOT / "docs/source/guide/write-documentation.rst",
        _REPO_ROOT / "docs/source/guide/write-docstrings.rst",
        _REPO_ROOT / "docs/source/guide/example.rst",
    ]

    def _read_all(self) -> str:
        texts = []
        for p in self.DOC_FILES:
            if p.exists():
                texts.append(p.read_text(encoding="utf-8"))
        return "\n".join(texts)

    def test_no_with_defaults(self):
        content = self._read_all()
        assert "--with-defaults" not in content

    def test_no_stale_siesta_cli_app_reference(self):
        content = self._read_all()
        # Allow only in non-user-facing contexts (e.g. code examples showing migration).
        # For a strict check, no raw `siesta.cli.app` module path should appear.
        assert "siesta.cli.app" not in content

    def test_no_github_wrong_capitalization(self):
        content = self._read_all()
        # Reject "Github" as a brand name (correct form is "GitHub").
        # Allow "github.com" (all-lower is fine in URLs).
        import re

        for match in re.finditer(r"(?<!\.)Github(?!\.com)", content):
            context_start = max(0, match.start() - 30)
            context = content[context_start : match.end() + 30]
            pytest.fail(f"Found 'Github' (should be 'GitHub') near: ...{context!r}...")

    def test_no_malformed_rst_note(self):
        for p in self.DOC_FILES:
            if not p.exists():
                continue
            text = p.read_text(encoding="utf-8")
            # Allow ".. note::" (correct) but not ".. note\n" (missing ::)
            import re

            for match in re.finditer(r"\.\. note(?!::)", text):
                # Only flag RST files and .py docstrings where it matters
                if p.suffix in {".rst", ".py"}:
                    context_start = max(0, match.start() - 10)
                    context = text[context_start : match.end() + 20]
                    pytest.fail(
                        f"Malformed '.. note' (missing '::') in {p.name} near: ...{context!r}..."
                    )
