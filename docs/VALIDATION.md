# Validation and recovery

## Local checks

See [audit findings and regression coverage](AUDIT.md) for the model/proxy/theme review.

Final regression run: **59 passed**. `ruff check .`, `ruff format --check .`, and `git diff --check` passed.
`python -m mypy` passed for the 17 configured core modules.

- Linux Python 3.12.3 / PySide6 6.11.2: regression suite covers schema upgrade,
  backup contents, migration rejection/rollback, quoted Unicode values, normalized
  tags, transaction rollback, archive traversal, relocation, WAL snapshots,
  import rollback, Qt model notifications, drag payloads, search, process failure,
  cancellation, playlist behavior, settings atomicity and populated panel startup.
  Structural-refactor coverage additionally verifies cross-module transaction
  rollback and panel worker success/failure/deferred close with GUI-thread delivery,
  host-destruction cleanup, deferred callback suppression and complete maintained
  signature annotation coverage with Python 3.11 syntax.
- Windows Houdini 21.0.559 / Python 3.11.7 / Qt 6.5.3: `tests/houdini_smoke.py`
  creates a temporary SOP asset, exports and reimports it, verifies original node
  identity and absence of leaked wrapper output nodes, exercises SQLite/Unicode,
  and constructs/closes the panel offscreen, including dark/default theme switching.
- Windows Houdini 22.0.368: verification blocked by a native crash in
  `PYsetArgvForPythonInitialization`. The same crash occurs with only
  `hython -c 'print("HOUDINI_BASELINE_OK")'`, before loading this project.
  No Houdini 22 compatibility claim is made from this environment.
- `.ui` Designer files are unchanged. Generated Qt/resource code is updated.
- No existing user library or HIP was used for tests.

The local Qt tests run with a temporary configuration. A restrictive sandbox can
block Qt's native audio initialization; the full UI suite was run outside that
sandbox in offscreen mode. Pure database/archive tests run inside it.

## Interactive acceptance checks still required

On each of Windows, macOS and Linux, using a disposable library and HIP:

1. Start the Python panel, choose a data folder, restart and check settings.
2. Register SOP, OBJ, VOP and subnet nodes via middle-button drag/drop. Compare
   original nodes, wires, names, flags and embedded definitions before/after.
3. Update a version; inspect history; rename, favorite, tag, edit notes, search
   names/tags/types; switch list/table/history views and remove selected rows.
4. Import old and new versions, including connected and nested nodes.
5. Capture a thumbnail and flipbook; interrupt/fail capture and verify the original
   timeline, playback range and FPS are restored.
6. Encode with FFmpeg paths containing spaces/non-ASCII characters; verify odd-sized
   frames and fractional FPS, playback, volume, seeking and all five playlist modes.
7. Import/export between OSes. Asset paths relocate; external HIP paths remain the
   original paths and require the artist's storage/mount mapping.
8. Close during encoding, metadata probes and export. Verify no orphan processes,
   thread destruction errors or partial replacement of previous videos.

Native desktop behavior and macOS execution are not established by the local
headless tests. The OS CI matrix is configured but has not been run from this workspace.

## SQLite migration and backups

Schema version is `PRAGMA user_version = 1`. The original tables, primary keys,
asset IDs, version strings and local timestamp values remain. Changes add indexes,
normalized `asset_tags` maintained by triggers, validation of new favorite/load-count
writes, and category cleanup scoped by both category and user.

An existing unversioned database is backed up next to itself as
`ihda.db.pre-v1-<UTC timestamp>-<unique suffix>.bak` before migration. DDL, indexes,
triggers and `user_version` advance in one transaction. Foreign-key violations
abort the upgrade; newer unsupported schema versions are refused. Migration
backups are not silently overwritten or deleted.

The default journal mode is retained for compatibility. Connections enable foreign
keys and a five-second busy timeout. Each background operation opens and closes its
own connection. Exports use SQLite's backup API so committed WAL data is included.

To restore a pre-upgrade DB, close every iHDA panel/process using it, preserve the
current database and its sidecars, and copy the desired `.bak` to `ihda.db`.
Use the old app for a true downgrade; this app upgrades version 0 on reopening.

## Archive imports

Extraction occurs in a unique staging directory on the destination filesystem.
Absolute/traversal/Windows drive paths, symlinks and duplicate case-folded names
are rejected. A manifest records the original asset root; legacy archives derive
it from their stored asset paths. The staged database is migrated and checked
before the active library is touched.

Import first creates a full ZIP backup in the data folder's `backup` directory.
On panel close, file renames activate the staged database/assets. Exceptions roll
back those renames. Old assets and DB remain as `.previous-<unique suffix>` recovery
copies. These are retained intentionally and may be removed after verifying the
import. A sudden OS/process failure between filesystem renames is not a cross-file
atomic transaction; the retained ZIP and `.previous-*` files provide recovery.

For recovery, close the app, preserve all current/staged files, then restore a
matching database and asset directory from the same backup. Never mix a DB from
one backup with assets from another. Reopen and verify history and file locations.

## Scope

Houdini 21+ standard Qt 6 builds are the target; separate Qt 5 builds are excluded.
This remains a single-user library. Viewport/HOM operations deliberately execute
on the main thread. External encoders/probes use QProcess; file archives use an
owned worker and finish before panel/application shutdown. This is not a migration
to an asset server or a redesign of the UI.


## Follow-up items 2–5

See [REFACTOR_2_5.md](REFACTOR_2_5.md) for explicit state owners, typed payloads, schema v2 crash recovery, asynchronous bounded thumbnails, measured performance and remaining limitations.

Latest items 2–5 regression result: **72 passed** (7.10 s), Ruff lint/format passed, mypy passed for **26** files, whitespace check passed. Native Houdini 21.0.559 / Qt 6.5.3 smoke passed during this change. See the follow-up document for scope and limitations.


Latest SOLID verification: **83 tests passed** (7.78 s), Ruff lint/format passed,
mypy passed for **33 configured source files**, and `git diff --check` passed.
Native Houdini **21.0.559 / Qt 6.5.3** smoke checks passed after the dependency
changes. Interactive three-platform acceptance remains pending.


## Integrity review follow-up

The latest full regression run passed **93 tests** (7.98 s). Ruff lint and format
checks passed across 121 Python files; mypy passed for its 34 configured files;
`git diff --check` passed. Native Windows Houdini 21.0.559 / Qt 6.5.3 passed HDA
export/import, original-node preservation, Unicode SQLite paths, and offscreen
panel construction/shutdown after these fixes. See [INTEGRITY_REVIEW.md](INTEGRITY_REVIEW.md)
for the corrected paths and remaining verification limits.


## Schema v3 follow-up

The subsequent [schema review](SCHEMA_REVIEW.md) passed **96 tests** (8.46 s),
including v2-to-v3 migration, tag synchronization and index query plans. Native
Houdini 21.0.559 smoke checks passed after the schema change.


## Schema v4 structural upgrade

Current regression result: **116 tests passed** (10.69 s), Ruff lint/format and
mypy passed (35 configured files), and whitespace checks passed. The native
Houdini 21.0.559 smoke now also executes legacy table reconstruction and checks
fractional FPS preservation and invalid numeric write rejection. See
[SCHEMA_REVIEW.md](SCHEMA_REVIEW.md) for backup, rollback and compatibility details.


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
See [LIBRARY_TOOLS.md](LIBRARY_TOOLS.md) and [Explorer measurements](explorer-benchmark.json).
