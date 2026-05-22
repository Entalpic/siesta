# Copyright 2025 Entalpic
from unittest.mock import patch

import pytest

from siesta.cli.main_app import app


def test_set_github_pat_rejects_argv_token(capture_output):
    """PAT values passed on the command line must not be accepted."""
    with patch("keyring.set_password") as mock_set_password:
        with capture_output():
            with pytest.raises(SystemExit) as exc_info:
                app(["self", "set-github-pat", "secret-token-on-argv"])

    assert exc_info.value.code != 0
    mock_set_password.assert_not_called()


def test_set_github_pat_interactive_success(capture_output):
    """Interactive getpass + confirmation stores the PAT in keyring."""
    with (
        patch(
            "siesta.cli.self_app.getpass.getpass",
            return_value="interactive-pat-token",
        ),
        patch("siesta.cli.self_app.logger.confirm_secret", return_value=True),
        patch("keyring.set_password") as mock_set_password,
        capture_output() as output,
    ):
        try:
            app(["self", "set-github-pat"])
        except SystemExit as e:
            assert e.code == 0

    mock_set_password.assert_called_once_with(
        "siesta", "github_pat", "interactive-pat-token"
    )
    assert "secret-token-on-argv" not in output.getvalue()
    assert "interactive-pat-token" not in output.getvalue()


def test_set_github_pat_interactive_cancelled(capture_output):
    """Declined confirmation must not persist the PAT."""
    with (
        patch(
            "siesta.cli.self_app.getpass.getpass",
            return_value="interactive-pat-token",
        ),
        patch("siesta.cli.self_app.logger.confirm_secret", return_value=False),
        patch("keyring.set_password") as mock_set_password,
        capture_output() as output,
    ):
        try:
            app(["self", "set-github-pat"])
        except SystemExit as e:
            assert e.code == 0

    mock_set_password.assert_not_called()
    assert "not set" in output.getvalue().lower()
