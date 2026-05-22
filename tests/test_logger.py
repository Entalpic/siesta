# Copyright 2025 Entalpic
"""Tests for Logger confirmation behavior."""

from unittest.mock import patch

import sys
import pytest

from siesta.logger import Logger


@pytest.fixture
def logger():
    return Logger("test")


def test_confirm_secret_accepts_explicit_yes(logger):
    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("builtins.input", return_value="y"),
    ):
        assert logger.confirm_secret("Reveal secret?") is True


def test_confirm_secret_accepts_yes_spelled_out(logger):
    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("builtins.input", return_value="yes"),
    ):
        assert logger.confirm_secret("Reveal secret?") is True


def test_confirm_secret_declines_empty_input(logger):
    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("builtins.input", return_value=""),
    ):
        assert logger.confirm_secret("Reveal secret?") is False


def test_confirm_secret_declines_eof(logger):
    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("builtins.input", side_effect=EOFError),
    ):
        assert logger.confirm_secret("Reveal secret?") is False


def test_confirm_secret_declines_non_tty(logger):
    with patch("sys.stdin.isatty", return_value=False):
        assert logger.confirm_secret("Reveal secret?") is False
