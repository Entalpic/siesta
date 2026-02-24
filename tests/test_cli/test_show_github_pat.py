# Copyright 2025 Entalpic
from unittest.mock import patch

from siesta.cli import app


def test_show_github_pat_masked(capture_output):
    """Test that show-github-pat displays a masked token by default."""
    with capture_output() as output:
        app(["self", "show-github-pat"])

    output_text = output.getvalue()
    assert "fake-github-" in output_text
    assert "ting" in output_text
    assert "fake-github-pat-for-testing" not in output_text
    assert "--full" in output_text


def test_show_github_pat_full(capture_output):
    """Test that show-github-pat --full displays the full token with a warning."""
    with capture_output() as output:
        app(["self", "show-github-pat", "--full"])

    output_text = output.getvalue()
    assert "fake-github-pat-for-testing" in output_text
    assert "plaintext" in output_text


def test_show_github_pat_none(capture_output):
    """Test that show-github-pat warns when no PAT is stored."""
    with (
        patch("siesta.utils.github.get_user_pat", return_value=None),
        patch("siesta.cli.get_user_pat", return_value=None),
    ):
        with capture_output() as output:
            app(["self", "show-github-pat"])

    output_text = output.getvalue()
    assert "No GitHub PAT found" in output_text
    assert "set-github-pat" in output_text
