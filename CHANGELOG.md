# Changelog

## Unreleased — modern editing

- **Tags are chips.** The tag pane no longer takes `#a #b` text. Committed tags
  are chips (click one to search it, × or Backspace removes it); the line below
  completes from the tags already in the library. Enter, comma or space commit.
  AI suggestions arrive as dimmed chips to accept, never as an overwrite.
- **Personal notes and tags autosave.** Edits are written about 1.5 s after
  typing stops, and when you select another asset, switch library or close the
  panel. The Yes/No prompt on every save is gone; the status line reads
  `Unsaved`, `Saving…`, `Saved · just now` or `Save failed — edits retained`.
  The team library keeps one explicit Save button (writes carry a revision and
  may conflict). Note history gains one row per pause, not per keystroke.
- **Notes preview as Markdown.** A toggle next to the note swaps the editor for
  a rendered view (headings, emphasis, lists, links). Notes are still stored as
  plain text, so nothing changes for existing notes or the note history.
- **Left-drag and double-click import.** Assets drag out of the list, table and
  history views with the left button as well as the middle one, and a
  double-click imports the selection into the current Network Editor
  (Ctrl+double-click plays the preview video, which the plain double-click
  used to do). The three views share one drag implementation.
- **Keyboard shortcuts.** Ctrl+S saves, Ctrl+F focuses the search, Esc clears
  it, F5 reloads, Enter imports the selected assets and Delete moves them to
  the Trash. All are scoped to the panel or to one view, so Houdini keeps its
  own keys and nothing fires while typing a note. The video player's `f`
  (fullscreen) key, present but unconnected, now works.

## 2.2.0 (unreleased) — activity history, trash hygiene and the SOLID audit

- **History shows renames and video changes.** Rename and preview-video events
  were already recorded by the audit triggers but never shown. They appear as
  italic non-version rows (`NAME (CHANGE) old → new`, `VIDEO (INSERT/UPDATE)`)
  interleaved by time with the versions, in the personal and the team library;
  they own no files, so open/detail/delete/drag skip them. The Version details
  Activity tab names the rename (`Renamed "old" → "new"`) and says whether a
  video was attached or replaced.
- **Emptied categories disappear.** Deleting an asset moves it to the Trash and
  keeps its row until purge, so the category cleanup trigger never fired and
  `obj`/`sop` stayed in the tree. The category query now lists only categories
  with a live asset; restoring brings the category back.
- **Trashed assets stay out of every read.** Tags, icons, thumbnails, names and
  ids of trashed assets leaked into the UI through reads that selected from
  `hda_key` directly. One live-row filter is applied everywhere; the few reads
  that must see trashed rows say why in the SQL, and a test forbids new
  unfiltered reads. Registering a name that sits in the Trash says so.
- **Purge can free the files it left behind.** Permanent deletion queued the
  files but nothing deleted them. The Trash dialog now previews the queued
  files after a purge and asks before removing the ones no version references,
  together with the directories they leave empty; referenced or out-of-root
  files are reported and kept.
- **Writes commit as one unit.** Note, tag and registration name checks and the
  multi-statement rename/scene-record writers run inside a transaction and
  report SQLite errors as `LibraryError`.
- **Team server.** Listing assets and histories no longer runs one query per
  row; two indexes back the hot reads (schema 4 — run the `upgrade` CLI once);
  PostgreSQL listings read under REPEATABLE READ so the revision matches the
  rows; the audit event listing accepts `offset`/`limit`. Reads and writes go
  through one authorized access layer, each operation is a handler, and the
  audit trail has its own module.
- **Panel architecture.** Features talk through ports (`widgets/panel/ports.py`)
  and never reach another feature's private members; the personal/team split
  is behind `LibraryPort`, chosen in one place. `LibraryRepository` is the union
  of three role protocols. Item models stop touching the filesystem and
  rewriting rows while painting. The main window and the preference dialog
  build their large sections in their own modules, `HoudiniAPI` is a facade over
  topic modules, and a task started from a completion callback is queued
  instead of dropped. Guard tests keep each of these from regressing; see
  CONTRIBUTING.md.

## 2.1.1 (unreleased) — registration durability and panel typography

- **Registration on Windows.** Flush staged capture files through a writable
  handle. `os.fsync()` on a read-only descriptor maps to EBADF there, which
  failed every node registration with "[Errno 9] Bad file descriptor". The same
  call in the PostgreSQL backup adapter is corrected, and the platform rule now
  lives in one place.
- **Registration thumbnails.** Stage captures under their destination filenames.
  Houdini selects the flipbook image format from the path suffix, so the former
  extension-less `thumbnail` staging name produced no file and assets committed
  without a thumbnail. A capture that yields no optional file is now logged
  instead of passing silently.
- **Bundled panel font.** Ship MaruBuri in `resource/fonts` and apply it to the
  panel subtree, including the windows it opens. The host application font is
  left alone so Houdini keeps its own look, and an explicit font still wins so
  the Preferences font choices keep working.
- **Library Tools menu placement.** Insert the menu before Help instead of
  appending after it.
- **History says what it recorded again.** A refactor swapped the INSERT/UPDATE
  marker written into the history comment for the payload's change description,
  which is empty unless the user asks to add one, so every row since went blank.
  The kind is intrinsic to the operation and is recorded again, with the
  description appended when there is one. Rows already written stay as they are.
- **Scene records survive a deleted node.** The imported-node list is scanned
  with `in` on every import, and a HOM node raises ObjectWasDeleted once the
  user deletes it -- so one deleted node aborted the whole record with
  "Imported asset; scene record could not be queued". Observations now compare
  on the node's session id and never on the node itself.
- **Quiet video playback.** Stop logging the player's window title. Buffering
  and track changes fire several times a second and each one wrote the same
  string the title already showed, burying everything else in the panel log. A
  decode or backend failure reached the log only inside one of those lines, at
  info level; it is now reported as an error.
- **AI suggestion progress and cancel.** The request reports its running token
  count and elapsed time beside the AI button, and a cancel button stops it. The
  provider gains an optional plain callback -- Qt stays out of `libs/` -- and
  cancelling is that callback refusing to continue, so no cancel token has to
  cross the boundary. A cancelled request is logged as cancelled, never as a
  failure, and its answer never reaches the editors.
- **Separate unsaved indicators for the note and the tags.** Each editor has its
  own save button but they shared one "Unsaved changes" label, sitting under the
  note; editing tags lit it there, and an AI suggestion fills both at once. The
  note line keeps the shared statuses (saving, save errors, team conflict links)
  and a new label under the tag editor carries tag dirtiness alone.
- **Applying a downloaded AI model.** Selecting a model in the installed list now
  clears the catalog selection. A refresh preselects the recommended catalog row
  and the catalog was read first, so "Use as AI backend" stayed disabled whenever
  the recommendation was not the model actually installed — leaving every request
  to fail with "choose a model in Preferences (AI) first". The AI button in the
  tag row also pins the shared icon size instead of the style default, which made
  it smaller than its neighbours.
- **Menu icons.** Give the Library Tools menu and the team library context menus
  the icons they never had, and fill the remaining gaps in the menu bar. Three
  entries pointed at `_18dp`/`_48dp` resource names that exist in no .qrc and so
  drew nothing; they now use the names that are actually bundled. A test walks
  every literal icon resource in the source and fails on one that does not
  resolve.
- **Web view rendering on Windows.** Add `$HFS/bin` to PATH before the help
  browser starts. Houdini keeps QtWebEngineProcess.exe in `$HFS/qt/bin` with no
  Qt DLLs beside it and does not put `$HFS/bin` on PATH, so Chromium's helper
  process exited with STATUS_DLL_NOT_FOUND and every page failed to load. A dead
  helper and a failed load now report themselves separately in the log.
- **Web view start page.** Stop persisting the Houdini help server address. Its
  loopback port is assigned per launch, so restoring it pointed the next session
  at a dead port. Addresses the user navigated to are still restored, an existing
  stale entry is dropped on load, and a failed load now records the URL it
  requested rather than the page still on screen.
- **Video playback without FFmpeg.** Remove the FFmpeg check from the two
  double-click playback paths. Playback runs through QMediaPlayer and never
  shells out, so an unset FFmpeg directory silently blocked videos that already
  existed. Video *creation* still requires FFmpeg, and the Preferences indicator
  now reports the same condition that gates it instead of merely testing that the
  directory exists.

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
