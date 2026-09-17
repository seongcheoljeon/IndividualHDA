# Changelog

## 2.1.0 (unreleased) — shared-library foundations

Personal and Team library foundations, with additive tracking and recovery.

- **Runtime preferences and policy ownership.** Add restart-applied search, refresh,
  team request/page and node-batch preferences with validated legacy-compatible
  loading. Share version, AI defaults, query limits and model column identities;
  inject callback/media/thumbnail policies without changing data formats.
- **Committed scene-record cleanup.** Collect stable IDs before deleting, retain
  failed/inaccessible records, update the view only after database success and
  reload after display failures. HIP/HDA source files are never removed.

- **Version tracking (Personal v6 / Team v3).** Add normalized dependencies,
  append-only manual compatibility reports/corrections, and account-scoped scene
  observations with durable offline delivery. Warn about dependents before Trash
  or purge; preserve missing references and copied report provenance. Retain API v2
  with a `version_tracking` capability and include tracking in backups.
- **Durable registration recovery.** Persist local capture/publication phases and
  a receipt in the metadata transaction; retain Team captures/uploads and exact
  commands for retry. Add Pending registrations to Library Tools with safe discard.
  Existing history activity no longer moves the current-version pointer.
- **Named data and policies.** Read multi-column SQLite results by explicit names,
  normalize payloads at the storage boundary, and isolate legacy row ordering in
  compatibility converters. Registration/history/scene UI paths use named fields
  without modifying caller lists. Select pages by identity and inject validated
  search, panel, SQLite and archive limits while retaining existing defaults.
- **Main-window composition.** Separate construction and retryable shutdown from
  Qt events. Compose bootstrap, AI, archives and library sync instead of inheriting
  their Mixins. Clean acquired resources on startup failure and keep failed closes
  in a retryable closing state without restarting stopped services.
- **Rename and Trash refactoring.** Share name validation and retain journaled
  rollback. Update asset/history views only after commit, preserve failed items in
  mixed batches, and retain note history/files in historical-version Trash menus.
  Report committed display failures separately and always close rename overlays.
- **Registration capture.** Share staged HDA/thumbnail capture and exclusive file
  publication between local new registration and version addition. Restore node
  flags/overlays after failures, preserve uncertain DB commits, and distinguish
  successful saves from subsequent display-update failures.
- **Panel refactoring.** Centralize selection updates and restore all derived fields
  and Qt indexes by identity. Extract reload lifecycle/stale-result handling into a
  presenter and route metadata/refresh/history through Personal/Team session ports.
  Keep history filters and ALL on reload, reject stale Team history responses,
  retry failed/busy history requests, and consolidate shared UI defaults.
- **Core refactoring.** Introduce immutable file-content values and shared hashing;
  separate copy orchestration, destination and journal adapters with injectable ports.
  Consolidate protocol limits/API prefixes and validate HTTP/DB resource policies.
  Existing command, journal and backup formats remain compatible.
- **Server backup and recovery.** Add consistent PostgreSQL/blob bundles, offline
  integrity checks and verified restore into a separate empty database. Administrator
  CLI commands and an optional tools container keep maintenance out of the main UI.
  Server storage locking no longer requires Qt.
- **Personal → Team copy.** Copy an asset with selected versions and previews from
  its existing menu. Preview conflicts/size, retain source provenance, and resume
  interrupted uploads or lost registration responses without duplicate assets.
  Personal originals and preferences remain local; registration is atomic.
- **Feature presenters.** Extract metadata drafts/saves, lifecycle commands,
  media metadata, history date filtering, detail formatting and dialog policies
  into typed presenters. Save notes/tags off the GUI thread; retain drafts after
  failures and selection changes, and reject stale library reload results.
- **Validated dialog actions.** Main actions run only after dialog validation.
  Detail display keeps source records unchanged and web zoom applies host scaling
  once. Empty tag lists can be saved on assets without a previous tag row.
- **Python-only UI.** All seven Designer layouts and their generated Python
  modules are replaced by maintained, typed `layout.py` modules. Layout sections
  and widget names describe their purpose; see `docs/UI_EDITING.md` for editing.
  Search and asset browsing use a Presenter and injectable search gateway while
  preserving local SQLite behavior and settings. AI model download/delete refreshes
  now wait for worker idle, avoiding intermittent premature-refresh failures.
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
- **Local AI.** Ollama backend; Tools > Local AI Models… detects the server,
  recommends a vision-capable model for the GPU, downloads it with progress and
  applies it; an AI button suggests a note and tags for the selected asset.
  Chat requests stream and disable model thinking, so a slow first load no
  longer trips the 60 s timeout; Test connection reports load and total time.
  An installed model shows a check mark, its button reads Update (Ollama only
  fetches changed layers) and Enter applies it instead of re-pulling.
  A Remove button deletes an installed model from Ollama after confirmation.
  qwen3-vl requests carry an empty `<think>` prefill: Ollama 0.34's
  `qwen3-vl-thinking` parser ignores `think: false`, so the model spent its
  whole answer budget thinking and the suggestion failed with "no JSON object";
  the family is read from `/api/show` once per request. An answer made only of
  thinking is reported as such, and a parse failure quotes the answer's start.

### Hardening

- **Startup and shutdown.** A failing panel constructor shows a fallback widget
  with an "Open log folder" button instead of a traceback; several panel tabs
  no longer share one global instance; unreadable or locked databases report
  `LibraryUnavailable`; settings load key by key and a corrupt file is set
  aside as `.corrupt`; `closeEvent` refuses first and only then tears down
  dialogs, workers, pollers and debounce timers.
- **Data safety.** SQLite runs in WAL mode (readers no longer block writers);
  `-wal`/`-shm` sidecars move with the database on import; a failed
  registration removes the HDA and thumbnail it wrote; a daily automatic
  database backup keeps the last seven copies; adapter writes raise
  `LibraryError` instead of returning `None`.
- **Observability.** Rotating file log in `<config>/logs/ihda.log`, Help > Open
  log folder, and previously swallowed exceptions are logged.
- **Quality gates.** Ruff `F,E,W,I,B,UP,SIM,C4,ANN` with all automatic fixes
  applied (see `.git-blame-ignore-revs`), mypy over the whole tree with scoped
  Qt enums, coverage floor in CI, pinned dev tools, pre-commit, `.editorconfig`,
  `.gitattributes`, a generated-UI drift test and a version consistency test.
- **Structure.** `public.py` split into `libs.keys`, `libs.paths`,
  `libs.platform_info` and `libs.host` (re-exports kept); all HOM access goes
  through `HoudiniAPI`; one tree `Node` and a shared model style mixin; the
  panel reaches the SQLite facade at three maintenance sites only, everything
  else goes through `LibraryRepository`; `tests/test_architecture.py` pins the
  layer rules and ratchets.

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

## Personal / Team workspace

- Add a code-maintained shared workspace using an injected presenter and personal/HTTP adapters.
- Add atomic revision checks and request receipts, persistent retries and SHA-256 file storage/cache.
- Add a separate FastAPI/PostgreSQL service, expiring/revocable tokens, projects and member roles.
- Preserve the existing personal library and observe legacy writes with revision triggers.
- Add Compose/server packaging, shared adapter/HTTP/Qt regressions and operating documentation.

## Main-panel team integration

- Replace the separate Personal / Team workspace with a library selector in the existing browser.
- Reuse the existing asset views, category/search controls and note/tag editors for remote data.
- Move server credentials and memberships into focused settings dialogs; show conflict/retry controls only when needed.
- Preserve personal data and drafts across successful/failed source changes; isolate local writes in team mode.
- Keep remote file transfers asynchronous, route asset menus and drag/drop through the team presenter, and remove obsolete workspace UI files.

## Library metadata and lifecycle v2

- Add stable library/asset/version identities, personal preferences, successful usage receipts,
  transactional audit, version descriptions/dependencies, and explicit file references.
- Preserve assets and historical files in Trash; add restore and owner-only team permanent deletion.
- Add code-built Trash and Version details views to the existing Library Tools menu.
- Separate metadata/preview changes from HDA version creation; preserve historical snapshots.
- Add SQLite v4→v5 and PostgreSQL v1→v2 upgrades, API v2 compatibility checks, and legacy pending review.
- Add explicit integrity checks and reference-safe cleanup commands; preserve missing-file metadata.
