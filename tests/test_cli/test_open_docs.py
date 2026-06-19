# Copyright 2025 Entalpic
import re
from unittest.mock import patch

import pytest

from siesta.cli.main_app import app


@pytest.mark.parametrize("platform", ["Darwin", "Windows", "Linux"])
def test_open_docs(module_test_path, capture_output, platform, monkeypatch):
    """Test opening the docs in the default browser."""
    monkeypatch.chdir(module_test_path)

    with capture_output() as output:
        with patch("siesta.cli.docs_app.platform.system") as mock_system:
            mock_system.return_value = platform

            # Only mock os.startfile for Windows
            if platform == "Windows":
                with patch(
                    "siesta.cli.docs_app.os.startfile", create=True
                ) as mock_startfile:
                    with patch("siesta.cli.docs_app.subprocess.call") as mock_call:
                        try:
                            app(["docs", "open"])
                        except SystemExit as e:
                            assert e.code == 0
                        mock_startfile.assert_called_once_with(
                            str(
                                module_test_path
                                / "docs"
                                / "build"
                                / "html"
                                / "index.html"
                            )
                        )
                        # subprocess.call should not be called on Windows
                        mock_call.assert_not_called()
            else:
                # For Darwin and Linux, only mock subprocess.call
                with patch("siesta.cli.docs_app.subprocess.call") as mock_call:
                    try:
                        app(["docs", "open"])
                    except SystemExit as e:
                        assert e.code == 0
                    if platform == "Darwin":
                        mock_call.assert_called_once_with(
                            (
                                "open",
                                str(
                                    module_test_path
                                    / "docs"
                                    / "build"
                                    / "html"
                                    / "index.html"
                                ),
                            )
                        )
                    else:  # Linux
                        mock_call.assert_called_once_with(
                            (
                                "xdg-open",
                                str(
                                    module_test_path
                                    / "docs"
                                    / "build"
                                    / "html"
                                    / "index.html"
                                ),
                            )
                        )
    assert "Opening" in output.getvalue()
    assert re.search(r"index\s*\.html", output.getvalue())
