# Copyright 2025 Entalpic
from unittest.mock import patch

from siesta.cli.main_app import app


def test_show_github_pat_masked(capture_output):
    """Test that show-github-pat displays a masked token by default."""
    with capture_output() as output:
        try:
            app(["self", "show-github-pat"])
        except SystemExit as e:
            assert e.code == 0

    output_text = output.getvalue()
    assert "fake-github-" in output_text
    assert "ting" in output_text
    assert "fake-github-pat-for-testing" not in output_text
    assert "--full" in output_text


def test_show_github_pat_full(capture_output):
    """Test that show-github-pat --full displays the full token after confirmation."""
    with patch("siesta.cli.self_app.logger.confirm_secret", return_value=True):
        with capture_output() as output:
            try:
                app(["self", "show-github-pat", "--full"])
            except SystemExit as e:
                assert e.code == 0

    output_text = output.getvalue()
    assert "fake-github-pat-for-testing" in output_text
    assert "plaintext" in output_text


def test_show_github_pat_full_cancelled(capture_output):
    """Test that cancelling --full confirmation shows masked token instead."""
    with patch("siesta.cli.self_app.logger.confirm_secret", return_value=False):
        with capture_output() as output:
            try:
                app(["self", "show-github-pat", "--full"])
            except SystemExit as e:
                assert e.code == 0

    output_text = output.getvalue()
    assert "fake-github-pat-for-testing" not in output_text
    assert "fake-github-" in output_text
    assert "cancelled" in output_text.lower()


def test_show_github_pat_full_declines_non_interactive(capture_output):
    """Test that --full never reveals PAT when stdin is non-interactive."""
    with patch("siesta.cli.self_app.logger.confirm_secret", return_value=False):
        with capture_output() as output:
            try:
                app(["self", "show-github-pat", "--full"])
            except SystemExit as e:
                assert e.code == 0

    output_text = output.getvalue()
    assert "fake-github-pat-for-testing" not in output_text
    assert "fake-github-" in output_text


def test_show_github_pat_none(capture_output):
    """Test that show-github-pat warns when no PAT is stored."""
    with patch("siesta.utils.github.get_user_pat", return_value=None):
        with capture_output() as output:
            try:
                app(["self", "show-github-pat"])
            except SystemExit as e:
                assert e.code == 0

    output_text = output.getvalue()
    assert "No GitHub PAT found" in output_text
    assert "set-github-pat" in output_text
