# Copyright 2025 Entalpic
from pathlib import Path
from textwrap import dedent

import pytest

from siesta.utils.tree import (
    SPACE,
    TREE_LABELS,
    func_or,
    get_filler_from_line,
    label_tree,
    tree,
    wrap_consequent_chars,
)


def test_func_or():
    assert func_or(lambda x: x > 0, lambda x: x < 0)(1)
    assert func_or(lambda x: x > 0, lambda x: x < 0)(-1)
    assert not func_or(lambda x: x > 0, lambda x: x < 0)(0)


@pytest.mark.parametrize(
    "tree_line,pattern",
    [
        ("├── source/", "│"),
        ("├── source" + "eza" * 10, "│"),
        ("└── README.md", SPACE + "│"),
        ("│   │   ├── conf.py", "│   │   │"),
    ],
)
def test_filler_from_line(tree_line, pattern):
    target_line_length = 30
    n_indent = 5
    indent = " " * n_indent
    line = indent + tree_line
    expected = (
        indent + pattern + " " * (target_line_length - n_indent - len(pattern) + 4)
    )
    assert len(get_filler_from_line(line, target_line_length)) == len(expected)
    assert get_filler_from_line(line, target_line_length) == expected


def test_tree_no_gitignore(tmp_path_chdir):
    (tmp_path_chdir / ".gitignore").touch()
    (tmp_path_chdir / "src").mkdir()
    (tmp_path_chdir / "src" / "main.py").touch()
    tree_lines = "\n".join(t["line"] for t in tree(tmp_path_chdir))
    assert tree_lines == dedent(
        """\
        ├── .gitignore
        └── src/
            └── main.py
        """.rstrip()
    )


def test_tree_with_gitignore(tmp_path_chdir):
    (tmp_path_chdir / ".gitignore").write_text("*.txt")
    (tmp_path_chdir / "src").mkdir()
    (tmp_path_chdir / "src" / "main.py").touch()
    (tmp_path_chdir / "src" / "main.txt").touch()
    tree_lines = "\n".join(t["line"] for t in tree(tmp_path_chdir))
    assert tree_lines == dedent(
        """\
        ├── .gitignore
        └── src/
            └── main.py
        """.rstrip()
    )


def test_tree_with_nested_gitignore(tmp_path_chdir):
    (tmp_path_chdir / ".gitignore").write_text("*.txt")
    (tmp_path_chdir / "src").mkdir()
    (tmp_path_chdir / "src" / ".gitignore").write_text("*.py")
    (tmp_path_chdir / "file.py").touch()
    (tmp_path_chdir / "src" / "main.py").touch()
    (tmp_path_chdir / "src" / "main.txt").touch()
    (tmp_path_chdir / "src" / "main.yaml").touch()
    tree_lines = "\n".join(t["line"] for t in tree(tmp_path_chdir))
    print(tree_lines)
    print("-----------------")
    assert tree_lines == dedent(
        """\
        ├── .gitignore
        ├── file.py
        └── src/
            ├── .gitignore
            └── main.yaml
        """.rstrip()
    )


def test_wrap_consequent_chars():
    assert (
        wrap_consequent_chars("Hello ·········· World", "·", "bold grey3")
        == "Hello [bold grey3]··········[/bold grey3] World"
    )
    assert wrap_consequent_chars("Hello World", "·", "bold grey3") == "Hello World"
    assert (
        wrap_consequent_chars("Hello\nWorld", "·", "bold grey3", True) == "Hello\nWorld"
    )
    assert (
        wrap_consequent_chars("Hel·lo\nWo·rld", "·", "blue", True)
        == "Hel[blue]·[/blue]lo\nWo[blue]·[/blue]rld"
    )


# FIXME
def test_label_tree():
    tree_lines = dedent(
        """\
        ├── .gitignore
        ├── file.py
        └── src/
            ├── .gitignore
            └── main.yaml
        """.rstrip()
    ).split("\n")
    tree_paths = [
        Path(p)
        for p in [
            ".gitignore",
            "file.py",
            "src",
            "src/.gitignore",
            "src/main.yaml",
        ]
    ]
    tree_dicts = [
        {"line": line, "path": path} for line, path in zip(tree_lines, tree_paths)
    ]

    assert "\n".join(label_tree(tree_dicts, Path(), 200)) == wrap_consequent_chars(
        dedent(
            f"""\
            ├── .gitignore ···· [grey50]# {TREE_LABELS[".gitignore"]}[/grey50]
            ├── file.py
            └── src/ ·········· [grey50]# {TREE_LABELS["src/"]}[/grey50]
                ├── .gitignore
                └── main.yaml
            """.rstrip()
        ),
        split_new_lines=True,
    )
