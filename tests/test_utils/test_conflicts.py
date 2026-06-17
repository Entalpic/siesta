# Copyright 2025 Entalpic
import sys

import pytest

from siesta.utils.common import logger
from siesta.utils.conflicts import (
    Conflict,
    OperationSummary,
    Resolution,
    apply_backup,
    resolve_conflict,
    run_mutations,
    write_path,
)


class _AbortMutation:
    def detect_conflicts(self):
        return [
            Conflict(
                key="abort",
                name="test artifact",
                options=frozenset(
                    {Resolution.SKIP, Resolution.OVERWRITE, Resolution.ABORT}
                ),
            )
        ]

    def apply(self, resolutions):
        summary = OperationSummary()
        summary.written.append("should-not-write")
        return summary


class _OrderMutation:
    def __init__(self, key: str, order: list[str]):
        self.key = key
        self.order = order

    def detect_conflicts(self):
        return []

    def apply(self, resolutions):
        self.order.append(self.key)
        return OperationSummary()


class TestResolveConflict:
    def test_overwrite_false_skips(self, capture_output):
        c = Conflict(
            "k",
            "file.txt",
            frozenset({Resolution.SKIP, Resolution.OVERWRITE, Resolution.ABORT}),
        )
        assert resolve_conflict(c, overwrite=False, backup=False) is Resolution.SKIP

    def test_overwrite_true_overwrites(self):
        c = Conflict(
            "k",
            "file.txt",
            frozenset({Resolution.SKIP, Resolution.OVERWRITE, Resolution.ABORT}),
        )
        assert resolve_conflict(c, overwrite=True, backup=False) is Resolution.OVERWRITE

    def test_overwrite_true_with_backup(self):
        c = Conflict(
            "k",
            "file.txt",
            frozenset(
                {
                    Resolution.SKIP,
                    Resolution.OVERWRITE,
                    Resolution.BACKUP,
                    Resolution.ABORT,
                }
            ),
        )
        assert resolve_conflict(c, overwrite=True, backup=True) is Resolution.BACKUP

    def test_uv_init_subset_skips_on_overwrite(self):
        c = Conflict("uv", "uv project", frozenset({Resolution.SKIP, Resolution.ABORT}))
        assert resolve_conflict(c, overwrite=True, backup=False) is Resolution.SKIP

    def test_claude_merge_on_overwrite(self):
        c = Conflict(
            "claude",
            "CLAUDE.md",
            frozenset({Resolution.SKIP, Resolution.MERGE, Resolution.ABORT}),
        )
        assert resolve_conflict(c, overwrite=True, backup=False) is Resolution.MERGE

    def test_non_tty_aborts(self, monkeypatch):
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        c = Conflict(
            "k",
            "file.txt",
            frozenset({Resolution.SKIP, Resolution.OVERWRITE, Resolution.ABORT}),
        )
        with pytest.raises(SystemExit):
            resolve_conflict(c, overwrite=None, backup=False)


class TestWritePath:
    def test_skip(self, tmp_path):
        dest = tmp_path / "out.txt"
        dest.write_text("keep")
        assert write_path(None, dest, Resolution.SKIP) is Resolution.SKIP
        assert dest.read_text() == "keep"

    def test_overwrite_file(self, tmp_path):
        src = tmp_path / "src.txt"
        dest = tmp_path / "dest.txt"
        src.write_text("new")
        dest.write_text("old")
        write_path(src, dest, Resolution.OVERWRITE)
        assert dest.read_text() == "new"

    def test_backup_then_write(self, tmp_path):
        src = tmp_path / "src.txt"
        dest = tmp_path / "dest.txt"
        src.write_text("new")
        dest.write_text("old")
        write_path(src, dest, Resolution.BACKUP)
        assert dest.read_text() == "new"
        assert (tmp_path / "dest.txt.bak").read_text() == "old"


class TestApplyBackup:
    def test_file(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("data")
        apply_backup(f)
        assert not f.exists()
        assert (tmp_path / "f.txt.bak").read_text() == "data"

    def test_dir(self, tmp_path):
        d = tmp_path / "d"
        d.mkdir()
        (d / "x").write_text("x")
        apply_backup(d)
        assert not d.exists()
        assert (tmp_path / "d.bak" / "x").read_text() == "x"

    def test_clears_stale_bak(self, tmp_path):
        f = tmp_path / "f.txt"
        bak = tmp_path / "f.txt.bak"
        f.write_text("new")
        bak.write_text("stale")
        apply_backup(f)
        assert bak.read_text() == "new"


class TestRunMutations:
    def test_abort_writes_nothing(self, monkeypatch):
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        monkeypatch.setattr(logger, "select", lambda _msg, _labels: "Abort")
        with pytest.raises(SystemExit):
            run_mutations([_AbortMutation()], overwrite=None, backup=False)

    def test_apply_order(self):
        order: list[str] = []
        run_mutations(
            [_OrderMutation("a", order), _OrderMutation("b", order)],
            overwrite=True,
            backup=False,
        )
        assert order == ["a", "b"]
