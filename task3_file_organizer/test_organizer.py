#!/usr/bin/env python3
"""Tests for the file organizer - focused on the "never overwrite" guarantee.

Run with either::

    python -m unittest test_organizer -v
    pytest test_organizer.py -v
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from file_organizer import (
    build_plan,
    category_for,
    destination_folder,
    organize,
    resolve_destination,
)


class TestNaming(unittest.TestCase):
    def test_category_mapping(self) -> None:
        self.assertEqual(category_for(".pdf"), "Documents")
        self.assertEqual(category_for(".jpg"), "Images")
        self.assertEqual(category_for(".xyz"), "Other")

    def test_destination_folder_by_extension(self) -> None:
        self.assertEqual(destination_folder(Path("a/b/report.PDF"), "extension"), "pdf")
        self.assertEqual(destination_folder(Path("a/b/LICENSE"), "extension"), "No_Extension")

    def test_destination_folder_by_category(self) -> None:
        self.assertEqual(destination_folder(Path("report.pdf"), "category"), "Documents")
        self.assertEqual(destination_folder(Path("song.mp3"), "category"), "Audio")


class TestConflictResolution(unittest.TestCase):
    def test_free_destination_used_as_is(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "folder" / "file.txt"
            self.assertEqual(resolve_destination(dest, set(), "number"), dest)

    def test_existing_file_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "file.txt"
            dest.write_text("ORIGINAL", encoding="utf-8")

            resolved = resolve_destination(dest, set(), "number")

            self.assertNotEqual(resolved, dest)
            self.assertEqual(resolved.name, "file_1.txt")
            self.assertEqual(dest.read_text(encoding="utf-8"), "ORIGINAL")

    def test_repeated_conflicts_increment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "file.txt"
            dest.write_text("x", encoding="utf-8")
            (Path(tmp) / "file_1.txt").write_text("x", encoding="utf-8")
            (Path(tmp) / "file_2.txt").write_text("x", encoding="utf-8")

            self.assertEqual(resolve_destination(dest, set(), "number").name, "file_3.txt")

    def test_multipart_suffix_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "archive.tar.gz"
            dest.write_text("x", encoding="utf-8")
            self.assertEqual(resolve_destination(dest, set(), "number").name, "archive_1.tar.gz")

    def test_reserved_names_are_avoided(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "file.txt"
            reserved = {dest}
            self.assertEqual(resolve_destination(dest, reserved, "number").name, "file_1.txt")

    def test_timestamp_style(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "file.txt"
            dest.write_text("x", encoding="utf-8")
            resolved = resolve_destination(dest, set(), "timestamp")
            self.assertTrue(resolved.name.startswith("file_"))
            self.assertTrue(resolved.name.endswith(".txt"))


class TestOrganizeEndToEnd(unittest.TestCase):
    def test_moves_files_into_extension_folders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.pdf").write_text("a", encoding="utf-8")
            (root / "b.jpg").write_text("b", encoding="utf-8")

            organize(root, mode="extension")

            self.assertTrue((root / "pdf" / "a.pdf").exists())
            self.assertTrue((root / "jpg" / "b.jpg").exists())
            self.assertFalse((root / "a.pdf").exists())

    def test_existing_destination_file_survives(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "report.pdf").write_text("INCOMING", encoding="utf-8")
            (root / "pdf").mkdir()
            (root / "pdf" / "report.pdf").write_text("ORIGINAL", encoding="utf-8")

            results = organize(root, mode="extension")

            self.assertEqual((root / "pdf" / "report.pdf").read_text(encoding="utf-8"), "ORIGINAL")
            self.assertEqual((root / "pdf" / "report_1.pdf").read_text(encoding="utf-8"), "INCOMING")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].status, "renamed")

    def test_dry_run_moves_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.pdf").write_text("a", encoding="utf-8")

            organize(root, mode="extension", dry_run=True)

            self.assertTrue((root / "a.pdf").exists())
            self.assertFalse((root / "pdf").exists())

    def test_empty_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(organize(Path(tmp)), [])

    def test_two_sources_never_collide(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Same filename in two different subdirectories, recursive run.
            (root / "one").mkdir()
            (root / "two").mkdir()
            (root / "one" / "same.pdf").write_text("1", encoding="utf-8")
            (root / "two" / "same.pdf").write_text("2", encoding="utf-8")

            plan = build_plan(
                [root / "one" / "same.pdf", root / "two" / "same.pdf"],
                mode="extension",
                conflict="number",
            )
            destinations = [dest for _, dest in plan]
            self.assertEqual(len(destinations), len(set(destinations)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
