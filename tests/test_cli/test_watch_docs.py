# Copyright 2025 Entalpic
from unittest.mock import Mock, patch

import pytest
from watchdog.observers import Observer

from siesta.cli import app
from siesta.utils.docs import AutoBuildDocs


def test_watch_docs_path_not_found(capture_output):
    """Test watch_docs fails when path doesn't exist."""
    with pytest.raises(SystemExit) as exc_info:
        with capture_output() as output:
            app(["docs watch", "--path", "nonexistent/path"])
        assert "Path not found" in output.getvalue()

    assert exc_info.value.code == 1


def test_watch_docs_observer_setup(module_test_path, monkeypatch, capture_output):
    """Test watch_docs sets up observer correctly."""
    monkeypatch.chdir(module_test_path)

    mock_observer = Mock(spec=Observer)
    mock_observer_instance = mock_observer.return_value

    with (
        patch("siesta.cli.Observer", mock_observer),
        patch("time.sleep", side_effect=KeyboardInterrupt),
    ):
        with capture_output() as output:
            try:
                app(["docs", "watch"])
            except SystemExit as e:
                assert e.code == 0

    # Verify observer was started
    assert mock_observer_instance.start.called
    # Verify observer was stopped after KeyboardInterrupt
    assert mock_observer_instance.stop.called
    assert mock_observer_instance.join.called
    # Verify watching message
    assert "Watching stopped" in output.getvalue()


@pytest.mark.parametrize(
    "src_path, target",
    [
        ("src/mypackage/test.py", True),
        ("docs/source/index.rst", True),
        ("docs/source/autoapi/index.rst", False),
    ],
)
def test_autobuild_on_modified(module_test_path, monkeypatch, src_path, target):
    """Test AutoBuildDocs handler processes file changes correctly."""
    monkeypatch.chdir(module_test_path)

    # Create mock build command
    mock_build = Mock()

    # Create AutoBuild instance with test patterns
    patterns = [r".+/src/.+\.py", r".+/source/.+\.rst"]
    handler = AutoBuildDocs(patterns, mock_build, "docs")

    # Test Python source file change
    mock_event = Mock()
    mock_event.src_path = src_path
    handler.on_modified(mock_event)
    assert mock_build.called is target


def test_watch_docs_custom_patterns(module_test_path, monkeypatch, capture_output):
    """Test watch_docs accepts custom patterns."""
    monkeypatch.chdir(module_test_path)

    mock_observer = Mock(spec=Observer)
    custom_patterns = "custom/*.py;other/*.rst"

    with (
        patch("siesta.cli.Observer", mock_observer),
        patch("time.sleep", side_effect=KeyboardInterrupt),
    ):
        with capture_output():
            try:
                app(["docs", "watch", "--patterns", custom_patterns])
            except SystemExit as e:
                assert e.code == 0

    # Verify observer was scheduled with handler using custom patterns
    schedule_call = mock_observer.return_value.schedule.call_args[0]
    handler = schedule_call[0]
    assert isinstance(handler, AutoBuildDocs)
    assert list(map(lambda x: x.pattern, handler.regexes)) == [
        p.strip() for p in custom_patterns.split(";")
    ]
