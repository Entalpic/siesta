# Copyright 2025 Entalpic
import runpy

import pytest

import siesta.cli.docs_app as cli
from siesta.cli.main_app import app


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
        try:
            app(["docs", "init", "--overwrite"])
        except SystemExit as e:
            assert e.code == 0
    assert "Failed to build the docs" not in output.getvalue()

    assert not (docs_dir / "marker.txt").exists()
    assert (docs_dir / "source" / "conf.py").exists()


def test_init_docs_with_backup(
    temp_project_with_git_and_remote, monkeypatch, capture_output
):
    """Test that --backup renames existing docs to docs.bak before init."""
    monkeypatch.chdir(temp_project_with_git_and_remote)
    docs_dir = temp_project_with_git_and_remote / "docs"
    docs_dir.mkdir()
    (docs_dir / "marker.txt").write_text("original content")

    with capture_output():
        try:
            app(["docs", "init", "--overwrite", "--backup"])
        except SystemExit as e:
            assert e.code == 0

    assert (temp_project_with_git_and_remote / "docs.bak" / "marker.txt").exists()
    assert (docs_dir / "source" / "conf.py").exists()


def test_init_docs_package_discovery(
    temp_project_with_git_and_remote, monkeypatch, capture_output
):
    """Test that docs init correctly discovers and configures packages."""
    monkeypatch.chdir(temp_project_with_git_and_remote)

    with capture_output() as output:
        try:
            app(["docs", "init"])
        except SystemExit as e:
            assert e.code == 0
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
        try:
            app(["docs", "init"])
        except SystemExit as e:
            assert e.code == 0
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


def test_init_docs_escapes_project_name_in_conf_py(
    temp_project_with_git_and_remote, monkeypatch, capture_output
):
    """Generated Sphinx config treats project names as string data."""
    monkeypatch.chdir(temp_project_with_git_and_remote)
    project_name = '"; import os; #'

    with capture_output() as output:
        try:
            app(["docs", "init", "--project-name", project_name])
        except SystemExit as e:
            assert e.code == 0
    assert "Failed to build the docs" not in output.getvalue()

    conf_py = temp_project_with_git_and_remote / "docs" / "source" / "conf.py"
    conf_globals = runpy.run_path(str(conf_py))

    assert conf_globals["project"] == project_name
    assert conf_globals["html_title"] == project_name
    assert conf_globals["html_theme_options"]["nav_links"][0]["title"] == project_name


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
        try:
            app(["docs", "init", "--no-deps"])
        except SystemExit as e:
            assert e.code == 0

    output_text = output.getvalue()
    # deps should be False (user specified --no-deps)
    assert "Skipping dependency installation" in output_text
    # Docs should still be created
    docs_dir = temp_project_with_git_and_remote / "docs"
    assert docs_dir.exists()
    assert (docs_dir / "source" / "conf.py").exists()


def test_init_docs_collects_prompts_before_mutation(
    temp_project_with_git_and_remote, monkeypatch
):
    """Test that docs init collects interactive decisions before mutating state."""
    monkeypatch.chdir(temp_project_with_git_and_remote)
    (temp_project_with_git_and_remote / "uv.lock").write_text("")
    events: list[str] = []

    def fake_confirm(message: str) -> bool:
        events.append(f"confirm:{message}")
        return True

    monkeypatch.setattr("siesta.cli.docs_app.logger.confirm", fake_confirm)
    monkeypatch.setattr(
        cli, "install_dependencies", lambda *_args, **_kwargs: events.append("install")
    )
    monkeypatch.setattr(
        cli, "copy_boilerplate", lambda *_args, **_kwargs: events.append("copy")
    )
    monkeypatch.setattr(
        cli, "make_empty_folders", lambda *_args, **_kwargs: events.append("empty")
    )
    monkeypatch.setattr(
        cli,
        "overwrite_docs_files",
        lambda *_args, **_kwargs: events.append("overwrite"),
    )
    monkeypatch.setattr(
        cli, "write_rtd_config", lambda *_args, **_kwargs: events.append("rtd")
    )
    monkeypatch.setattr(
        cli, "build_docs", lambda *_args, **_kwargs: events.append("build")
    )

    orig_mkdir = cli.Path.mkdir

    def tracked_mkdir(path_obj, *args, **kwargs):
        events.append("mkdir")
        return orig_mkdir(path_obj, *args, **kwargs)

    monkeypatch.setattr(cli.Path, "mkdir", tracked_mkdir)

    with pytest.raises(SystemExit) as exc_info:
        app(["docs", "init", "-i"])
    assert exc_info.value.code == 0

    prompt_indices = [
        i for i, event in enumerate(events) if event.startswith("confirm:")
    ]
    first_mutation_idx = next(
        i for i, event in enumerate(events) if not event.startswith("confirm:")
    )
    assert prompt_indices
    assert max(prompt_indices) < first_mutation_idx


def test_init_docs_cancel_during_prompt_has_no_mutation(
    temp_project_with_git_and_remote, monkeypatch
):
    """Test cancellation during prompt collection leaves project untouched."""
    monkeypatch.chdir(temp_project_with_git_and_remote)

    def fail_mkdir(*_args, **_kwargs):
        raise AssertionError("mkdir should not be called on cancellation")

    def fail_install_dependencies(*_args, **_kwargs):
        raise AssertionError(
            "install_dependencies should not be called on cancellation"
        )

    monkeypatch.setattr(
        "siesta.cli.docs_app.logger.confirm",
        lambda _message: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    monkeypatch.setattr(cli.Path, "mkdir", fail_mkdir)
    monkeypatch.setattr(cli, "install_dependencies", fail_install_dependencies)

    with pytest.raises(SystemExit) as exc_info:
        app(["docs", "init", "-i"])
    assert exc_info.value.code == 130

    assert not (temp_project_with_git_and_remote / "docs").exists()
