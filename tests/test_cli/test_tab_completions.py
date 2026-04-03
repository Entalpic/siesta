# Copyright 2025 Entalpic
"""
Unit tests for :mod:`siesta.completions`.

Tests are organised into classes that mirror the public API of the module:

* ``TestHelpers``               — pure utility functions (exec resolution, ID
                                  hashing, path computation).
* ``TestRenderHook``            — shell hook script content for bash and zsh.
* ``TestRcManagement``          — RC file source-line insertion and removal.
* ``TestInstall``               — end-to-end install flow for bash and zsh via
                                  ``self tab-completions install``.
* ``TestRefreshBehavior``       — runtime hook refresh (bash and zsh) when
                                  executable mtime is newer than cached static
                                  completion file.
* ``TestUninstall``             — end-to-end uninstall flow and edge cases via
                                  ``self tab-completions uninstall``.
* ``TestShow``                  — print-to-stdout mode via
                                  ``self tab-completions show``.
* ``TestWhere``                 — path display via ``self tab-completions where``.
* ``TestDetectCurrentShell``    — shell detection from ``$SHELL``.
* ``TestIsCompletionInstalled`` — hook-file presence check.
* ``TestShellDefaulting``       — automatic shell detection and error when
                                  shell cannot be detected.
* ``TestHelpEpilogue``          — completion hint appears in help output.
"""

import os
import shlex
import shutil
import subprocess
from pathlib import Path
from textwrap import dedent
from unittest.mock import patch

import cyclopts
import pytest

from siesta.cli import app
from siesta.completions import (
    _CLI_NAME,
    detect_current_shell,
    is_completion_installed,
    managed_completion_paths,
    remove_rc_source_line,
    render_shell_hook,
    resolve_cli_executable,
    shell_rc_file,
    stable_exec_id,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

FAKE_EXEC = "/tmp/bin/siesta"


def _fake_siesta_refresh_stub(*, completion_shell: str) -> str:
    """Executable placed on PATH; handles ``self tab-completions show --shell <shell>``.

    Uses the same interpreter as ``completion_shell`` so the stub matches the
    shell family under test (bash vs zsh).
    """
    return dedent(
        f"""\
        #!/usr/bin/env {completion_shell}
        if [[ "${{1:-}}" == "self" && "${{2:-}}" == "tab-completions" && "${{3:-}}" == "show" && "${{4:-}}" == "--shell" && "${{5:-}}" == "{completion_shell}" ]]; then
          printf '# Refreshed completion\\n'
          printf 'show\\n' >> "${{SIESTA_SHOW_LOG}}"
          exit 0
        fi
        exit 0
        """
    )


def _assert_managed_hook_refreshes_when_binary_newer(
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    completion_shell: str,
) -> None:
    """Drive install + hook: static file is regenerated when binary mtime is newer."""
    if completion_shell == "zsh" and shutil.which("zsh") is None:
        pytest.skip("zsh not found on PATH")

    fake_bin_dir = isolated_home / "bin"
    fake_bin_dir.mkdir(parents=True, exist_ok=True)
    fake_exec = fake_bin_dir / _CLI_NAME
    show_log = isolated_home / "show-calls.log"
    fake_exec.write_text(
        _fake_siesta_refresh_stub(completion_shell=completion_shell),
        encoding="utf-8",
    )
    fake_exec.chmod(0o755)

    monkeypatch.setenv("PATH", f"{fake_bin_dir}:{os.environ.get('PATH', '')}")

    with patch.object(
        cyclopts.App,
        "generate_completion",
        return_value="# Initial completion\n",
    ):
        with pytest.raises(SystemExit):
            app(
                [
                    "self",
                    "tab-completions",
                    "install",
                    "--shell",
                    completion_shell,
                    "--no-add-to-startup",
                ],
                exit_on_error=False,
            )

    exec_id = stable_exec_id(str(fake_exec.resolve()))
    paths = managed_completion_paths(completion_shell, exec_id)
    assert paths["static_file"].read_text(encoding="utf-8") == "# Initial completion\n"

    static_mtime = paths["static_file"].stat().st_mtime
    os.utime(fake_exec, (static_mtime + 5, static_mtime + 5))

    env = os.environ.copy()
    env["SIESTA_SHOW_LOG"] = str(show_log)
    hook_q = shlex.quote(str(paths["hook_file"]))

    if completion_shell == "bash":
        subprocess.run(
            ["bash", "-lc", f"source {hook_q} && siesta ping"],
            check=True,
            env=env,
            capture_output=True,
            text=True,
        )
    else:
        subprocess.run(
            ["zsh", "-fc", f". {hook_q} && siesta ping"],
            check=True,
            env=env,
            capture_output=True,
            text=True,
        )

    assert show_log.read_text(encoding="utf-8") == "show\n"
    assert (
        paths["static_file"].read_text(encoding="utf-8") == "# Refreshed completion\n"
    )
    assert int(paths["static_file"].stat().st_mtime) == int(fake_exec.stat().st_mtime)


@pytest.fixture()
def isolated_home(tmp_path, monkeypatch):
    """Redirect HOME and XDG_CONFIG_HOME to ``tmp_path`` for full isolation."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    return tmp_path


@pytest.fixture()
def mock_which():
    """Patch ``shutil.which`` in the completions module to return a fake path."""
    with patch("siesta.completions.shutil.which", return_value=FAKE_EXEC) as m:
        yield m


@pytest.fixture()
def mock_generate_completion():
    """Patch ``cyclopts.App.generate_completion`` to return a lightweight stub."""
    with patch.object(
        cyclopts.App,
        "generate_completion",
        return_value="# Stub completion\n",
    ) as m:
        yield m


# ---------------------------------------------------------------------------
# TestHelpers
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_resolve_executable_uses_which(self, mock_which):
        result = resolve_cli_executable()
        assert result == str(Path(FAKE_EXEC).expanduser().resolve())

    def test_resolve_executable_fallback_when_not_found(self):
        with patch("siesta.completions.shutil.which", return_value=None):
            result = resolve_cli_executable()
        assert result == _CLI_NAME

    def test_stable_exec_id_is_16_chars(self):
        assert len(stable_exec_id("/some/path/siesta")) == 16

    def test_stable_exec_id_differs_for_two_paths(self):
        assert stable_exec_id("/tmp/a/siesta") != stable_exec_id("/tmp/b/siesta")

    def test_stable_exec_id_is_deterministic(self):
        path = "/home/user/.venv/bin/siesta"
        assert stable_exec_id(path) == stable_exec_id(path)

    def test_managed_completion_paths_uses_xdg(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
        paths = managed_completion_paths("bash", "abcd1234abcd1234")
        assert (
            paths["base_dir"] == tmp_path / "xdg" / _CLI_NAME / "completions" / "bash"
        )

    def test_managed_completion_paths_without_xdg(self, monkeypatch, tmp_path):
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))
        paths = managed_completion_paths("zsh", "abcd1234abcd1234")
        assert (
            paths["base_dir"]
            == tmp_path / ".config" / _CLI_NAME / "completions" / "zsh"
        )

    def test_managed_completion_paths_keys(self):
        paths = managed_completion_paths("bash", "1234567890abcdef")
        assert set(paths.keys()) == {"base_dir", "hook_file", "static_file"}

    def test_managed_completion_paths_filenames(self):
        exec_id = "1234567890abcdef"
        paths = managed_completion_paths("zsh", exec_id)
        assert paths["hook_file"].name == "hook.zsh"
        assert paths["static_file"].name == f"static-{exec_id}.zsh"

    def test_shell_rc_file_bash(self):
        assert shell_rc_file("bash").name == ".bashrc"

    def test_shell_rc_file_zsh(self):
        assert shell_rc_file("zsh").name == ".zshrc"


# ---------------------------------------------------------------------------
# TestRenderHook
# ---------------------------------------------------------------------------


class TestRenderHook:
    def test_bash_hook_contains_maybe_refresh(self, tmp_path):
        hook = render_shell_hook("bash", base_dir=tmp_path)
        assert f"_{_CLI_NAME}_maybe_refresh" in hook

    def test_bash_hook_contains_regenerate_command(self, tmp_path):
        hook = render_shell_hook("bash", base_dir=tmp_path)
        assert f"command {_CLI_NAME} self tab-completions show --shell bash" in hook

    def test_bash_hook_contains_base_dir(self, tmp_path):
        hook = render_shell_hook("bash", base_dir=tmp_path)
        assert str(tmp_path) in hook

    def test_bash_hook_contains_shellcheck_directive(self, tmp_path):
        hook = render_shell_hook("bash", base_dir=tmp_path)
        assert "# shellcheck shell=bash" in hook

    def test_zsh_hook_contains_compdef(self, tmp_path):
        hook = render_shell_hook("zsh", base_dir=tmp_path)
        assert "compdef" in hook

    def test_zsh_hook_contains_resolve_function(self, tmp_path):
        hook = render_shell_hook("zsh", base_dir=tmp_path)
        assert f"_{_CLI_NAME}_resolve_exec_path" in hook

    def test_zsh_hook_contains_regenerate_command(self, tmp_path):
        hook = render_shell_hook("zsh", base_dir=tmp_path)
        assert f"command {_CLI_NAME} self tab-completions show --shell zsh" in hook

    def test_zsh_hook_contains_base_dir(self, tmp_path):
        hook = render_shell_hook("zsh", base_dir=tmp_path)
        assert str(tmp_path) in hook

    def test_zsh_hook_contains_whence(self, tmp_path):
        hook = render_shell_hook("zsh", base_dir=tmp_path)
        assert "whence -p" in hook

    def test_bash_hook_does_not_contain_compdef(self, tmp_path):
        hook = render_shell_hook("bash", base_dir=tmp_path)
        assert "compdef" not in hook


# ---------------------------------------------------------------------------
# TestRcManagement
# ---------------------------------------------------------------------------


class TestRcManagement:
    def test_ensure_creates_rc_if_absent(self, isolated_home):
        from siesta.completions import ensure_rc_source_line

        hook = (
            isolated_home / ".config" / _CLI_NAME / "completions" / "bash" / "hook.bash"
        )
        ensure_rc_source_line("bash", hook)
        assert (isolated_home / ".bashrc").exists()

    def test_ensure_adds_source_line(self, isolated_home):
        from siesta.completions import ensure_rc_source_line

        hook = Path("/some/hook.bash")
        ensure_rc_source_line("bash", hook)
        content = (isolated_home / ".bashrc").read_text()
        assert str(hook) in content

    def test_ensure_is_idempotent(self, isolated_home):
        from siesta.completions import ensure_rc_source_line

        hook = Path("/some/hook.bash")
        ensure_rc_source_line("bash", hook)
        ensure_rc_source_line("bash", hook)
        content = (isolated_home / ".bashrc").read_text()
        assert content.count(f"{_CLI_NAME} managed completion") == 1

    def test_remove_rc_source_line_strips_comment_and_source(self, isolated_home):
        from siesta.completions import ensure_rc_source_line

        hook = Path("/some/hook.bash")
        ensure_rc_source_line("bash", hook)
        remove_rc_source_line("bash", hook)
        content = (isolated_home / ".bashrc").read_text()
        assert str(hook) not in content
        assert f"{_CLI_NAME} managed completion" not in content

    def test_remove_rc_source_line_is_idempotent(self, isolated_home):
        from siesta.completions import ensure_rc_source_line

        hook = Path("/some/hook.bash")
        ensure_rc_source_line("bash", hook)
        remove_rc_source_line("bash", hook)
        remove_rc_source_line("bash", hook)  # second call must not raise
        content = (isolated_home / ".bashrc").read_text()
        assert f"{_CLI_NAME} managed completion" not in content

    def test_remove_noop_when_rc_missing(self, isolated_home):
        hook = Path("/nonexistent/hook.bash")
        remove_rc_source_line("bash", hook)  # must not raise

    def test_remove_noop_when_line_absent(self, isolated_home):
        rc = isolated_home / ".bashrc"
        rc.write_text("# pre-existing content\n")
        hook = Path("/some/hook.bash")
        remove_rc_source_line("bash", hook)
        assert rc.read_text() == "# pre-existing content\n"


# ---------------------------------------------------------------------------
# TestInstall — CLI round-trip via `self tab-completions install`
# ---------------------------------------------------------------------------


class TestInstall:
    def test_install_bash_creates_all_files(
        self, isolated_home, mock_which, mock_generate_completion, capsys
    ):
        """Install mode writes hook and static files for bash."""
        with pytest.raises(SystemExit):
            app(
                ["self", "tab-completions", "install", "--shell", "bash"],
                exit_on_error=False,
            )

        base_dir = isolated_home / "config" / _CLI_NAME / "completions" / "bash"
        assert (base_dir / "hook.bash").exists()
        assert len(list(base_dir.glob("static-*.bash"))) == 1

    def test_install_bash_hook_content(
        self, isolated_home, mock_which, mock_generate_completion
    ):
        with pytest.raises(SystemExit):
            app(
                ["self", "tab-completions", "install", "--shell", "bash"],
                exit_on_error=False,
            )

        base_dir = isolated_home / "config" / _CLI_NAME / "completions" / "bash"
        hook_text = (base_dir / "hook.bash").read_text()
        assert f"_{_CLI_NAME}_maybe_refresh" in hook_text
        assert (
            f"command {_CLI_NAME} self tab-completions show --shell bash" in hook_text
        )

    def test_install_bash_adds_rc_line(
        self, isolated_home, mock_which, mock_generate_completion
    ):
        with pytest.raises(SystemExit):
            app(
                ["self", "tab-completions", "install", "--shell", "bash"],
                exit_on_error=False,
            )

        rc_content = (isolated_home / ".bashrc").read_text()
        hook_path = (
            isolated_home / "config" / _CLI_NAME / "completions" / "bash" / "hook.bash"
        )
        assert str(hook_path) in rc_content

    def test_install_bash_rc_idempotent(
        self, isolated_home, mock_which, mock_generate_completion
    ):
        for _ in range(2):
            with pytest.raises(SystemExit):
                app(
                    ["self", "tab-completions", "install", "--shell", "bash"],
                    exit_on_error=False,
                )
        rc = (isolated_home / ".bashrc").read_text()
        assert rc.count(f"{_CLI_NAME} managed completion") == 1

    def test_install_bash_output_message(
        self, isolated_home, mock_which, mock_generate_completion, capsys
    ):
        with pytest.raises(SystemExit):
            app(
                ["self", "tab-completions", "install", "--shell", "bash"],
                exit_on_error=False,
            )
        out = capsys.readouterr().out
        assert "Managed completion installed to" in out
        assert "hook.bash" in out

    def test_install_bash_prints_restart_hint(
        self, isolated_home, mock_which, mock_generate_completion, capsys
    ):
        with pytest.raises(SystemExit):
            app(
                ["self", "tab-completions", "install", "--shell", "bash"],
                exit_on_error=False,
            )
        out = capsys.readouterr().out
        assert "Restart your shell" in out or ".bashrc" in out

    def test_install_zsh_creates_all_files(
        self, isolated_home, mock_which, mock_generate_completion
    ):
        """Install mode writes hook and static files for zsh."""
        with pytest.raises(SystemExit):
            app(
                ["self", "tab-completions", "install", "--shell", "zsh"],
                exit_on_error=False,
            )

        base_dir = isolated_home / "config" / _CLI_NAME / "completions" / "zsh"
        assert (base_dir / "hook.zsh").exists()
        assert len(list(base_dir.glob("static-*.zsh"))) == 1

    def test_install_zsh_hook_content(
        self, isolated_home, mock_which, mock_generate_completion
    ):
        with pytest.raises(SystemExit):
            app(
                ["self", "tab-completions", "install", "--shell", "zsh"],
                exit_on_error=False,
            )

        base_dir = isolated_home / "config" / _CLI_NAME / "completions" / "zsh"
        hook_text = (base_dir / "hook.zsh").read_text()
        assert "compdef" in hook_text
        assert f"command {_CLI_NAME} self tab-completions show --shell zsh" in hook_text

    def test_install_zsh_adds_rc_line(
        self, isolated_home, mock_which, mock_generate_completion
    ):
        with pytest.raises(SystemExit):
            app(
                ["self", "tab-completions", "install", "--shell", "zsh"],
                exit_on_error=False,
            )

        rc_content = (isolated_home / ".zshrc").read_text()
        hook_path = (
            isolated_home / "config" / _CLI_NAME / "completions" / "zsh" / "hook.zsh"
        )
        assert str(hook_path) in rc_content

    def test_install_no_add_to_startup_skips_rc(
        self, isolated_home, mock_which, mock_generate_completion
    ):
        """``--no-add-to-startup`` must not touch the shell RC file."""
        with pytest.raises(SystemExit):
            app(
                [
                    "self",
                    "tab-completions",
                    "install",
                    "--shell",
                    "zsh",
                    "--no-add-to-startup",
                ],
                exit_on_error=False,
            )
        assert not (isolated_home / ".zshrc").exists()


# ---------------------------------------------------------------------------
# TestRefreshBehavior — runtime hook refresh behavior
# ---------------------------------------------------------------------------


class TestRefreshBehavior:
    def test_bash_hook_regenerates_when_exec_is_newer(self, isolated_home, monkeypatch):
        """Bash hook regenerates static completions when executable mtime is newer."""
        _assert_managed_hook_refreshes_when_binary_newer(
            isolated_home, monkeypatch, completion_shell="bash"
        )

    def test_zsh_hook_regenerates_when_exec_is_newer(self, isolated_home, monkeypatch):
        """Zsh hook regenerates static completions when executable mtime is newer."""
        _assert_managed_hook_refreshes_when_binary_newer(
            isolated_home, monkeypatch, completion_shell="zsh"
        )


# ---------------------------------------------------------------------------
# TestUninstall — CLI round-trip via `self tab-completions uninstall`
# ---------------------------------------------------------------------------


class TestUninstall:
    def _do_install(self, shell, isolated_home, mock_which, mock_generate_completion):
        with pytest.raises(SystemExit):
            app(
                ["self", "tab-completions", "install", "--shell", shell],
                exit_on_error=False,
            )

    def test_uninstall_removes_managed_files(
        self, isolated_home, mock_which, mock_generate_completion
    ):
        self._do_install("bash", isolated_home, mock_which, mock_generate_completion)
        base_dir = isolated_home / "config" / _CLI_NAME / "completions" / "bash"
        assert (base_dir / "hook.bash").exists()

        with pytest.raises(SystemExit):
            app(
                ["self", "tab-completions", "uninstall", "--shell", "bash"],
                exit_on_error=False,
            )

        assert not (base_dir / "hook.bash").exists()
        assert list(base_dir.glob("static-*.bash")) == []

    def test_uninstall_removes_rc_source_line(
        self, isolated_home, mock_which, mock_generate_completion
    ):
        self._do_install("bash", isolated_home, mock_which, mock_generate_completion)
        rc = isolated_home / ".bashrc"
        assert f"{_CLI_NAME} managed completion" in rc.read_text()

        with pytest.raises(SystemExit):
            app(
                ["self", "tab-completions", "uninstall", "--shell", "bash"],
                exit_on_error=False,
            )

        assert f"{_CLI_NAME} managed completion" not in rc.read_text()

    def test_uninstall_noop_when_not_installed(self, isolated_home, mock_which, capsys):
        """Uninstall must not raise when no managed files exist."""
        with pytest.raises(SystemExit):
            app(
                ["self", "tab-completions", "uninstall", "--shell", "zsh"],
                exit_on_error=False,
            )
        out = capsys.readouterr().out
        assert "Not found" in out or "Nothing" in out

    def test_uninstall_does_not_touch_other_exec_files(
        self, isolated_home, mock_generate_completion
    ):
        """Files for a *different* exec_id must survive uninstall."""
        exec_a = "/tmp/venv_a/bin/siesta"
        exec_b = "/tmp/venv_b/bin/siesta"

        with patch("siesta.completions.shutil.which", return_value=exec_a):
            with pytest.raises(SystemExit):
                app(
                    [
                        "self",
                        "tab-completions",
                        "install",
                        "--shell",
                        "bash",
                        "--no-add-to-startup",
                    ],
                    exit_on_error=False,
                )

        base_dir = isolated_home / "config" / _CLI_NAME / "completions" / "bash"
        static_a = list(base_dir.glob("static-*.bash"))
        assert len(static_a) == 1

        with patch("siesta.completions.shutil.which", return_value=exec_b):
            with pytest.raises(SystemExit):
                app(
                    ["self", "tab-completions", "uninstall", "--shell", "bash"],
                    exit_on_error=False,
                )

        # exec_a's static file must still be there
        assert static_a[0].exists()

    def test_uninstall_zsh(self, isolated_home, mock_which, mock_generate_completion):
        self._do_install("zsh", isolated_home, mock_which, mock_generate_completion)
        base_dir = isolated_home / "config" / _CLI_NAME / "completions" / "zsh"
        assert (base_dir / "hook.zsh").exists()

        with pytest.raises(SystemExit):
            app(
                ["self", "tab-completions", "uninstall", "--shell", "zsh"],
                exit_on_error=False,
            )

        assert not (base_dir / "hook.zsh").exists()
        assert list(base_dir.glob("static-*.zsh")) == []


# ---------------------------------------------------------------------------
# TestShow — `self tab-completions show`
# ---------------------------------------------------------------------------


class TestShow:
    def test_show_bash(self, capsys, monkeypatch):
        monkeypatch.setenv("SHELL", "/bin/bash")
        with patch.object(
            cyclopts.App,
            "generate_completion",
            return_value="# Bash completion for siesta\n",
        ) as mock_gen:
            with pytest.raises(SystemExit):
                app(
                    ["self", "tab-completions", "show", "--shell", "bash"],
                    exit_on_error=False,
                )

        mock_gen.assert_called_once()
        assert mock_gen.call_args.kwargs["shell"] == "bash"
        assert "Bash completion for siesta" in capsys.readouterr().out

    def test_show_zsh(self, capsys):
        with patch.object(
            cyclopts.App,
            "generate_completion",
            return_value="# Zsh completion\n",
        ) as mock_gen:
            with pytest.raises(SystemExit):
                app(
                    ["self", "tab-completions", "show", "--shell", "zsh"],
                    exit_on_error=False,
                )

        mock_gen.assert_called_once()
        assert mock_gen.call_args.kwargs["shell"] == "zsh"
        assert "Zsh completion" in capsys.readouterr().out

    def test_show_bash_real_script(self, capsys):
        """Integration: real bash completion script contains top-level commands."""
        with pytest.raises(SystemExit):
            app(
                ["self", "tab-completions", "show", "--shell", "bash"],
                exit_on_error=False,
            )
        out = capsys.readouterr().out
        assert "# Bash completion" in out
        # Top-level siesta commands must appear in the completion script.
        assert "tab-completions" in out

    def test_show_defaults_to_detected_shell(self, monkeypatch, capsys):
        monkeypatch.setenv("SHELL", "/bin/zsh")
        with patch.object(
            cyclopts.App,
            "generate_completion",
            return_value="# Zsh completion\n",
        ) as mock_gen:
            with pytest.raises(SystemExit):
                app(["self", "tab-completions", "show"], exit_on_error=False)
        mock_gen.assert_called_once()
        assert mock_gen.call_args.kwargs["shell"] == "zsh"


# ---------------------------------------------------------------------------
# TestWhere — `self tab-completions where`
# ---------------------------------------------------------------------------


class TestWhere:
    def test_where_shows_paths(self, isolated_home, mock_which, capsys, monkeypatch):
        monkeypatch.setenv("SHELL", "/bin/bash")
        with pytest.raises(SystemExit):
            app(
                ["self", "tab-completions", "where", "--shell", "bash"],
                exit_on_error=False,
            )
        out = capsys.readouterr().out
        assert "hook_file" in out or "Hook file" in out
        assert "bash" in out

    def test_where_shows_missing_when_not_installed(
        self, isolated_home, mock_which, capsys
    ):
        with pytest.raises(SystemExit):
            app(
                ["self", "tab-completions", "where", "--shell", "bash", "--simple"],
                exit_on_error=False,
            )
        out = capsys.readouterr().out
        assert "missing" in out

    def test_where_shows_exists_after_install(
        self, isolated_home, mock_which, mock_generate_completion, capsys
    ):
        with pytest.raises(SystemExit):
            app(
                ["self", "tab-completions", "install", "--shell", "bash"],
                exit_on_error=False,
            )
        capsys.readouterr()  # discard install output

        with pytest.raises(SystemExit):
            app(
                ["self", "tab-completions", "where", "--shell", "bash", "--simple"],
                exit_on_error=False,
            )
        out = capsys.readouterr().out
        assert "exists" in out

    def test_where_defaults_to_detected_shell(
        self, isolated_home, mock_which, capsys, monkeypatch
    ):
        monkeypatch.setenv("SHELL", "/bin/zsh")
        with pytest.raises(SystemExit):
            app(["self", "tab-completions", "where"], exit_on_error=False)
        out = capsys.readouterr().out
        assert "zsh" in out

    def test_where_simple_no_table(self, isolated_home, mock_which, capsys):
        with pytest.raises(SystemExit):
            app(
                ["self", "tab-completions", "where", "--shell", "bash", "--simple"],
                exit_on_error=False,
            )
        out = capsys.readouterr().out
        assert "Base directory:" in out
        assert "Hook file:" in out
        # Rich table border characters should not be present
        assert "─" not in out
        assert "│" not in out

    def test_where_simple_shows_status(self, isolated_home, mock_which, capsys):
        with pytest.raises(SystemExit):
            app(
                ["self", "tab-completions", "where", "--shell", "bash", "--simple"],
                exit_on_error=False,
            )
        out = capsys.readouterr().out
        assert "missing" in out


# ---------------------------------------------------------------------------
# TestDetectCurrentShell
# ---------------------------------------------------------------------------


class TestDetectCurrentShell:
    def test_zsh_path_returns_zsh(self, monkeypatch):
        monkeypatch.setenv("SHELL", "/bin/zsh")
        assert detect_current_shell() == "zsh"

    def test_bash_path_returns_bash(self, monkeypatch):
        monkeypatch.setenv("SHELL", "/bin/bash")
        assert detect_current_shell() == "bash"

    def test_homebrew_zsh_path_returns_zsh(self, monkeypatch):
        monkeypatch.setenv("SHELL", "/opt/homebrew/bin/zsh")
        assert detect_current_shell() == "zsh"

    def test_unsupported_shell_returns_none(self, monkeypatch):
        monkeypatch.setenv("SHELL", "/usr/bin/fish")
        assert detect_current_shell() is None

    def test_empty_shell_returns_none(self, monkeypatch):
        monkeypatch.setenv("SHELL", "")
        assert detect_current_shell() is None

    def test_missing_shell_env_returns_none(self, monkeypatch):
        monkeypatch.delenv("SHELL", raising=False)
        assert detect_current_shell() is None


# ---------------------------------------------------------------------------
# TestIsCompletionInstalled
# ---------------------------------------------------------------------------


class TestIsCompletionInstalled:
    def test_returns_true_when_hook_file_exists(self, isolated_home, mock_which):
        exec_id = stable_exec_id(str(Path(FAKE_EXEC).resolve()))
        paths = managed_completion_paths("zsh", exec_id)
        paths["base_dir"].mkdir(parents=True, exist_ok=True)
        paths["hook_file"].touch()

        assert is_completion_installed("zsh") is True

    def test_returns_false_when_hook_file_absent(self, isolated_home, mock_which):
        assert is_completion_installed("bash") is False

    def test_checks_correct_shell(self, isolated_home, mock_which):
        exec_id = stable_exec_id(str(Path(FAKE_EXEC).resolve()))
        bash_paths = managed_completion_paths("bash", exec_id)
        bash_paths["base_dir"].mkdir(parents=True, exist_ok=True)
        bash_paths["hook_file"].touch()

        assert is_completion_installed("bash") is True
        assert is_completion_installed("zsh") is False


# ---------------------------------------------------------------------------
# TestShellDefaulting — auto-detect and error behavior
# ---------------------------------------------------------------------------


class TestShellDefaulting:
    def test_install_uses_detected_shell(
        self, isolated_home, mock_which, mock_generate_completion, monkeypatch
    ):
        """Omitting ``--shell`` falls back to ``$SHELL``."""
        monkeypatch.setenv("SHELL", "/bin/bash")
        with pytest.raises(SystemExit):
            app(["self", "tab-completions", "install"], exit_on_error=False)

        base_dir = isolated_home / "config" / _CLI_NAME / "completions" / "bash"
        assert (base_dir / "hook.bash").exists()

    def test_uninstall_uses_detected_shell(
        self, isolated_home, mock_which, mock_generate_completion, monkeypatch
    ):
        """Omitting ``--shell`` from uninstall falls back to ``$SHELL``."""
        monkeypatch.setenv("SHELL", "/bin/zsh")
        # install first
        with pytest.raises(SystemExit):
            app(
                ["self", "tab-completions", "install", "--shell", "zsh"],
                exit_on_error=False,
            )
        base_dir = isolated_home / "config" / _CLI_NAME / "completions" / "zsh"
        assert (base_dir / "hook.zsh").exists()

        # uninstall without --shell
        with pytest.raises(SystemExit):
            app(["self", "tab-completions", "uninstall"], exit_on_error=False)
        assert not (base_dir / "hook.zsh").exists()

    def test_install_errors_when_shell_undetectable(
        self, isolated_home, mock_which, mock_generate_completion, monkeypatch, capsys
    ):
        """When ``$SHELL`` is not bash/zsh and ``--shell`` is absent, exit 1."""
        monkeypatch.setenv("SHELL", "/usr/bin/fish")
        with pytest.raises(SystemExit) as exc_info:
            app(["self", "tab-completions", "install"], exit_on_error=False)
        assert exc_info.value.code != 0
        out = capsys.readouterr().out
        assert "--shell" in out

    def test_show_errors_when_shell_undetectable(self, monkeypatch, capsys):
        """When ``$SHELL`` is unrecognised and ``--shell`` is absent, exit 1."""
        monkeypatch.setenv("SHELL", "/usr/bin/fish")
        with pytest.raises(SystemExit) as exc_info:
            app(["self", "tab-completions", "show"], exit_on_error=False)
        assert exc_info.value.code != 0
        out = capsys.readouterr().out
        assert "--shell" in out

    def test_where_errors_when_shell_undetectable(
        self, isolated_home, mock_which, monkeypatch, capsys
    ):
        """When ``$SHELL`` is unrecognised and ``--shell`` is absent, exit 1."""
        monkeypatch.setenv("SHELL", "/usr/bin/fish")
        with pytest.raises(SystemExit) as exc_info:
            app(["self", "tab-completions", "where"], exit_on_error=False)
        assert exc_info.value.code != 0
        out = capsys.readouterr().out
        assert "--shell" in out

    def test_uninstall_errors_when_shell_undetectable(
        self, isolated_home, mock_which, monkeypatch, capsys
    ):
        """When ``$SHELL`` is unrecognised and ``--shell`` is absent, exit 1."""
        monkeypatch.setenv("SHELL", "/usr/bin/fish")
        with pytest.raises(SystemExit) as exc_info:
            app(["self", "tab-completions", "uninstall"], exit_on_error=False)
        assert exc_info.value.code != 0
        out = capsys.readouterr().out
        assert "--shell" in out


# ---------------------------------------------------------------------------
# TestHelpEpilogue — completion hint in help output
# ---------------------------------------------------------------------------


class TestHelpEpilogue:
    def test_tip_appears_in_help_when_epilogue_set(self, capsys):
        """When help_epilogue is set, it appears in --help output."""
        original = app.help_epilogue
        try:
            app.help_epilogue = (
                "Tip: enable tab completions with `siesta self tab-completions install`"
            )
            with pytest.raises(SystemExit):
                app(["--help"], exit_on_error=False)
            out = capsys.readouterr().out
            assert "enable tab completions" in out
            assert "siesta self tab-completions install" in out
        finally:
            app.help_epilogue = original

    def test_tip_absent_when_epilogue_not_set(self, capsys):
        """When help_epilogue is None, no tip appears in --help output."""
        original = app.help_epilogue
        try:
            app.help_epilogue = None
            with pytest.raises(SystemExit):
                app(["--help"], exit_on_error=False)
            out = capsys.readouterr().out
            assert "enable tab completions" not in out
        finally:
            app.help_epilogue = original

    def test_tip_propagates_to_subcommand_help(self, capsys):
        """Epilogue set on root app propagates to sub-command help."""
        original = app.help_epilogue
        try:
            app.help_epilogue = (
                "Tip: enable tab completions with `siesta self tab-completions install`"
            )
            with pytest.raises(SystemExit):
                app(["self", "--help"], exit_on_error=False)
            out = capsys.readouterr().out
            assert "enable tab completions" in out
        finally:
            app.help_epilogue = original
