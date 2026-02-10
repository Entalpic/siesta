# Copyright 2025 Entalpic
from siesta.cli import app
from siesta.utils.common import load_deps


def test_show_deps(capture_output):
    """Test the self show-deps command outputs the expected dependencies."""
    with capture_output() as output:
        try:
            app(["self", "show-deps"])
        except SystemExit as e:
            assert e.code == 0

    output = output.getvalue()

    # Load expected deps from dependencies.json
    deps = load_deps()
    # Check each dependency appears in output
    for scope in deps:
        for dep in deps[scope]:
            assert dep in output
