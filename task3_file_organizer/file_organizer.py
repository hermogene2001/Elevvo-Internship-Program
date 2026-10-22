#!/usr/bin/env python3
"""Task 3 - Automated File Organizer.

Scans a target directory and automatically sorts files into subfolders based on
file extension (or grouped file category).

Safety rules that are enforced, not optional:
    * An existing file at the destination is NEVER overwritten. On a filename
      conflict the incoming file is renamed (numbered or timestamped suffix).
    * Every move is reported to the console (filename, source, destination).

Edge cases handled: duplicate filenames, missing permissions, empty folders,
subdirectories of the target, and the organizer's own script/log file.

Covered topics:
    File Handling | Exception Handling | Automation | Safe File Operations

Bonus:
    * Proper logging to a file (console output optional via --quiet).
    * A dry-run mode that previews changes without moving anything.
    * Reading ahead: schedule with Task Scheduler / cron (see README).
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

LOG = logging.getLogger("file_organizer")

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
CATEGORY_EXTENSIONS: dict[str, set[str]] = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".tiff", ".ico", ".heic"},
    "Documents": {".pdf", ".doc", ".docx", ".odt", ".rtf", ".txt", ".md", ".xls", ".xlsx", ".csv", ".ppt", ".pptx"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"},
    "Video": {".mp4", ".mkv", ".mov", ".avi", ".wmv", ".webm", ".flv"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"},
    "Code": {".py", ".js", ".ts", ".html", ".css", ".java", ".c", ".cpp", ".h", ".cs", ".go", ".rs", ".sh", ".ps1", ".json", ".xml", ".yml", ".yaml", ".sql", ".toml"},
    "Executables": {".exe", ".msi", ".bat", ".cmd", ".apk", ".dmg", ".deb"},
}
FALLBACK_CATEGORY = "Other"
NO_EXTENSION_FOLDER = "No_Extension"


# --------------------------------------------------------------------------- #
# Result model
# --------------------------------------------------------------------------- #
@dataclass
class MoveResult:
    """Outcome of a single attempted move."""

    source: Path
    destination: Path
    status: str  # "moved" | "renamed" | "skipped" | "error"
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status in {"moved", "renamed"}


# --------------------------------------------------------------------------- #
# Destination naming
# --------------------------------------------------------------------------- #
def category_for(suffix: str) -> str:
    """Map a lowercase file suffix (e.g. ``.pdf``) to a category folder."""
    for category, extensions in CATEGORY_EXTENSIONS.items():
        if suffix in extensions:
            return category
    return FALLBACK_CATEGORY


def destination_folder(path: Path, mode: str) -> str:
    """Return the subfolder name that ``path`` belongs in."""
    suffix = path.suffix.lower()

    if mode == "category":
        return category_for(suffix)

    # mode == "extension": folder named after the extension itself
    if not suffix:
        return NO_EXTENSION_FOLDER
    return suffix.lstrip(".")


def _split_name(path: Path) -> tuple[str, str]:
    """Split ``name.tar.gz`` into ``("name", ".tar.gz")``."""
    suffixes = path.suffixes
    suffix = "".join(suffixes)
    stem = path.name[: len(path.name) - len(suffix)] if suffix else path.name
    return stem or path.name, suffix


def _with_inserted_text(path: Path, text: str) -> Path:
    """Insert ``text`` before the multi-part suffix (``a.tar.gz`` -> ``a{text}.tar.gz``)."""
    stem, suffix = _split_name(path)
    return path.with_name(f"{stem}{text}{suffix}")


def resolve_destination(dest: Path, reserved: set[Path], style: str) -> Path:
    """Return a safe destination that never overwrites an existing file.

    ``reserved`` holds destinations already claimed during this run so two
    sources never collide with each other either.
    """

    def available(candidate: Path) -> bool:
        return not candidate.exists() and candidate not in reserved

    if available(dest):
        return dest

    if style == "timestamp":
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        candidate = _with_inserted_text(dest, f"_{stamp}")
        counter = 1
        while not available(candidate):
            candidate = _with_inserted_text(dest, f"_{stamp}_{counter}")
            counter += 1
        return candidate

    counter = 1
    while True:
        candidate = _with_inserted_text(dest, f"_{counter}")
        if available(candidate):
            return candidate
        counter += 1


# --------------------------------------------------------------------------- #
# Scanning
# --------------------------------------------------------------------------- #
def iter_files(target: Path, recursive: bool, exclude: Iterable[Path]) -> list[Path]:
    """Return the files directly inside ``target`` (or below it) to organise."""
    excluded = {path.resolve() for path in exclude}
    pattern = "*" if not recursive else "**/*"
    files: list[Path] = []

    for path in target.glob(pattern):
        if not path.is_file():
            continue
        if path.resolve() in excluded:
            continue
        files.append(path)

    return sorted(files, key=lambda p: p.name.lower())


# --------------------------------------------------------------------------- #
# Core
# --------------------------------------------------------------------------- #
def build_plan(
    files: Sequence[Path],
    mode: str,
    conflict: str,
) -> list[tuple[Path, Path]]:
    """Compute ``(source, destination)`` pairs without touching the filesystem."""
    reserved: set[Path] = set()
    plan: list[tuple[Path, Path]] = []

    for source in files:
        dest_dir = source.parent / destination_folder(source, mode)
        dest = resolve_destination(dest_dir / source.name, reserved, conflict)
        reserved.add(dest)
        plan.append((source, dest))

    return plan


def execute_plan(plan: Sequence[tuple[Path, Path]], dry_run: bool, target: Path) -> list[MoveResult]:
    """Perform (or preview) each planned move, logging every operation."""
    results: list[MoveResult] = []

    for source, destination in plan:
        source_rel = _relative(source, target)
        dest_rel = _relative(destination, target)
        renamed = destination.name != source.name
        status = "renamed" if renamed else "moved"

        if dry_run:
            LOG.info("[dry-run] %-24s %s  ->  %s", source.name, source_rel, dest_rel)
            results.append(MoveResult(source, destination, "skipped", "dry run"))
            continue

        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
        except PermissionError as exc:
            LOG.error("[error  ] %-24s %s  (permission denied: %s)", source.name, source_rel, exc)
            results.append(MoveResult(source, destination, "error", f"permission denied: {exc}"))
            continue
        except (OSError, shutil.Error) as exc:
            LOG.error("[error  ] %-24s %s  (failed: %s)", source.name, source_rel, exc)
            results.append(MoveResult(source, destination, "error", str(exc)))
            continue

        note = " (conflict - renamed to avoid overwrite)" if renamed else ""
        LOG.info("[%-7s] %-24s %s  ->  %s%s", status, source.name, source_rel, dest_rel, note)
        results.append(MoveResult(source, destination, status, "renamed on conflict" if renamed else ""))

    return results


def organize(
    target: Path,
    *,
    mode: str = "extension",
    conflict: str = "number",
    dry_run: bool = False,
    recursive: bool = False,
    exclude: Iterable[Path] = (),
) -> list[MoveResult]:
    """Organise ``target`` and return the results of every attempted move."""
    files = iter_files(target, recursive, exclude)

    if not files:
        LOG.info("Nothing to organise in %s - the folder is empty or contains only subfolders.", target)
        return []

    plan = build_plan(files, mode, conflict)
    results = execute_plan(plan, dry_run, target)

    _log_summary(results, target, dry_run)
    return results


def _log_summary(results: Sequence[MoveResult], target: Path, dry_run: bool) -> None:
    moved = sum(1 for r in results if r.status == "moved")
    renamed = sum(1 for r in results if r.status == "renamed")
    skipped = sum(1 for r in results if r.status == "skipped")
    errored = sum(1 for r in results if r.status == "error")

    LOG.info("-" * 64)
    if dry_run:
        LOG.info("DRY RUN complete for %s - no files were moved.", target)
    else:
        LOG.info("Done organising %s", target)
    LOG.info(
        "Moved: %d | Renamed (conflicts): %d | Skipped: %d | Errors: %d | Total: %d",
        moved, renamed, skipped, errored, len(results),
    )
    LOG.info("-" * 64)


def _relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


# --------------------------------------------------------------------------- #
# Sample data (so the organizer can be tried instantly)
# --------------------------------------------------------------------------- #
SAMPLE_FILES: dict[str, str] = {
    "report.pdf": "quarterly report",
    "report.docx": "editable report",
    "notes.txt": "meeting notes",
    "script.py": "print('hello')",
    "photo.jpg": "jpeg image",
    "photo.png": "png image",
    "song.mp3": "audio bytes",
    "clip.mp4": "video bytes",
    "backup.zip": "archive bytes",
    "data.csv": "a,b,c\n1,2,3",
    "README.md": "# sample",
    "budget.xlsx": "spreadsheet",
    "LICENSE": "no extension here",
}
# Pre-existing files that force the "never overwrite" path to trigger.
# These live in the folders the default (extension) mode targets.
SAMPLE_CONFLICTS: dict[Path, str] = {
    Path("pdf") / "report.pdf": "PRE-EXISTING file - must not be overwritten",
    Path("jpg") / "photo.jpg": "PRE-EXISTING file - must not be overwritten",
}


def create_sample_files(target: Path) -> None:
    """Populate ``target`` with a small pile of clutter for a live demo."""
    target.mkdir(parents=True, exist_ok=True)

    for name, content in SAMPLE_FILES.items():
        (target / name).write_text(content, encoding="utf-8")

    for relative, content in SAMPLE_CONFLICTS.items():
        existing = target / relative
        existing.parent.mkdir(parents=True, exist_ok=True)
        existing.write_text(content, encoding="utf-8")

    LOG.info("Created %d sample files in %s (plus %d pre-existing conflicts).",
             len(SAMPLE_FILES), target, len(SAMPLE_CONFLICTS))


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def setup_logging(log_path: Path, quiet: bool) -> None:
    """Log to a file always; mirror to the console unless ``quiet``."""
    LOG.setLevel(logging.DEBUG)
    LOG.handlers.clear()
    LOG.propagate = False

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s  %(levelname)-8s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    LOG.addHandler(file_handler)

    if not quiet:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(logging.Formatter("%(message)s"))
        LOG.addHandler(stream_handler)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sort the files in a directory into subfolders by extension.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python file_organizer.py C:\\Downloads\\clutter\n"
            "  python file_organizer.py C:\\Downloads\\clutter --dry-run\n"
            "  python file_organizer.py C:\\Downloads\\clutter --mode category --conflict timestamp\n"
            "  python file_organizer.py sample_clutter --create-sample\n"
        ),
    )
    parser.add_argument("target", help="Directory whose files should be organised.")
    parser.add_argument(
        "--mode",
        choices=("extension", "category"),
        default="extension",
        help="Folder naming: raw file extension (default) or grouped category.",
    )
    parser.add_argument(
        "--conflict",
        choices=("number", "timestamp"),
        default="number",
        help="How to rename an incoming file that clashes with an existing one (default: number).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview moves without changing anything.")
    parser.add_argument("--recursive", action="store_true", help="Also organise files in subfolders.")
    parser.add_argument("--quiet", action="store_true", help="Only write to the log file, not the console.")
    parser.add_argument(
        "--log-file",
        default="file_organizer.log",
        help="Where to write the log (default: file_organizer.log).",
    )
    parser.add_argument(
        "--create-sample",
        action="store_true",
        help="Fill the target with sample clutter (and demo conflicts), then exit.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    target = Path(args.target).expanduser()
    log_path = Path(args.log_file).expanduser().resolve()

    setup_logging(log_path, quiet=args.quiet)

    if args.create_sample:
        create_sample_files(target)
        return 0

    if not target.exists():
        LOG.error("Target directory does not exist: %s", target)
        return 2
    if not target.is_dir():
        LOG.error("Target is not a directory: %s", target)
        return 2

    # Never touch the running script or our own log file.
    exclude = {Path(__file__).resolve()}
    if log_path.parent == target.resolve():
        exclude.add(log_path)

    LOG.info("Organizing: %s", target)
    LOG.info("Mode: %s | Conflict policy: %s%s%s",
             args.mode, args.conflict,
             " | DRY RUN" if args.dry_run else "",
             " | recursive" if args.recursive else "")

    try:
        results = organize(
            target,
            mode=args.mode,
            conflict=args.conflict,
            dry_run=args.dry_run,
            recursive=args.recursive,
            exclude=exclude,
        )
    except KeyboardInterrupt:
        LOG.warning("Interrupted by user.")
        return 130

    errors = sum(1 for result in results if result.status == "error")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
