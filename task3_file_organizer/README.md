# Task 3 — Automated File Organizer

**Level 2 · Module 4 · Tools: `os`, `shutil`, `pathlib`, `logging`**

Scans a target directory and automatically sorts files into subfolders based on
their file extension.

**Covered topics:** File Handling · Exception Handling · Automation · Safe File Operations

**Bonus implemented:** proper logging to a file (console optional with
`--quiet`) and a `--dry-run` mode that previews changes without moving anything.

## The non-negotiable rule

> **An existing file at the destination is never overwritten.**

If the incoming file would clash with something already there, the incoming file
is renamed instead — either with a numbered suffix (`report_1.pdf`,
`report_2.pdf`, …) or a timestamp (`report_20261019-143012.pdf`). The pre-existing
file is left completely untouched. `test_organizer.py` proves this directly.

## Files

| File | Purpose |
|------|---------|
| `file_organizer.py` | The organizer (scan → plan → move → log → summarise). |
| `test_organizer.py` | Unit tests, focused on the never-overwrite guarantee. |

## Run

```bash
cd task3_file_organizer

# 1. Create a demo folder full of clutter (including two deliberate conflicts)
python file_organizer.py sample_clutter --create-sample

# 2. Preview what would happen (nothing is moved)
python file_organizer.py sample_clutter --dry-run

# 3. Do it for real
python file_organizer.py sample_clutter
```

## Options

| Flag | Meaning |
|------|---------|
| `target` | Directory to organise (required). |
| `--mode {extension,category}` | Folder naming: raw extension (default) or grouped category (`Images`, `Documents`, …). |
| `--conflict {number,timestamp}` | How a clashing incoming file is renamed (default `number`). |
| `--dry-run` | Preview only; no files are moved. |
| `--recursive` | Also organise files inside subfolders. |
| `--quiet` | Log to file only; no console output. |
| `--log-file PATH` | Where to write the log (default `file_organizer.log`). |
| `--create-sample` | Fill the target with sample clutter and exit. |

## How it works

1. **Scan** — `iter_files()` lists the files to organise (non-recursive by
   default) and excludes the running script and the organizer's own log file.
2. **Plan** — `build_plan()` computes every `source → destination` pair *before*
   touching anything. A `reserved` set prevents two sources from claiming the
   same name.
3. **Move** — `execute_plan()` creates the subfolder if needed and calls
   `shutil.move()`. `PermissionError` and other `OSError`/`shutil.Error`
   conditions are caught per-file so one failure doesn't abort the run.
4. **Report** — every operation is logged as
   `[moved]/[renamed]  filename  source  ->  destination`, followed by a summary
   of moved / renamed / skipped / errored counts.

## Edge cases handled

- **Duplicate filenames** → renamed, never overwritten.
- **Missing permissions** → logged as an error, run continues, exit code `1`.
- **Empty folders** → reports "Nothing to organise".
- **Extensionless files** → go to `No_Extension/`.
- **Multi-part suffixes** → `archive.tar.gz` → `archive_1.tar.gz`.
- **Self-preservation** → the running script and the log file are never moved.

## Sample output

```
[renamed] report.pdf               report.pdf  ->  pdf\report_1.pdf (conflict - renamed to avoid overwrite)
[moved  ] report.docx              report.docx  ->  docx\report.docx
[renamed] photo.jpg                photo.jpg  ->  jpg\photo_1.jpg (conflict - renamed to avoid overwrite)
----------------------------------------------------------------
Done organising sample_clutter
Moved: 11 | Renamed (conflicts): 2 | Skipped: 0 | Errors: 0 | Total: 13
----------------------------------------------------------------
```

## Reading ahead — scheduling

**Windows Task Scheduler**
```powershell
$action  = New-ScheduledTaskAction -Execute "python" `
           -Argument "D:\Elevvo Internship Program\task3_file_organizer\file_organizer.py C:\Downloads --quiet"
$trigger  = New-ScheduledTaskTrigger -Daily -At 6pm
Register-ScheduledTask -TaskName "OrganizeDownloads" -Action $action -Trigger $trigger
```

**Linux/macOS cron** (every day at 18:00)
```cron
0 18 * * * /usr/bin/python3 /path/to/file_organizer.py ~/Downloads --quiet
```
