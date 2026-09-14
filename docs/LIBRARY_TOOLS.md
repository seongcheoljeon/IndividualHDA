# Library Tools

Open **Library Tools** in the panel menu. The existing asset list, thumbnails,
category navigation, history and themes remain in place. The manager is a modal
child of the panel, with six tabs. File and database work runs in an owned worker;
HOM calls stay on Houdini's GUI thread. Closing during work waits for completion.

## Health

**Scan library** checks SQLite integrity and foreign keys, incomplete asset
metadata, and referenced HDA, thumbnail and video files in current assets and
history. Missing source HIP files are listed separately because they may belong
to another workstation. Export the table as a UTF-8 text report. Scanning uses a
read-only database connection and does not attempt automatic repairs.

## Backups

**Refresh backups** lists full ZIP backups and database-only migration/path-repair
copies, with timestamps, size and reason. Enter a reason and choose **Create full
backup** to save a consistent SQLite snapshot with the library files.

**Validate selected backup** extracts into temporary storage, migrates and checks
the copied database, and verifies its referenced library files. Source HIP files
are not expected in the archive. Database-only and recovery-file copies are
clearly marked for manual recovery and cannot be used as full-library restores.

**Restore selected backup** requires confirmation. It validates the archive,
backs up the current library and stages the replacement. The panel closes to
activate it through the existing durable import journal. Reopen the panel after
restoration. Existing files remain in `.previous-*` recovery locations. A failed
validation does not replace the current library.

## Repair paths

Enter the old absolute root and choose the new directory after moving files.
Windows roots are matched using Windows path semantics, even when repairing on
another OS. Preview shows every affected table/row, old/new directory and whether
the destination file exists. Only checked rows are applied, and each destination
must still exist at execution time. This updates metadata; it does not move files.

A database backup precedes the transaction. Changed preview values are rejected;
trigger side effects on unrelated node-location records are restored. The panel
closes after success so cached paths cannot continue using the old location.
Reopen it afterward. Choose the new library location in Preferences first if the
entire database has moved as well.

## Versions

Start from the selected main-panel asset, enter an asset ID, or choose **Compare
selected asset versions** in Explorer. Load history snapshots and select left and
right versions. The report compares metadata, the available note as of that
snapshot, saved parameter-interface scripts, and expanded node/section files.
Text sections receive line diffs; binary/large sections receive size and SHA-256
comparisons. A text section's diff is capped at 2,000 lines and marks truncation.
Save the displayed comparison as a UTF-8 report.

The implementation uses SideFX [definitionsInFile / expandToDirectory](https://www.sidefx.com/docs/houdini/hom/hou/hda.html)
and saved `DialogScript` sections. Houdini 21 requires installed types for
`parmTemplateGroup()`, so comparison uses the saved interface and does not install
HDA definitions or create scene nodes. Expanded files are temporary. Black-box or
binary contents are reported as such, not presented as a semantic node graph.

**Import right version into current network** uses the existing iHDA import
adapter and a Houdini undo group. The Network Editor must match the asset's
category. Comparing does not modify the scene; importing is an explicit action.

## Explorer

Search Name, Tags or Type using a literal substring. Queries run on their own
read-only SQLite connection and return at most 200 rows per page. Typing waits
250 ms, cancels the previous query and ignores stale results. **Load next 200**
appends another page without rebuilding previous rows. **Cancel task** interrupts
SQL through a progress handler. Select a result in the main panel, or open its
versions. Existing main-panel filters still determine whether that result is
visible there.

Main-panel asset/history text filters are also debounced by 200 ms when their
source contains at least 1,000 rows. Smaller lists retain immediate filtering.
The original initial full snapshot and Qt proxy sorting are still synchronous;
Explorer is an additional bounded browsing path, not a conversion of every
existing view to server-side paging. See [query measurements](explorer-benchmark.json).

## Recovery files

Scan recognized `.ihda-deleted-<id>-*`, asset `.previous-<id>` and database
`.previous-<id>` entries. The table shows size and whether current library/source
references still point into them. Check entries and confirm cleanup. No entry is
selected automatically. Referenced files, changed previews, symlinks and pending
operation journals prevent deletion.

Selected contents are first written to a separate recovery ZIP with a manifest
of their original locations. Its CRCs and the source inventory are checked before
removal. If removal fails partway, the error identifies the safety archive. These
ZIPs are retained and listed in Backups for manual recovery; they are not complete
library restores. Compressed safety copies still occupy disk space. Unknown files,
staged imports and unrelated directories are not cleanup candidates.

## Limits and verification

Cancellation of archive validation is checked between extraction/validation
phases; a running ZIP extraction may finish its phase first. Mutating operations
finish before shutdown rather than being interrupted midway. Migration during
restore validation affects only the temporary copy. All development tests use
temporary libraries; no live user library has been restored, rebased or cleaned.

Functional tests cover missing references, path previews and rollback checks,
Windows path matching, full backup verification, staged restore, referenced-file
protection, recovery safety archives, search paging/cancellation, version text
diffs, debounce, dialog closure and superseded search results. Native Houdini 21
also checks comparison without changes to installed definitions or scene nodes,
and creation/shutdown of the six-tab manager.


Explorer query measurements (Linux/WSL, Python 3.12, median of three warm calls):

| Assets | Full snapshot | First 200 | Filtered 200 | Second 200 |
| --- | ---: | ---: | ---: | ---: |
| 10,000 | 208.85 ms | 3.54 ms | 4.00 ms | 4.86 ms |
| 50,000 | 1,712.58 ms | 22.79 ms | 15.34 ms | 28.11 ms |

Run `python benchmarks/benchmark_explorer.py` from the repository root to reproduce
the workload. These measurements exclude UI rendering and initial panel loading.


## Library Tools verification

The full regression suite passed **131 tests** (16.46 s). Ruff lint/format checks
and mypy passed; mypy now covers **41 configured files**. Whitespace checks passed.
Native Windows **Houdini 21.0.559 / Qt 6.5.3** passed HDA export/import, original-node
preservation, version comparison without changes to installed definitions or scene
nodes, Unicode SQLite paths, legacy migration, and six-tab manager/panel lifecycle.

The new tests exercise all six service paths, staged restoration, path backups and
stale previews, referenced recovery files, malformed backups, delayed and cancelled
searches, reopening the manager and closing during work. Full interactive acceptance
on Windows, macOS and Linux remains pending. No live library was modified.

