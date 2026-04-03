# Copyright 2025 Entalpic
"""
Shell tab-completion management for CLI tool.

Overview
--------
This module provides all logic for generating, installing, and uninstalling
bash/zsh tab completions for a CLI.  It is deliberately kept free of any
CLI-framework (cyclopts) dependency so that it can be imported and tested in
isolation; the actual ``generate_completion`` callable is injected by the
caller.

The CLI name is controlled by the module-level :data:`_CLI_NAME` constant.
All shell variable names, hook file comments, and config-directory path
components are derived from it, making the module straightforward to adapt
for different CLI tools by changing a single value.

Modes of operation
------------------
**Print mode** (default)
    The caller obtains the raw completion script from the CLI framework and
    writes it to stdout.  Users can source it manually or pipe it to a file.

**Managed install mode** (``siesta self tab-completions install``)
    Two files are written under an XDG-compliant directory tree::

        $XDG_CONFIG_HOME/<cli>/completions/<shell>/
            hook.<shell>              – sourced by the shell RC file at startup
            static-<exec_id>.<shell>  – cached completion script

    A source line is optionally appended to the shell RC file
    (``~/.bashrc`` / ``~/.zshrc``).

How the managed hook works
--------------------------
At shell startup the hook:

1. Resolves the CLI executable path **without** spawning Python.
2. Derives the ``exec_id`` (SHA-256 hex of the path, first 16 chars) used to
   locate the shell-specific cached completion file.
3. Sources the cached static file immediately so completions are available
   without any Python startup overhead.

On the **first real invocation** of the CLI in a session the hook runs
``_<cli>_maybe_refresh``, which:

4. Compares the executable's mtime to the static completion file.  If the
   binary is newer (i.e. the CLI was reinstalled or upgraded), it regenerates
   the cached script by calling
   ``<cli> self tab-completions show --shell <shell>`` exactly once, then
   re-sources it.
5. Sets ``_<CLI>_COMPLETION_REFRESHED=1`` so subsequent invocations in the
   same session skip the check entirely.

Python is **never** spawned at shell startup — only on the first use after an
upgrade.

Multi-install support
---------------------
Multiple installations (e.g. different virtual-environments or pip-installed
versions) are isolated by their ``exec_id``.  Each installation gets its own
``static-<exec_id>.<shell>`` file under the shared base directory.  Switching
between environments in a new shell session transparently picks up the correct
completion script.

Bash vs. zsh differences
-------------------------
Both shells share the same high-level logic but differ in a few details:

* **Path resolution**: bash uses ``command -v``; zsh uses ``whence -p`` with a
  ``command -v`` fallback (absolute-path check) for reliability.
* **Completion registration**: zsh additionally calls ``compdef`` to hook the
  completion function into the zsh completion system.
* **Mid-session path change detection**: the zsh hook re-resolves the
  executable path on every ``_<cli>_maybe_refresh`` call, so switching virtual
  environments mid-session is handled correctly.  The bash hook does not
  re-resolve mid-session (resolved once at startup), which is acceptable given
  bash's usage patterns.

Uninstall
---------
:func:`uninstall_managed_completion` removes all managed files for the current
``exec_id`` and strips the RC source line.  Files for *other* exec_ids
(i.e. other installations) are left untouched.
"""

import hashlib
import os
import shutil
import textwrap
from pathlib import Path
from typing import Callable, Literal

Shell = Literal["bash", "zsh"]

_CLI_NAME: str = "siesta"
"""Name of the CLI binary.

All shell variable names, config-directory path components, and RC file
comments are derived from this value.  Change it here to adapt the module for
a different CLI tool.
"""


def _shell_quote(path: str | Path) -> str:
    """Single-quote a string for safe embedding in a shell script.

    Uses the standard ``'\''`` idiom to handle embedded single-quotes.

    Parameters
    ----------
    path : str | Path
        Value to quote.

    Returns
    -------
    str
        Shell-safe single-quoted string (e.g. ``'/some/path'``).
    """
    return "'" + str(path).replace("'", "'\\''") + "'"


# ---------------------------------------------------------------------------
# Executable resolution
# ---------------------------------------------------------------------------


def resolve_cli_executable() -> str:
    """Return the resolved absolute path to the active CLI executable.

    Uses :func:`shutil.which` to locate the binary on ``PATH``, then resolves
    symlinks so that the path is stable across different activation methods
    (venv, pipx, conda, …).

    Returns
    -------
    str
        Absolute, symlink-resolved path if found; the bare CLI name string
        if the binary is not on ``PATH`` (fallback that keeps callers
        functional even when resolution fails).
    """
    resolved = shutil.which(_CLI_NAME)
    return str(Path(resolved).expanduser().resolve()) if resolved else _CLI_NAME


# ---------------------------------------------------------------------------
# Stable exec ID (multi-install isolation)
# ---------------------------------------------------------------------------


def stable_exec_id(exec_path: str) -> str:
    """Return a short, stable identifier for a CLI executable path.

    The ID is the first 16 hex characters of the SHA-256 digest of the
    resolved path string.  It is used as a filename component to isolate
    completion artefacts belonging to different installations of the CLI
    (e.g. separate virtual-environments) that share the same config directory.

    Parameters
    ----------
    exec_path : str
        Absolute, resolved path to the CLI binary.

    Returns
    -------
    str
        16-character lowercase hex string, unique per distinct path.

    Examples
    --------
    .. code-block:: python

        >>> stable_exec_id("/home/user/.venv/bin/siesta")
        'a3f9c1d8e2b74501'  # illustrative; actual value depends on the path
    """
    return hashlib.sha256(exec_path.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Path computation (XDG-aware)
# ---------------------------------------------------------------------------


def managed_completion_paths(shell: Shell, exec_id: str) -> dict[str, Path]:
    """Return the managed completion-related paths for ``shell`` and ``exec_id``.

    The base directory respects ``$XDG_CONFIG_HOME`` when set, otherwise
    defaults to ``~/.config``.

    Parameters
    ----------
    shell : {'bash', 'zsh'}
        Target shell.
    exec_id : str
        Stable identifier for the CLI executable (see :func:`stable_exec_id`).

    Returns
    -------
    dict[str, Path]
        Dictionary with the following keys:

        ``base_dir``
            ``<config_root>/<cli>/completions/<shell>/``
        ``hook_file``
            ``<base_dir>/hook.<shell>`` — sourced by the shell RC file.
        ``static_file``
            ``<base_dir>/static-<exec_id>.<shell>`` — cached completion
            script.  Its mtime is kept in sync with the CLI executable for
            staleness detection.
    """
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME", "").strip()
    config_root = (
        Path(xdg_config_home).expanduser()
        if xdg_config_home
        else Path.home() / ".config"
    )
    base_dir = config_root / _CLI_NAME / "completions" / shell
    return {
        "base_dir": base_dir,
        "hook_file": base_dir / f"hook.{shell}",
        "static_file": base_dir / f"static-{exec_id}.{shell}",
    }


# ---------------------------------------------------------------------------
# Shell hook rendering
# ---------------------------------------------------------------------------


def render_shell_hook(shell: Shell, *, base_dir: Path) -> str:
    """Render a shell hook script that sources cached completions at startup.

    The generated script:

    * Sources the cached static completion file immediately at shell startup
      (no Python spawned).
    * Wraps the CLI command with a thin shell function that calls
      ``_<cli>_maybe_refresh`` on the first invocation in each session.
    * For zsh, additionally registers the completion function via ``compdef``.

    Parameters
    ----------
    shell : {'bash', 'zsh'}
        Target shell for the hook.
    base_dir : Path
        The base directory where managed completion files live
        (``<config_root>/<cli>/completions/<shell>/``).

    Returns
    -------
    str
        Complete shell script text to be written to ``hook.<shell>``.
    """
    base_dir_q = _shell_quote(base_dir)
    if shell == "bash":
        return textwrap.dedent(f"""\
            # {_CLI_NAME} managed completion hook (bash)
            # Generated by {_CLI_NAME} self tab-completions install
            # shellcheck shell=bash

            # Unset inherited guard so every new shell starts fresh.
            unset _{_CLI_NAME.upper()}_COMPLETION_REFRESHED 2>/dev/null

            _{_CLI_NAME}_completion_base_dir={base_dir_q}

            # Portable SHA-256: try sha256sum (coreutils/Linux) then shasum (macOS).
            _{_CLI_NAME}_sha256_16() {{
              local hash
              hash="$(printf '%s' "$1" | sha256sum 2>/dev/null || printf '%s' "$1" | shasum -a 256 2>/dev/null)" || return 1
              printf '%s' "${{hash%% *}}" | cut -c1-16
            }}

            # Resolve executable and exec_id once at startup (no Python spawned).
            _{_CLI_NAME}_exec_path="$(command -v {_CLI_NAME} 2>/dev/null || true)"
            _{_CLI_NAME}_exec_id=""
            _{_CLI_NAME}_static_file=""
            if [[ -n "${{_{_CLI_NAME}_exec_path}}" ]]; then
              _{_CLI_NAME}_exec_id="$(_{_CLI_NAME}_sha256_16 "${{_{_CLI_NAME}_exec_path}}")"
              [[ -z "${{_{_CLI_NAME}_exec_id}}" ]] && _{_CLI_NAME}_exec_id="${{_{_CLI_NAME}_exec_path//\\//__}}"
              _{_CLI_NAME}_static_file="${{_{_CLI_NAME}_completion_base_dir}}/static-${{_{_CLI_NAME}_exec_id}}.bash"
              if [[ -f "${{_{_CLI_NAME}_static_file}}" ]]; then
                # shellcheck source=/dev/null
                source "${{_{_CLI_NAME}_static_file}}"
              fi
            fi

            # On the first real invocation, regenerate completions if the executable is
            # newer than the cached static script (i.e. the CLI was reinstalled or
            # updated). Python is only spawned here, never at shell startup.
            _{_CLI_NAME}_maybe_refresh() {{
              if [[ -n "${{_{_CLI_NAME.upper()}_COMPLETION_REFRESHED:-}}" ]] || [[ -z "${{_{_CLI_NAME}_exec_id}}" ]]; then
                return 0
              fi
              local tmp_file
              if [[ ! -f "${{_{_CLI_NAME}_static_file}}" ]] || [[ "${{_{_CLI_NAME}_exec_path}}" -nt "${{_{_CLI_NAME}_static_file}}" ]]; then
                tmp_file="${{_{_CLI_NAME}_static_file}}.tmp"
                if command {_CLI_NAME} self tab-completions show --shell bash > "${{tmp_file}}" 2>/dev/null; then
                  mv "${{tmp_file}}" "${{_{_CLI_NAME}_static_file}}"
                  touch -r "${{_{_CLI_NAME}_exec_path}}" "${{_{_CLI_NAME}_static_file}}" 2>/dev/null || true
                  # shellcheck source=/dev/null
                  source "${{_{_CLI_NAME}_static_file}}"
                else
                  rm -f "${{tmp_file}}" 2>/dev/null || true
                fi
              fi
              _{_CLI_NAME.upper()}_COMPLETION_REFRESHED=1
            }}

            {_CLI_NAME}() {{
              _{_CLI_NAME}_maybe_refresh
              command {_CLI_NAME} "$@"
            }}
            """)

    return textwrap.dedent(f"""\
        # {_CLI_NAME} managed completion hook (zsh)
        # Generated by {_CLI_NAME} self tab-completions install

        # Unset inherited guard so every new shell starts fresh.
        unset _{_CLI_NAME.upper()}_COMPLETION_REFRESHED 2>/dev/null

        _{_CLI_NAME}_completion_base_dir={base_dir_q}

        # Portable SHA-256: try sha256sum (coreutils/Linux) then shasum (macOS).
        _{_CLI_NAME}_sha256_16() {{
          local hash
          hash="$(printf '%s' "$1" | sha256sum 2>/dev/null || printf '%s' "$1" | shasum -a 256 2>/dev/null)" || return 1
          printf '%s' "${{hash%% *}}" | cut -c1-16
        }}

        # zsh: prefer whence -p for reliable absolute-path resolution; fall back to
        # command -v and reject relative paths (e.g. from a local ./{_CLI_NAME}).
        _{_CLI_NAME}_resolve_exec_path() {{
          local p
          p="$(whence -p {_CLI_NAME} 2>/dev/null || true)"
          [[ -n "${{p}}" ]] && {{ printf '%s\n' "${{p}}"; return 0; }}
          p="$(command -v {_CLI_NAME} 2>/dev/null || true)"
          if [[ "${{p}}" = /* ]]; then
            printf '%s\n' "${{p}}"
          else
            printf '%s\n' ""
          fi
        }}

        _{_CLI_NAME}_exec_path="$(_{_CLI_NAME}_resolve_exec_path)"
        _{_CLI_NAME}_exec_id=""
        _{_CLI_NAME}_static_file=""
        if [[ -n "${{_{_CLI_NAME}_exec_path}}" ]]; then
          _{_CLI_NAME}_exec_id="$(_{_CLI_NAME}_sha256_16 "${{_{_CLI_NAME}_exec_path}}")"
          [[ -z "${{_{_CLI_NAME}_exec_id}}" ]] && _{_CLI_NAME}_exec_id="${{_{_CLI_NAME}_exec_path//\\//__}}"
          _{_CLI_NAME}_static_file="${{_{_CLI_NAME}_completion_base_dir}}/static-${{_{_CLI_NAME}_exec_id}}.zsh"
          [[ -f "${{_{_CLI_NAME}_static_file}}" ]] && source "${{_{_CLI_NAME}_static_file}}"
        fi

        # zsh re-resolves the exec path on every call so that switching virtual
        # environments mid-session is handled correctly.
        _{_CLI_NAME}_maybe_refresh() {{
          local current_exec tmp_file
          if [[ -n "${{_{_CLI_NAME.upper()}_COMPLETION_REFRESHED:-}}" ]]; then
            return 0
          fi

          current_exec="$(_{_CLI_NAME}_resolve_exec_path)"
          if [[ -z "${{current_exec}}" ]]; then
            return 0
          fi

          if [[ "${{current_exec}}" != "${{_{_CLI_NAME}_exec_path}}" ]]; then
            _{_CLI_NAME}_exec_path="${{current_exec}}"
            _{_CLI_NAME}_exec_id="$(_{_CLI_NAME}_sha256_16 "${{_{_CLI_NAME}_exec_path}}")"
            [[ -z "${{_{_CLI_NAME}_exec_id}}" ]] && _{_CLI_NAME}_exec_id="${{_{_CLI_NAME}_exec_path//\\//__}}"
            _{_CLI_NAME}_static_file="${{_{_CLI_NAME}_completion_base_dir}}/static-${{_{_CLI_NAME}_exec_id}}.zsh"
          fi

          if [[ ! -f "${{_{_CLI_NAME}_static_file}}" ]] || [[ "${{_{_CLI_NAME}_exec_path}}" -nt "${{_{_CLI_NAME}_static_file}}" ]]; then
            tmp_file="${{_{_CLI_NAME}_static_file}}.tmp"
            if command {_CLI_NAME} self tab-completions show --shell zsh > "${{tmp_file}}" 2>/dev/null; then
              mv "${{tmp_file}}" "${{_{_CLI_NAME}_static_file}}"
              touch -r "${{_{_CLI_NAME}_exec_path}}" "${{_{_CLI_NAME}_static_file}}" 2>/dev/null || true
            else
              rm -f "${{tmp_file}}" 2>/dev/null || true
            fi
          fi

          [[ -f "${{_{_CLI_NAME}_static_file}}" ]] && source "${{_{_CLI_NAME}_static_file}}"
          typeset -g _{_CLI_NAME.upper()}_COMPLETION_REFRESHED=1
        }}

        _{_CLI_NAME}_managed_completion() {{
          _{_CLI_NAME}_maybe_refresh
          if typeset -f _{_CLI_NAME} >/dev/null 2>&1; then
            _{_CLI_NAME} "$@"
          fi
        }}

        if (( $+functions[compdef] )); then
          compdef _{_CLI_NAME}_managed_completion {_CLI_NAME} >/dev/null 2>&1
        fi

        {_CLI_NAME}() {{
          _{_CLI_NAME}_maybe_refresh
          command {_CLI_NAME} "$@"
        }}
        """)


# ---------------------------------------------------------------------------
# RC file management
# ---------------------------------------------------------------------------


def shell_rc_file(shell: Shell) -> Path:
    """Return the primary startup RC file path for ``shell``.

    Parameters
    ----------
    shell : {'bash', 'zsh'}
        Target shell.

    Returns
    -------
    Path
        ``~/.bashrc`` for bash, ``~/.zshrc`` for zsh.
    """
    return Path.home() / (".bashrc" if shell == "bash" else ".zshrc")


def ensure_rc_source_line(shell: Shell, hook_file: Path) -> None:
    """Append a source line to the shell RC file (idempotent).

    Creates the RC file if it does not exist.  If the source line is already
    present the file is not modified, making repeated installs safe.

    Parameters
    ----------
    shell : {'bash', 'zsh'}
        Target shell (determines which RC file is used).
    hook_file : Path
        Absolute path to the managed hook file that should be sourced.
    """
    rc_file = shell_rc_file(shell)
    rc_file.parent.mkdir(parents=True, exist_ok=True)
    if not rc_file.exists():
        rc_file.write_text("", encoding="utf-8")

    hook_q = _shell_quote(hook_file)
    source_line = f"[[ -f {hook_q} ]] && source {hook_q}"
    content = rc_file.read_text(encoding="utf-8")
    if source_line not in content:
        with rc_file.open("a", encoding="utf-8") as fh:
            if content and not content.endswith("\n"):
                fh.write("\n")
            fh.write(f"\n# {_CLI_NAME} managed completion\n{source_line}\n")


def remove_rc_source_line(shell: Shell, hook_file: Path) -> None:
    """Remove the managed source line from the shell RC file (idempotent).

    Strips the ``# <cli> managed completion`` comment line and the ``source``
    line added by :func:`ensure_rc_source_line`.  If neither line is found the
    RC file is left untouched.  Does nothing if the RC file does not exist.

    Parameters
    ----------
    shell : {'bash', 'zsh'}
        Target shell (determines which RC file is used).
    hook_file : Path
        Absolute path to the hook file whose source line should be removed.
    """
    rc_file = shell_rc_file(shell)
    if not rc_file.exists():
        return

    hook_q = _shell_quote(hook_file)
    source_line = f"[[ -f {hook_q} ]] && source {hook_q}"
    comment_line = f"# {_CLI_NAME} managed completion"
    content = rc_file.read_text(encoding="utf-8")

    if source_line not in content:
        return

    lines = content.splitlines(keepends=True)
    filtered: list[str] = []
    skip_next_blank = False
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.rstrip("\n").rstrip()
        if stripped == comment_line or stripped == source_line:
            # Also consume a leading blank line that we inserted before the block.
            if filtered and filtered[-1].strip() == "":
                filtered.pop()
            skip_next_blank = True
            i += 1
            continue
        if skip_next_blank and stripped == "":
            skip_next_blank = False
            i += 1
            continue
        skip_next_blank = False
        filtered.append(line)
        i += 1

    rc_file.write_text("".join(filtered), encoding="utf-8")


# ---------------------------------------------------------------------------
# Shell detection and installation status
# ---------------------------------------------------------------------------


def detect_current_shell() -> Shell | None:
    """Return the current user shell if it is a supported one.

    Reads ``$SHELL`` and returns ``"bash"`` or ``"zsh"`` when the basename
    matches, ``None`` otherwise (e.g. fish, unknown, or variable unset).

    Returns
    -------
    Shell | None
        ``"bash"``, ``"zsh"``, or ``None`` for unrecognised shells.
    """
    basename = os.path.basename(os.environ.get("SHELL", ""))
    if basename in ("bash", "zsh"):
        return basename  # type: ignore[return-value]
    return None


def is_completion_installed(shell: Shell) -> bool:
    """Return whether managed completions are installed for ``shell``.

    Checks for the presence of the managed hook file for the currently
    resolved CLI executable.  Existence of the hook file is the definitive
    indicator — if it was written, the install succeeded.  Staleness is
    handled at shell startup by the hook itself.

    Parameters
    ----------
    shell : {'bash', 'zsh'}
        Shell to check.

    Returns
    -------
    bool
        ``True`` if the hook file exists for the current executable, ``False``
        otherwise.
    """
    exec_path = resolve_cli_executable()
    exec_id = stable_exec_id(exec_path)
    paths = managed_completion_paths(shell=shell, exec_id=exec_id)
    return paths["hook_file"].exists()


# ---------------------------------------------------------------------------
# Install / uninstall orchestration
# ---------------------------------------------------------------------------


def install_managed_completion(
    shell: Shell,
    generate_fn: Callable[[str], str],
    *,
    add_to_startup: bool,
) -> Path:
    """Install the managed completion hook and static script.

    The static file's mtime is set to match the executable's mtime so the
    shell hook can detect upgrades via a simple ``-nt`` comparison.

    Parameters
    ----------
    shell : {'bash', 'zsh'}
        Target shell.
    generate_fn : Callable[[str], str]
        Callable that accepts a ``shell`` keyword argument and returns the
        raw completion script string.  Typically the CLI framework's
        ``generate_completion`` method.  Passed explicitly to keep this module
        free of CLI-framework imports.
    add_to_startup : bool
        When ``True``, append a source line for the hook file to the shell RC
        file (``~/.bashrc`` / ``~/.zshrc``).

    Returns
    -------
    Path
        Path to the written hook file (``<base_dir>/hook.<shell>``).
    """
    exec_path = resolve_cli_executable()
    exec_id = stable_exec_id(exec_path)
    paths = managed_completion_paths(shell=shell, exec_id=exec_id)
    paths["base_dir"].mkdir(parents=True, exist_ok=True)

    completion_script = generate_fn(shell=shell)
    paths["static_file"].write_text(completion_script, encoding="utf-8")

    # Set the static file's mtime to match the executable so the hook knows
    # completions are current.  If stat fails the hook will regenerate on
    # first use.
    try:
        exec_stat = os.stat(exec_path)
        os.utime(paths["static_file"], (exec_stat.st_atime, exec_stat.st_mtime))
    except OSError:
        pass

    hook_content = render_shell_hook(shell=shell, base_dir=paths["base_dir"])
    paths["hook_file"].write_text(hook_content, encoding="utf-8")

    if add_to_startup:
        ensure_rc_source_line(shell=shell, hook_file=paths["hook_file"])

    return paths["hook_file"]


def uninstall_managed_completion(shell: Shell) -> dict[str, list[Path]]:
    """Remove managed completion files for the current executable and shell.

    Deletes the hook file and the static completion script for the currently
    resolved CLI executable.  Files belonging to *other* exec_ids (i.e. other
    installations) are left untouched.  Also removes the RC source line added
    during install.

    Parameters
    ----------
    shell : {'bash', 'zsh'}
        Target shell whose managed files should be removed.

    Returns
    -------
    dict[str, list[Path]]
        Dictionary with keys ``"removed"`` and ``"missing"``, each containing
        a list of :class:`~pathlib.Path` objects that were successfully deleted
        or were not found, respectively.
    """
    exec_path = resolve_cli_executable()
    exec_id = stable_exec_id(exec_path)
    paths = managed_completion_paths(shell=shell, exec_id=exec_id)

    removed: list[Path] = []
    missing: list[Path] = []

    for key in ("hook_file", "static_file"):
        target = paths[key]
        if target.exists():
            target.unlink()
            removed.append(target)
        else:
            missing.append(target)

    remove_rc_source_line(shell=shell, hook_file=paths["hook_file"])

    return {"removed": removed, "missing": missing}
