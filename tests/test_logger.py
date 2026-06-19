# Copyright 2025 Entalpic
"""Tests for Logger confirmation behavior."""

from unittest.mock import patch

import pytest

from siesta.logger import Logger


@pytest.fixture
def logger():
    return Logger("test")


def test_prompt_uses_questionary_text(logger, monkeypatch):
    asked = {}

    class Prompt:
        def ask(self):
            return "  value  "

    def fake_text(message, default):
        asked["message"] = message
        asked["default"] = default
        return Prompt()

    monkeypatch.setattr("siesta.logger.questionary.text", fake_text)
    assert logger.prompt("Project name", default="proj") == "value"
    assert "[grey50 bold]" not in asked["message"]
    assert "[/grey50 bold]" not in asked["message"]
    assert asked["message"].startswith("[test | ")
    assert asked["message"].endswith("Project name")
    assert asked["default"] == "proj"


def test_prompt_cancellation_raises_keyboard_interrupt(logger, monkeypatch):
    class Prompt:
        def ask(self):
            return None

    monkeypatch.setattr(
        "siesta.logger.questionary.text", lambda *_args, **_kwargs: Prompt()
    )
    with pytest.raises(KeyboardInterrupt):
        logger.prompt("Project name")


def test_confirm_uses_questionary_confirm(logger, monkeypatch):
    asked = {}

    class Confirm:
        def ask(self):
            return True

    def fake_confirm(message, default):
        asked["message"] = message
        asked["default"] = default
        return Confirm()

    monkeypatch.setattr("siesta.logger.questionary.confirm", fake_confirm)
    assert logger.confirm("Continue?") is True
    assert "[grey50 bold]" not in asked["message"]
    assert "[/grey50 bold]" not in asked["message"]
    assert asked["message"].startswith("[test | ")
    assert asked["message"].endswith("Continue?")
    assert asked["default"] is True


def test_confirm_returns_false_when_declined(logger, monkeypatch):
    class Confirm:
        def ask(self):
            return False

    monkeypatch.setattr(
        "siesta.logger.questionary.confirm", lambda *_args, **_kwargs: Confirm()
    )
    assert logger.confirm("Continue?") is False


def test_confirm_defaults_to_true(logger, monkeypatch):
    asked = {}

    class Confirm:
        def ask(self):
            return True

    def fake_confirm(message, default):
        asked["message"] = message
        asked["default"] = default
        return Confirm()

    monkeypatch.setattr("siesta.logger.questionary.confirm", fake_confirm)
    assert logger.confirm("Continue?") is True
    assert asked["default"] is True


def test_confirm_accepts_false_default(logger, monkeypatch):
    asked = {}

    class Confirm:
        def ask(self):
            return False

    def fake_confirm(message, default):
        asked["message"] = message
        asked["default"] = default
        return Confirm()

    monkeypatch.setattr("siesta.logger.questionary.confirm", fake_confirm)
    assert logger.confirm("Continue?", default=False) is False
    assert asked["default"] is False


def test_confirm_cancellation_raises_keyboard_interrupt(logger, monkeypatch):
    class Confirm:
        def ask(self):
            return None

    monkeypatch.setattr(
        "siesta.logger.questionary.confirm", lambda *_args, **_kwargs: Confirm()
    )
    with pytest.raises(KeyboardInterrupt):
        logger.confirm("Continue?")


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


def test_checkbox_empty_choices_skips_questionary(logger, monkeypatch):
    def fail_checkbox(*_args, **_kwargs):
        raise AssertionError("questionary.checkbox should not be called")

    monkeypatch.setattr("siesta.logger.questionary.checkbox", fail_checkbox)
    assert logger.checkbox("Select items:", []) == []


def test_checkbox_checked_choices_are_preselected(logger, monkeypatch):
    captured = {}

    class Prompt:
        def ask(self):
            return ["a", "b"]

    def fake_checkbox(message, choices):
        captured["message"] = message
        captured["choices"] = choices
        return Prompt()

    monkeypatch.setattr("siesta.logger.questionary.checkbox", fake_checkbox)

    assert logger.checkbox("Select items:", ["a", "b"], checked=["a", "b"]) == [
        "a",
        "b",
    ]
    assert [choice.value for choice in captured["choices"]] == ["a", "b"]
    assert [choice.checked for choice in captured["choices"]] == [True, True]
