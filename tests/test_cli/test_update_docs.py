# Copyright 2025 Entalpic
import siesta.cli as cli
from siesta.cli import app


def test_update_docs_no_selection_is_noop(tmp_path, monkeypatch, capture_output):
    """Test docs update exits cleanly when user selects no actions."""
    docs_path = tmp_path / "docs"
    (docs_path / "source" / "_static").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(cli.logger, "confirm", lambda _message: False)
    monkeypatch.setattr(
        cli,
        "copy_boilerplate",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("copy_boilerplate should not run on no-op selection")
        ),
    )
    monkeypatch.setattr(
        cli,
        "update_conf_py",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("update_conf_py should not run on no-op selection")
        ),
    )
    monkeypatch.setattr(
        cli,
        "write_or_update_pre_commit_file",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("pre-commit update should not run on no-op selection")
        ),
    )

    with capture_output() as output:
        try:
            app(["docs", "update"])
        except SystemExit as e:
            assert e.code == 0

    assert "No updates selected. Nothing to do." in output.getvalue()


def test_update_docs_collects_all_decisions_upfront(tmp_path, monkeypatch):
    """Test docs update asks all prompts before executing selected actions."""
    docs_path = tmp_path / "docs"
    (docs_path / "source" / "_static").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    events: list[str] = []
    answers = iter([False, True, False])

    def fake_confirm(message: str) -> bool:
        events.append(f"confirm:{message}")
        return next(answers)

    monkeypatch.setattr(cli.logger, "confirm", fake_confirm)
    monkeypatch.setattr(
        cli, "update_conf_py", lambda *_args, **_kwargs: events.append("update_conf_py")
    )
    monkeypatch.setattr(
        cli, "copy_boilerplate", lambda *_args, **_kwargs: events.append("copy")
    )

    try:
        app(["docs", "update"])
    except SystemExit as e:
        assert e.code == 0

    assert events[:3] == [
        "confirm:Overwrite the documentation's HTML static files. Continue?",
        "confirm:Would you like to update the conf.py file?",
        "confirm:Would you like to update the pre-commit hooks?",
    ]
    assert "update_conf_py" in events
    assert "copy" not in events
