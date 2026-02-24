# Copyright 2025 Entalpic
import pytest

from siesta.cli import app


def test_init_docs_basic(temp_project_with_git_and_remote, monkeypatch):
    """Test basic docs initialization with defaults."""
    # Change to temp project directory
    monkeypatch.chdir(temp_project_with_git_and_remote)

    try:
        app(["docs", "init"])
    except SystemExit as e:
        assert e.code == 0

    docs_dir = temp_project_with_git_and_remote / "docs"
    assert docs_dir.exists()

    # Check essential files exist
    assert (docs_dir / "source" / "conf.py").exists()
    assert (docs_dir / "source" / "index.rst").exists()
    assert (docs_dir / "source" / "_static").exists()
    assert (docs_dir / "source" / "_templates").exists()
    assert (docs_dir / "Makefile").exists()


def test_init_docs_no_overwrite(
    temp_project_with_git_and_remote, monkeypatch, capture_output
):
    """Test that docs init fails when docs exist and --overwrite is not used."""
    monkeypatch.chdir(temp_project_with_git_and_remote)

    # Create docs dir
    docs_dir = temp_project_with_git_and_remote / "docs"
    docs_dir.mkdir()

    with pytest.raises(SystemExit) as exc_info:
        with capture_output() as output:
            app(["docs", "init"])
        assert "Path already exists" in output.getvalue()

    assert exc_info.value.code == 1


def test_init_docs_with_overwrite(
    temp_project_with_git_and_remote, monkeypatch, capture_output
):
    """Test that docs init succeeds when --overwrite is used on existing docs."""
    monkeypatch.chdir(temp_project_with_git_and_remote)

    # Create docs dir with a marker file
    docs_dir = temp_project_with_git_and_remote / "docs"
    docs_dir.mkdir()
    (docs_dir / "marker.txt").write_text("original content")

    with capture_output() as output:
        app(["docs", "init", "--overwrite"])
    assert "Failed to build the docs" not in output.getvalue()

    assert not (docs_dir / "marker.txt").exists()
    assert (docs_dir / "source" / "conf.py").exists()


def test_init_docs_package_discovery(
    temp_project_with_git_and_remote, monkeypatch, capture_output
):
    """Test that docs init correctly discovers and configures packages."""
    monkeypatch.chdir(temp_project_with_git_and_remote)

    with capture_output() as output:
        app(["docs", "init"])
    assert "Failed to build the docs" not in output.getvalue()

    # Check conf.py contains discovered package
    conf_py = temp_project_with_git_and_remote / "docs" / "source" / "conf.py"
    conf_content = conf_py.read_text()
    assert 'autoapi_dirs = ["../../src/mypackage"]' in conf_content


def test_init_docs_project_name(
    temp_project_with_git_and_remote, monkeypatch, capture_output
):
    """Test that docs init uses correct project name in generated files."""
    monkeypatch.chdir(temp_project_with_git_and_remote)

    with capture_output() as output:
        app(["docs", "init"])
    assert "Failed to build the docs" not in output.getvalue()

    # Check project name in conf.py
    conf_py = temp_project_with_git_and_remote / "docs" / "source" / "conf.py"
    conf_content = conf_py.read_text()

    assert 'project = "test_init_docs_project_name0"' in conf_content

    # Check project name in index.rst template
    index_rst = (
        temp_project_with_git_and_remote
        / "docs"
        / "source"
        / "_templates"
        / "autoapi"
        / "index.rst"
    )
    index_content = index_rst.read_text()
    assert "test_init_docs_project_name0" in index_content


def test_init_docs_no_python_files(tmp_path, monkeypatch, capture_output):
    """Test that docs init fails when no Python files are found."""
    # Change to temp project directory
    monkeypatch.chdir(tmp_path)

    # Remove the Python file created in the fixture

    with pytest.raises(SystemExit) as exc_info:
        with capture_output() as output:
            app(["docs", "init"])
        assert "No Python files found in project" in output.getvalue()

    assert exc_info.value.code == 1


def test_init_docs_respects_no_deps(
    temp_project_with_git_and_remote, monkeypatch, capture_output
):
    """Test that user flags take precedence (--no-deps)."""
    monkeypatch.chdir(temp_project_with_git_and_remote)

    with capture_output() as output:
        # User specifies --no-deps, defaults should not override it
        app(["docs", "init", "--no-deps"])

    output_text = output.getvalue()
    # deps should be False (user specified --no-deps)
    assert "Skipping dependency installation" in output_text
    # Docs should still be created
    docs_dir = temp_project_with_git_and_remote / "docs"
    assert docs_dir.exists()
    assert (docs_dir / "source" / "conf.py").exists()
