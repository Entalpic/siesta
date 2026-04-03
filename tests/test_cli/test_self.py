# Copyright 2025 Entalpic
"""Tests for siesta self commands (version, update, upgrade)."""

from unittest.mock import MagicMock, patch

import pytest

from siesta import __version__
from siesta.cli import app
from siesta.utils.github import format_github_access_error
from siesta.utils.self import (
    PACKAGE_NAME,
    compare_versions,
    get_installation_method,
    get_installation_source,
    get_latest_version,
    get_update_command,
)


class TestGetInstallationMethod:
    """Tests for get_installation_method()."""

    def test_detects_uv_tool_unix(self):
        """Test detection of uv tool installation on Unix."""
        with patch(
            "siesta.utils.self.sys.executable",
            "/home/user/.local/share/uv/tools/siesta/bin/python",
        ):
            assert get_installation_method() == "uv"

    def test_detects_uv_tool_windows(self):
        """Test detection of uv tool installation on Windows."""
        with patch(
            "siesta.utils.self.sys.executable",
            "C:\\Users\\user\\.local\\share\\uv\\tools\\siesta\\Scripts\\python.exe",
        ):
            assert get_installation_method() == "uv"

    def test_detects_pipx_unix(self):
        """Test detection of pipx installation on Unix."""
        with patch(
            "siesta.utils.self.sys.executable",
            "/home/user/.local/pipx/venvs/siesta/bin/python",
        ):
            assert get_installation_method() == "pipx"

    def test_detects_pipx_windows(self):
        """Test detection of pipx installation on Windows."""
        with patch(
            "siesta.utils.self.sys.executable",
            "C:\\Users\\user\\.local\\pipx\\venvs\\siesta\\Scripts\\python.exe",
        ):
            assert get_installation_method() == "pipx"

    def test_detects_editable_install(self):
        """Test detection of editable (development) installation."""
        mock_dist = MagicMock()
        mock_dist.read_text.return_value = '{"dir_info": {"editable": true}}'

        with (
            patch("siesta.utils.self.sys.executable", "/usr/bin/python3"),
            patch("siesta.utils.self.metadata.distribution", return_value=mock_dist),
        ):
            assert get_installation_method() == "editable"

    def test_defaults_to_pip(self):
        """Test fallback to pip for regular installations."""
        mock_dist = MagicMock()
        mock_dist.read_text.side_effect = FileNotFoundError

        with (
            patch("siesta.utils.self.sys.executable", "/usr/bin/python3"),
            patch("siesta.utils.self.metadata.distribution", return_value=mock_dist),
        ):
            assert get_installation_method() == "pip"


class TestGetInstallationSource:
    """Tests for get_installation_source()."""

    def test_detects_github_source(self):
        """Test detection of GitHub (git) installation source."""
        mock_dist = MagicMock()
        mock_dist.read_text.return_value = (
            '{"url": "git+ssh://git@github.com/entalpic/siesta.git", '
            '"vcs_info": {"vcs": "git", "commit_id": "abc123"}}'
        )

        with patch("siesta.utils.self.metadata.distribution", return_value=mock_dist):
            assert get_installation_source() == "github"

    def test_detects_pypi_source_no_direct_url(self):
        """Test detection of PyPI source when no direct_url.json exists."""
        mock_dist = MagicMock()
        mock_dist.read_text.side_effect = FileNotFoundError

        with patch("siesta.utils.self.metadata.distribution", return_value=mock_dist):
            assert get_installation_source() == "pypi"

    def test_detects_pypi_source_no_vcs_info(self):
        """Test detection of PyPI source when direct_url has no vcs_info."""
        mock_dist = MagicMock()
        mock_dist.read_text.return_value = (
            '{"url": "https://files.pythonhosted.org/..."}'
        )

        with patch("siesta.utils.self.metadata.distribution", return_value=mock_dist):
            assert get_installation_source() == "pypi"

    def test_detects_pypi_source_editable(self):
        """Test that editable installs are treated as pypi source."""
        mock_dist = MagicMock()
        mock_dist.read_text.return_value = '{"dir_info": {"editable": true}}'

        with patch("siesta.utils.self.metadata.distribution", return_value=mock_dist):
            assert get_installation_source() == "pypi"


class TestGetLatestVersion:
    """Tests for get_latest_version()."""

    def test_returns_version_from_pypi(self):
        """Test successful version fetch from PyPI when source is pypi."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"info": {"version": "2.0.0"}}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("siesta.utils.self.urlopen", return_value=mock_response):
            assert get_latest_version(source="pypi") == ("2.0.0", None)

    def test_returns_version_from_github_release(self):
        """Test successful version fetch from GitHub releases."""
        mock_release = MagicMock()
        mock_release.tag_name = "v2.0.0"

        mock_repo = MagicMock()
        mock_repo.get_latest_release.return_value = mock_release

        mock_github = MagicMock()
        mock_github.get_repo.return_value = mock_repo

        with patch("siesta.utils.github.Github", return_value=mock_github):
            assert get_latest_version(source="github") == ("2.0.0", None)

    def test_returns_version_from_github_tags_fallback(self):
        """Test fallback to GitHub tags when no releases exist."""
        from github import GithubException

        mock_tag = MagicMock()
        mock_tag.name = "v1.5.0"

        mock_tags = MagicMock()
        mock_tags.totalCount = 1
        mock_tags.__getitem__ = MagicMock(return_value=mock_tag)

        mock_repo = MagicMock()
        mock_repo.get_latest_release.side_effect = GithubException(
            404, "Not Found", None
        )
        mock_repo.get_tags.return_value = mock_tags

        mock_github = MagicMock()
        mock_github.get_repo.return_value = mock_repo

        with patch("siesta.utils.github.Github", return_value=mock_github):
            assert get_latest_version(source="github") == ("1.5.0", None)

    def test_returns_none_on_pypi_network_error(self):
        """Test None is returned on PyPI network failure."""
        from urllib.error import URLError

        with patch("siesta.utils.self.urlopen", side_effect=URLError("Network error")):
            assert get_latest_version(source="pypi") == (
                None,
                "<urlopen error Network error>",
            )

    def test_returns_none_on_pypi_json_error(self):
        """Test None is returned on invalid JSON response from PyPI."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"not valid json"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("siesta.utils.self.urlopen", return_value=mock_response):
            ver, err = get_latest_version(source="pypi")
            assert ver is None
            assert err is not None

    def test_auto_detects_source(self):
        """Test that source is auto-detected when not specified."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"info": {"version": "3.0.0"}}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with (
            patch("siesta.utils.self.get_installation_source", return_value="pypi"),
            patch("siesta.utils.self.urlopen", return_value=mock_response),
        ):
            assert get_latest_version() == ("3.0.0", None)


class TestFormatGithubAccessError:
    """Tests for format_github_access_error()."""

    def test_bad_credentials_message(self):
        """BadCredentialsException maps to PAT guidance."""
        from github import BadCredentialsException

        msg = format_github_access_error(
            BadCredentialsException(401, {"message": "Bad credentials"})
        )
        assert "token" in msg.lower()
        assert "set-github-pat" in msg

    def test_github_exception_includes_status(self):
        """Generic GithubException includes HTTP status and API message."""
        from github import GithubException

        msg = format_github_access_error(GithubException(404, {"message": "Not Found"}))
        assert "404" in msg
        assert "Not Found" in msg


class TestGetLatestCommitInfo:
    """Tests for get_latest_commit_info()."""

    def _make_mock_commit(self, sha: str, author: str, date):
        mock_author = MagicMock()
        mock_author.name = author
        mock_author.date = date

        mock_commit_obj = MagicMock()
        mock_commit_obj.author = mock_author

        mock_commit = MagicMock()
        mock_commit.sha = sha
        mock_commit.commit = mock_commit_obj
        return mock_commit

    def test_returns_commit_info_on_success(self):
        """Returns hash, author, and time for the latest commit."""
        from datetime import datetime, timezone

        from siesta.utils.github import get_latest_commit_info

        date = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        mock_commit = self._make_mock_commit("abc1234def", "Test User", date)

        mock_commits = MagicMock()
        mock_commits.__getitem__ = MagicMock(return_value=mock_commit)

        mock_repo = MagicMock()
        mock_repo.get_commits.return_value = mock_commits

        mock_github = MagicMock()
        mock_github.get_repo.return_value = mock_repo

        with (
            patch("siesta.utils.github.Github", return_value=mock_github),
            patch("siesta.utils.github.get_user_pat", return_value=None),
        ):
            info, err = get_latest_commit_info()

        assert err is None
        assert info is not None
        assert info["hash"] == "abc1234"
        assert info["author"] == "Test User"
        assert info["time"] == date

    def test_returns_none_on_github_exception(self):
        """GithubException is caught and error string is returned."""
        from github import GithubException

        from siesta.utils.github import get_latest_commit_info

        mock_github = MagicMock()
        mock_github.get_repo.side_effect = GithubException(
            403, {"message": "Forbidden"}
        )

        with (
            patch("siesta.utils.github.Github", return_value=mock_github),
            patch("siesta.utils.github.get_user_pat", return_value=None),
        ):
            info, err = get_latest_commit_info()

        assert info is None
        assert err is not None
        assert "403" in err

    def test_returns_none_none_on_index_error(self):
        """Empty commit list (IndexError) returns (None, None)."""
        from siesta.utils.github import get_latest_commit_info

        mock_commits = MagicMock()
        mock_commits.__getitem__ = MagicMock(side_effect=IndexError)

        mock_repo = MagicMock()
        mock_repo.get_commits.return_value = mock_commits

        mock_github = MagicMock()
        mock_github.get_repo.return_value = mock_repo

        with (
            patch("siesta.utils.github.Github", return_value=mock_github),
            patch("siesta.utils.github.get_user_pat", return_value=None),
        ):
            info, err = get_latest_commit_info()

        assert info is None
        assert err is None


class TestCompareVersions:
    """Tests for compare_versions()."""

    def test_current_less_than_latest(self):
        """Test when update is available."""
        assert compare_versions("1.0.0", "2.0.0") == -1

    def test_current_equals_latest(self):
        """Test when up to date."""
        assert compare_versions("1.0.0", "1.0.0") == 0

    def test_current_greater_than_latest(self):
        """Test when running pre-release version."""
        assert compare_versions("2.0.0", "1.0.0") == 1

    def test_prerelease_versions(self):
        """Test comparison with pre-release versions."""
        assert compare_versions("1.0.0-rc1", "1.0.0") == -1
        assert compare_versions("1.0.0", "1.0.0-rc1") == 1


class TestGetUpdateCommand:
    """Tests for get_update_command()."""

    def test_uv_command(self):
        """Test uv tool update command."""
        cmd = get_update_command("uv")
        assert cmd == ["uv", "tool", "upgrade", PACKAGE_NAME]

    def test_pipx_command(self):
        """Test pipx update command."""
        cmd = get_update_command("pipx")
        assert cmd == ["pipx", "upgrade", PACKAGE_NAME]

    def test_pip_command(self):
        """Test pip update command."""
        import sys

        cmd = get_update_command("pip")
        assert cmd == [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--upgrade",
            PACKAGE_NAME,
        ]

    def test_editable_raises_error(self):
        """Test editable installation raises ValueError."""
        with pytest.raises(ValueError, match="Editable installations"):
            get_update_command("editable")


class TestSelfVersionCommand:
    """Tests for 'siesta self version' command."""

    def _mock_commit_info(self):
        from datetime import datetime, timezone

        return {
            "hash": "abc1234",
            "author": "Test User",
            "time": datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
        }

    def test_version_command_shows_all_versions(self, capture_output):
        """Test that version command shows pip, release, and commit info."""
        with (
            patch(
                "siesta.cli.get_latest_github_release_version",
                return_value=(__version__, None),
            ),
            patch(
                "siesta.cli.get_latest_commit_info",
                return_value=(self._mock_commit_info(), None),
            ),
            capture_output() as output,
        ):
            try:
                app(["self", "version"])
            except SystemExit:
                pass

        output_str = output.getvalue()
        assert __version__ in output_str
        assert "abc1234" in output_str
        assert "Test User" in output_str

    def test_version_command_shows_update_available(self, capture_output):
        """Test that version command shows when update is available."""
        with (
            patch(
                "siesta.cli.get_latest_github_release_version",
                return_value=("99.0.0", None),
            ),
            patch(
                "siesta.cli.get_latest_commit_info",
                return_value=(self._mock_commit_info(), None),
            ),
            capture_output() as output,
        ):
            try:
                app(["self", "version"])
            except SystemExit:
                pass

        output_str = output.getvalue()
        assert "newer version" in output_str.lower() or "99.0.0" in output_str

    def test_version_command_handles_network_errors(self, capture_output):
        """Test that version command surfaces fetch failure details."""
        with (
            patch(
                "siesta.cli.get_latest_github_release_version",
                return_value=(None, "GitHub API 401: Bad credentials"),
            ),
            patch(
                "siesta.cli.get_latest_commit_info",
                return_value=(None, "GitHub API 401: Bad credentials"),
            ),
            capture_output() as output,
        ):
            try:
                app(["self", "version"])
            except SystemExit:
                pass

        output_str = output.getvalue()
        assert __version__ in output_str
        assert "could not fetch" in output_str.lower()
        assert "401" in output_str


class TestSelfUpdateCommand:
    """Tests for 'siesta self update' command."""

    def test_update_command_editable_shows_warning(self, capture_output):
        """Test that update command shows warning for editable installs."""
        with (
            patch("siesta.cli.get_installation_method", return_value="editable"),
            capture_output() as output,
        ):
            try:
                app(["self", "update"])
            except SystemExit:
                pass

        output_str = output.getvalue()
        assert "editable" in output_str.lower() or "git pull" in output_str.lower()

    def test_update_command_already_up_to_date(self, capture_output):
        """Test update command when already on latest version."""
        with (
            patch("siesta.cli.get_installation_method", return_value="pip"),
            patch("siesta.cli.get_latest_version", return_value=(__version__, None)),
            capture_output() as output,
        ):
            try:
                app(["self", "update"])
            except SystemExit:
                pass

        output_str = output.getvalue()
        assert "up to date" in output_str.lower() or __version__ in output_str

    def test_upgrade_alias_works(self, capture_output):
        """Test that 'upgrade' is an alias for 'update'."""
        with (
            patch("siesta.cli.get_installation_method", return_value="pip"),
            patch("siesta.cli.get_latest_version", return_value=(__version__, None)),
            capture_output() as output,
        ):
            try:
                app(["self", "upgrade"])
            except SystemExit:
                pass

        output_str = output.getvalue()
        # Should work without error, showing same behavior as update
        assert "up to date" in output_str.lower() or __version__ in output_str

    def test_dry_run_shows_command_uv(self, capture_output):
        """Test that --dry shows the uv command without executing."""
        with (
            patch("siesta.cli.get_installation_method", return_value="uv"),
            capture_output() as output,
        ):
            try:
                app(["self", "update", "--dry"])
            except SystemExit:
                pass

        output_str = output.getvalue()
        assert "uv tool" in output_str.lower()
        assert "would run" in output_str.lower()
        assert "uv tool upgrade siesta" in output_str.lower()

    def test_dry_run_shows_command_pipx(self, capture_output):
        """Test that --dry shows the pipx command without executing."""
        with (
            patch("siesta.cli.get_installation_method", return_value="pipx"),
            capture_output() as output,
        ):
            try:
                app(["self", "update", "--dry"])
            except SystemExit:
                pass

        output_str = output.getvalue()
        assert "pipx" in output_str.lower()
        assert "would run" in output_str.lower()
        assert "pipx upgrade siesta" in output_str.lower()

    def test_dry_run_shows_command_pip(self, capture_output):
        """Test that --dry shows the pip command without executing."""
        with (
            patch("siesta.cli.get_installation_method", return_value="pip"),
            capture_output() as output,
        ):
            try:
                app(["self", "update", "--dry"])
            except SystemExit:
                pass

        output_str = output.getvalue()
        assert "pip" in output_str.lower()
        assert "would run" in output_str.lower()
        # The pip command uses `python -m pip install --upgrade siesta`
        # Output may be wrapped across lines, so check for key parts
        assert "-m pip" in output_str.lower()
        assert "--upgrade siesta" in output_str.lower()
