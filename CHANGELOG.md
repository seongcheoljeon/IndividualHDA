# Changelog

## 2.1.0 (unreleased) — shared-library foundations

Client-only groundwork for a multi-user library; behavior in local mode is
unchanged apart from the items below.

- **Storage boundary.** `LibraryRepository` protocol + SQLite adapter; panel
  registration, versioning, tags/notes, favorites, rename and deletion go
  through it. Prepares the HTTP/PostgreSQL server mode.
- **Identity.** User = `IHDA_USER` or OS login; existing local libraries keep
  their single user row.
- **Search.** Repository-side `LIKE`/`GLOB` search over name, tags, type,
  definition comment and note with `field:` prefixes and wildcards, run off the
  GUI thread; new `Note` and `All` fields. Tags are normalized on write.
- **Reload and change detection.** Toolbar Reload plus a revision poller that
  refreshes the panel when another process changes the library.
- **Optional media.** Missing `QtMultimedia`/`QtWebEngine` no longer prevent the
  panel from opening.
- **Panel state.** `LibraryContext` snapshot replaces Preference-dialog reads;
  category selection lives in `SelectionState`.

## 2.0.0 — Houdini 21+ (Qt 6 / PySide6 / Python 3.11)

Decisions that shaped this release. Verification details live in
[`docs/VALIDATION.md`](docs/VALIDATION.md); module rules in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

### Platform
- Target is the standard Houdini 21+ Qt 6 build with its bundled PySide6 and
  Python 3.11. Separate Qt 5 builds and Houdini 20.x are not supported; the
  Python Panel refuses to start below Houdini 21.
- Designer `.ui` files stay the source of truth; `*_ui.py` and `*_rc.py` are
  generated with `pyside6-uic` / `pyside6-rcc`. Vendored Python 2 backports
  (`pathlib2`, `scandir`, `qtpy`, `qdarkstyle`) were removed; the dark theme
  ships only as the compiled resource `libs/darkstyle_rc.py`.
- Installation is a Houdini package (`packages/IndividualHDA.json`) setting
  `IHDA_ROOT`; nothing is installed into Houdini's Python.

### Database
- Schema is versioned with `PRAGMA user_version` (currently 4). Every upgrade
  backs the file up next to itself as `ihda.db.pre-v<N>-<UTC>-<suffix>.bak`
  and runs DDL, indexes, triggers and the version bump in one transaction.
  Newer schemas are refused; foreign-key violations abort the upgrade.
- v1: indexes, trigger-maintained `asset_tags`, favorite/load-count checks,
  category cleanup scoped by user. v2: `operation_commits` for crash recovery;
  nested transactions use savepoints. v3: category-cleanup trigger gained the
  missing user predicate; tag index synced by triggers. v4: redundant UNIQUE
  constraints removed, numeric columns typed and constrained (fractional FPS
  preserved, invalid FPS rejected), legacy tables rebuilt in place.
- All SQL parameters are bound. `SQLite3DatabaseAPI` is a facade over
  `libs/database/`; mixins share one session and one thread.

### Concurrency and recovery
- Widgets, Qt models and HOM calls stay on the GUI thread. Archive/file work runs
  in an owned `BackgroundJob`; encoders and probes run as `ProcessJob`
  (`QProcess`, argv only, no shell). `TaskController` delivers each result once
  and can drain synchronously for `onDestroyInterface`.
- Rename, delete and import activation write a `MoveJournal` before touching
  files and record the operation id in the same SQLite transaction; startup
  recovery replays or reverses interrupted moves. Deletes keep hidden
  `.ihda-deleted-*` files, imports keep `.previous-*` copies; neither is purged
  automatically.
- Archive import extracts into a staging directory, rejects traversal/absolute/
  symlink/case-duplicate entries, migrates the staged database, then swaps on
  panel close. A full ZIP backup is taken first.

### Panel structure
- `main.IndividualHDA` is split into feature mixins under `widgets/panel/`.
  `PanelServices` is the composition root; the panel takes it as a constructor
  argument so adapters (`AssetNames`, `RenameRepository`, `OperationFactory`,
  database/archive/task factories) can be replaced without editing features.
- `AssetStore` owns shared rows and notifies Qt models through
  `RowNotifications`; `SelectionState` owns selections; `AssetData`,
  `HistoryData`, `SceneRecord` type the DB/UI payloads.
- Proxy models share null-safe predicates (`model/proxy_filters.py`), use Qt
  recursive filtering, and map source/proxy indexes explicitly.
- Library Tools manager: health check, backups, path repair, version
  comparison, paged explorer, recovery-file browser.
- AI extension point: `libs/ai_provider.py` (`AIProvider.complete`),
  backend/endpoint/model/API-key-env settings in Preferences, a dedicated task
  controller for AI calls. Default backend does nothing; no network code yet.
