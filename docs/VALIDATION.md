# Validation and recovery

## Local checks

```sh
python -m ruff check .
python -m ruff format --check .
python -m mypy
python -m pytest -q
```

- Linux Python 3.11 / PySide6 6.x (offscreen): the regression suite covers schema
  upgrade, backup contents, migration rejection/rollback, quoted Unicode values,
  normalized tags, transaction rollback, archive traversal, relocation, WAL
  snapshots, import rollback, Qt model notifications, drag payloads, search,
  process failure, cancellation, playlist behavior, settings atomicity, populated
  panel startup, panel worker success/failure/deferred close with GUI-thread
  delivery, host-destruction cleanup, Library Tools service paths, AI provider
  settings roundtrip, and complete signature annotation coverage with Python 3.11
  syntax.
- Windows Houdini 21.0.559 / Python 3.11.7 / Qt 6.5.3: `hython tests/houdini_smoke.py`
  creates a temporary SOP asset, exports and reimports it, verifies original node
  identity and absence of leaked wrapper output nodes, compares versions without
  changing installed definitions, exercises SQLite/Unicode and legacy migration,
  and constructs/closes the panel and six-tab manager offscreen, including
  dark/default theme switching.
- CI also runs the suite on Python 3.12. Whether Houdini 21 ships a Python 3.12
  build has not been confirmed against SideFX's platform notes; 3.11 is the
  verified host interpreter.
- No existing user library or HIP was used for tests.

The local Qt tests run with a temporary configuration (`IHDA_CONFIG_DIR`). A
restrictive sandbox can block Qt's native audio initialization; run the UI suite
outside it in offscreen mode.

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

The current schema version is `SCHEMA_VERSION = 4` in `libs/database_migrations.py`.
The original tables, primary keys, asset IDs, version strings and local timestamp
values remain across upgrades. Version steps: v1 indexes, trigger-maintained
`asset_tags`, favorite/load-count validation and user-scoped category cleanup;
v2 `operation_commits` for crash recovery and savepoint-based nested transactions;
v3 user predicate on the category-cleanup trigger and synced tag index; v4 removal
of redundant UNIQUE constraints, typed/constrained numeric columns (fractional FPS
preserved, zero FPS rejected) and in-place legacy table rebuilds.

An existing unversioned database is backed up next to itself as
`ihda.db.pre-v<N>-<UTC timestamp>-<unique suffix>.bak` before migration. DDL, indexes,
triggers and `user_version` advance in one transaction. Foreign-key violations
abort the upgrade; newer unsupported schema versions are refused. Migration
backups are not silently overwritten or deleted.

The default journal mode is retained for compatibility. Connections enable foreign
keys and a five-second busy timeout. Each background operation opens and closes its
own connection. Exports use SQLite's backup API so committed WAL data is included.

To restore a pre-upgrade DB, close every iHDA panel/process using it, preserve the
current database and its sidecars, and copy the desired `.bak` to `ihda.db`.
Use the old app for a true downgrade; this app upgrades older versions on reopening.

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


## Library Tools

Service paths, staged restoration, path backups, recovery files, malformed
backups and search paging/cancellation are covered by the regression suite; see
[LIBRARY_TOOLS.md](LIBRARY_TOOLS.md) for behavior, limits and how to reproduce the
explorer measurements. Full interactive acceptance on Windows, macOS and Linux
remains pending.
