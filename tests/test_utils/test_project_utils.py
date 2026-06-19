# Copyright 2025 Entalpic
from siesta.utils.common import safe_load
from siesta.utils.project import (
    add_ipdb_as_debugger,
    write_test_actions_config,
    write_tests_infra,
)


def test_write_test_actions_config(tmp_path_chdir):
    write_test_actions_config()

    assert (tmp_path_chdir / ".github" / "workflows" / "test.yml").exists()
    assert safe_load(tmp_path_chdir / ".github" / "workflows" / "test.yml")


def test_write_test_actions_config_overwrites_existing(tmp_path_chdir):
    (tmp_path_chdir / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
    write_test_actions_config()
    assert (tmp_path_chdir / ".github" / "workflows" / "test.yml").exists()
    assert safe_load(tmp_path_chdir / ".github" / "workflows" / "test.yml")


def test_write_tests_infra(tmp_path_chdir):
    write_tests_infra("some_project")

    assert (tmp_path_chdir / "tests" / "test_import.py").exists()
    txt = (tmp_path_chdir / "tests" / "test_import.py").read_text()
    assert "importlib.import_module('some_project')" in txt


def test_write_tests_infra_escapes_generated_import(tmp_path_chdir):
    """Generated import tests treat project names as string data."""
    write_tests_infra('some_project");\nimport os\n#')

    txt = (tmp_path_chdir / "tests" / "test_import.py").read_text()

    assert "\nimport os\n" not in txt
    assert "importlib.import_module(" in txt


def test_write_tests_infra_overwrites_existing(tmp_path_chdir):
    (tmp_path_chdir / "tests").mkdir(parents=True, exist_ok=True)
    write_tests_infra("some_project")
    assert (tmp_path_chdir / "tests" / "test_import.py").exists()
    txt = (tmp_path_chdir / "tests" / "test_import.py").read_text()
    assert "importlib.import_module('some_project')" in txt


def test_add_ipdb_as_debugger(tmp_path_chdir):
    (tmp_path_chdir / "src" / "some_project").mkdir(parents=True, exist_ok=True)
    (tmp_path_chdir / "src" / "some_project" / "__init__.py").touch()

    add_ipdb_as_debugger()

    assert (tmp_path_chdir / "src" / "some_project" / "__init__.py").exists()
    txt = (tmp_path_chdir / "src" / "some_project" / "__init__.py").read_text()
    assert "import ipdb" in txt and "PYTHONBREAKPOINT" in txt


def test_add_ipdb_as_debugger_no_init(tmp_path_chdir, capture_output):
    with capture_output() as output:
        add_ipdb_as_debugger()
    assert "No __init__.py files found. Skipping ipdb debugger." in output.getvalue()
