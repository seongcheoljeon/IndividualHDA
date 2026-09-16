# Module responsibilities

## Panel

`main.IndividualHDA` remains the panel entry point and Qt event router.
`PanelComposition` creates services, session/widgets and models, then connects
features; `PanelBootstrap` handles initial loading and widget/signal setup.
`PanelShutdown` owns close policy and `PanelLifetime` orders resource cleanup.
AI, archive and library-sync integrations are composed objects, with explicit
forwarding methods for existing panel callers. The 12 remaining feature Mixins
still share legacy window state; feature presenters use the MVP boundaries below.
Every screen now has a maintained
Python layout; no Designer sources or generated layout modules remain. Persisted
control and splitter names retain their existing identities. See
[UI_EDITING.md](UI_EDITING.md) for the screen map and editing workflow.

Feature modules in `widgets/panel/` contain related behavior:

| Module | Responsibility |
| --- | --- |
| `composition.py` | Ordered construction and ownership of acquired resources |
| `lifetime.py`, `shutdown.py` | Worker/timer/view cleanup, close refusal and retry |
| `bootstrap.py` | Initial loading, widget setup and signal wiring |
| `presentation.py` | Fonts, sizes, overlays, preferences and application information |
| `selection.py` | Selection, search, comboboxes and item activation |
| `host_callbacks.py` | Houdini event/selection callbacks and guarded deferred execution |
| `asset_management.py` | Rename, favorites, deletion and library cleanup |
| `library_queries.py` | Panel queries, row lookup and shared history insertion |
| `notes.py` | Notes, tags and detail views |
| `context_menus.py` | Asset, history, category, record and inside-node menus |
| `asset_registration.py` | Dropped Houdini nodes, asset metadata and transactional registration/update |
| `houdini_actions.py` | Asset instantiation, scene records, node connections and comments |
| `model_binding.py` | Model/proxy construction, filters, pixmaps and coordinated model notifications |
| `media_actions.py` | Thumbnails, preview capture and asynchronous video encoding completion |
| `archive_actions.py` | Import/export dialogs, background work and activation at shutdown |

These mixins are parts of one panel, not independently instantiated widgets.
They use protected (`_name`) panel attributes and methods. The old double-private
names were internal implementation details; Python name mangling must not be used
as a cross-module interface. The mixins have no constructors and do not add Qt
base classes, so the panel owns all QObject initialization and destruction.

Modules do not import `main`; calls to panel helpers dispatch through `self`.
Do not add UI dependencies to the underlying archive, process or database code.
If a feature becomes reusable outside the panel, extract a service with explicit
inputs rather than giving it more access to window state.

All widgets, Qt models and Houdini HOM operations remain on the GUI thread.
`BackgroundJob` handles archive filesystem work; it receives neither widgets nor
an existing database connection. Its completion slots update the panel on the GUI
thread. `ProcessJob` owns encoders/probes. Panel shutdown waits for archive work
and stops encoding before dependent UI objects are destroyed.

## Asset browser: first MVP migration

The search controls, zoom/view controls and list/table container are code-built in
`widgets/asset_browser/view.py`. The code-built `MainWindowLayout` in
`widgets/panel/layout.py` embeds this widget. Existing
custom item views, item models and proxy models remain in use. The counter is
owned by the browser but placed in the existing footer by the integration adapter.

- **View:** widget construction, model filters, result count and asset-ID selection
  signals. It knows no database, transport, main-window state or business rules.
- **Presenter:** typed search requests, busy/error state and gateway invocation.
  It imports neither Qt, Houdini, SQL nor the main window. A failed query leaves
  the last successful result visible.
- **Search gateway:** `libs/browser_search.py` defines an immutable `SearchRequest`
  and the small `AssetSearchGateway` / `SearchRepository` protocols. The local
  implementation delegates to the existing repository, which owns connections.
- **Executor:** existing `AssetSearch` runs blocking operations away from the GUI
  thread and delivers only the current generation, including errors. Search
  options are captured per request; the optional AI rewrite still runs in the
  worker. Invalidate immediately when input changes, before debounce fires.
- **Integration:** `widgets/asset_browser/integration.py` owns browser aliases;
  `widgets/asset_details/integration.py` adapts the existing metadata editors. It bridges asset IDs back to legacy
  selection handlers, context menus and Houdini drag/activation actions. Delete
  main-window aliases as consumers migrate. Code-built widgets retain the existing
  `widgetType__purpose` style (for example `lineEdit__search_hda`) in both Python
  attributes and object names. Use descriptive snake_case for presentation and
  service state; avoid generic names such as `query`, `field` or `manager` for
  widget attributes. The Presenter never accesses widget attributes directly.
- **Composition:** `PanelServices` injects the search gateway factory and executor.
  Preferences replace the gateway and invalidate pending work. Shutdown stops
  debounce, invalidates outstanding results and drains workers before deletion.

The main panel still owns the shared AssetStore and legacy model construction;
this change does not claim to migrate all panel state or all business operations.
The executor contract requires stale-result suppression and GUI-thread delivery.
A future HTTP implementation also needs bounded request timeouts: cancellation
invalidates a result but cannot interrupt an arbitrary blocking call.

## Feature presentation boundaries

| Feature | Presenter / use case | Qt integration |
| --- | --- | --- |
| Notes and tags | `widgets/asset_details/presenter.py` | `asset_details/integration.py`, `panel/notes.py` |
| Registration, rename and removal | `widgets/asset_lifecycle/presenter.py`, `libs/asset_lifecycle.py` | `panel/asset_registration.py`, `panel/asset_management.py` |
| Thumbnail/video metadata | `widgets/asset_media/presenter.py` | `panel/media_actions.py` |
| Detail display | `widgets/detail_view/presenter.py` | `detail_view/detail_view.py` |
| History date range | `widgets/history/presenter.py` | `panel/selection.py` |
| Rename validation | `widgets/rename_ihda/presenter.py` | `rename_ihda/rename_ihda.py` |
| Video capture validation | `widgets/make_video_info/presenter.py` | `make_video_info/make_video_info.py` |
| Storage preference validation | `widgets/preference/presenter.py` | `preference/preference.py` |
| Web zoom | `widgets/web_view/presenter.py` | `web_view/web_view.py` |
| Playback metadata | `widgets/video_player/presenter.py` | `video_player/video_player.py` |
| AI model actions | `widgets/ai_models/presenter.py` | `ai_models/dialog.py` |
| Library explorer paging | `widgets/library_manager/presenter.py` | `library_manager/dialog.py` |

Presenters import no Qt, HOM, main window or concrete database implementation.
Views retain widget access, model notification, local file dialogs and host calls.
Existing library maintenance, AI transport, playlist and settings services remain
responsible for their operations. This is separation of feature policies and
coordination; it does not eliminate every panel mixin or convert all Qt event
handlers into presenters.

Metadata saves use their own TaskController. Each request captures its repository,
asset ID and submitted values. Drafts survive selection changes and failed saves;
edits made during a save remain dirty. Switching libraries drains the old writer
and resets drafts; changing preferences for the same library preserves drafts.
Drafts are held in memory for the current panel session, not persisted across restarts.
Errors remain visible next to the editor. Library reload results started before a
metadata write are discarded so they cannot replace newly saved data with old rows.

Lifecycle and media presenters report storage failures without running the
committed callback. UI/model exceptions after commit propagate separately from
storage failures. LocalAssetLifecycle owns rename path planning and uses the
existing journaled SQLite/file transactions. Registration captures HOM data and
creates host files on the GUI thread before invoking the local use case. These
lifecycle operations remain synchronous; HTTP implementations need asynchronous
command execution, cancellation/close handling, and upload/download support before
they can be enabled. `PanelServices.lifecycle` is the local adapter factory;
unimplemented server mode is rejected explicitly instead of silently using SQLite.

Dialog button boxes call the dialog's validation; main-panel actions listen to
`QDialog.accepted`. Connecting a main action directly to a button box's `accepted`
would bypass validation and must not be reintroduced.

### Personal and team/studio evolution

The browser-facing boundary describes user operations, not database transactions.
Personal mode executes use cases locally through SQLite/file adapters. Team mode
will call a FastAPI application that runs server use cases through PostgreSQL and
file-storage adapters. Pure business rules may be shared; server-side permission
and consistency checks remain authoritative. Houdini extraction and HDA creation
stay in the host client.

The current search result is a set of IDs filtering an already loaded AssetStore,
with the existing repository limit of 5,000 matches. This is a compatibility step,
not the final remote query design. Before implementing the server:

1. Add paged asset results and server-side sorting/filtering together; avoid one
   HTTP request per existing repository helper or client-side loading of all rows.
2. Move rename/delete/register requests to IDs and intent. Resolve paths and
   perform file operations inside the appropriate use case/storage adapter.
3. Define revision-based conditional updates and conflict errors, request IDs for
   idempotent writes, authenticated project/team scope, and API compatibility.
4. Choose shared storage versus upload/download and local cache resolution;
   define recovery when file and metadata operations only partially succeed.
5. Decide offline behavior explicitly. No bidirectional sync or offline write
   queue is implied by supporting two backends.

Follow-up presentation-logic migration order: detail/notes/tags,
registration/rename/deletion, history/media, then remaining dialogs. All of their
layout construction is already Python-only. Each feature gets narrow interfaces and
its own presenter; avoid a single global presenter or service interface. No
server, database migration or file relocation is introduced by this first step.

## Database

`libs.sqlite3_db_api.SQLite3DatabaseAPI` is the compatibility facade. Public class
methods, signatures, return values and context-manager usage remain available.
Implementation lives in `libs/database/`:

| Module | Responsibility |
| --- | --- |
| `session.py` | Connection/cursor ownership, close, backup and transaction boundaries |
| `catalog.py` | Users, categories and asset keys |
| `assets.py` | Current asset data, tags, notes, locations and media metadata |
| `nodes.py` | Houdini node metadata, paths and input/output connections |
| `history.py` | Version and note history |
| `records.py` | Scene usage records |
| `values.py` | Value conversions and ordered row-key layouts |

Operation mixins share exactly one session. They must not open independent
connections or commit directly: use `_commit`/`_rollback` so operations across
multiple domains participate in the caller's `transaction()` block. Keep SQL
parameters bound, and create/use/close each database API instance on one thread.
The migration implementation remains in `libs/database_migrations.py`; moving
queries between files does not require or change the database schema version.

## Verification

The regression suite (`python -m pytest -q`) covers populated-panel search, model
notifications, archive roundtrips and rollback, schema migration, process
lifecycle, cross-module transaction rollback, panel background completion and
deferred close, host destruction, startup fallbacks, settings tolerance, data
safety (WAL, orphan cleanup, auto backup), Python layout construction and dialog contracts, version
consistency, the architecture ratchets and annotation coverage. CI runs
`ruff check`, `ruff format --check`, `mypy` and `pytest --cov` with a coverage
floor (`pyproject.toml`); `requirements-dev.txt` pins the tools. Host-side checks
and their limits are recorded in [VALIDATION.md](VALIDATION.md).

The session-scoped `app` fixture deletes every top-level widget a test left
behind before the interpreter exits (explicit `DeferredDelete` delivery, then a
garbage-collection pass): widgets freed after Qt's static destructors, including a
`QWebEnginePage`, crash the process at exit.

## Houdini host contract

The production entry is a Houdini Python Panel. Its `onCreateInterface()` returns
`IndividualHDA(embedded=True)` and lets Houdini own the root widget. Shelf-launched
floating windows continue to use `hou.qt.mainWindow()`. The app never creates a
second QApplication or installs/replaces Houdini's Python or Qt libraries.
The direct `PySide6` imports use the binding bundled with Houdini, as in the
[SideFX Qt cookbook](https://www.sidefx.com/docs/houdini/hom/cb/qt.html).

`onDestroyInterface()` calls `shutdown_for_host()`: it finishes archive work and
consumes the result before Houdini deletes the widget. A normal close may defer
itself; a host destroy notification cannot veto widget destruction. Queued result
slots tolerate already-consumed results. Deferred HOM actions use SideFX's
`hdefereval.executeDeferred` and skip execution after shutdown begins.
See [Python Panel hooks](https://www.sidefx.com/docs/houdini/ref/windows/pythonpaneleditor.html)
and [floating-window ownership](https://www.sidefx.com/docs/houdini/hom/hou/qt/mainWindow.html).
The installed `$HFS/houdini/python3.11libs/hdefereval.py` was also inspected to
confirm the main-thread deferred-execution behavior.

## Type annotations

All functions/methods in maintained production Python files have parameter
and return annotations (implicit `self`/`cls` excluded), as do the Python Panel
hooks. Test helpers are annotated too. Generated resource modules are
excluded from manual annotation edits.

The syntax target is Python 3.11, matching the installed Houdini 21 build. Modern
union/container annotations, postponed annotation evaluation, `Self`, `ParamSpec`
and `TypeVar` preserve host compatibility and decorator signatures. An AST test
checks both signature coverage and Python 3.11 syntax. Ruff enforces signature
annotations on future changes.

`Any` remains at dynamic boundaries such as Qt item roles, signal payloads and
heterogeneous legacy asset dictionaries. It does not establish a fully static
schema for those values. `python -m mypy` runs over the whole tree with
`follow_imports = "normal"` (`pyproject.toml`). Two override groups keep it green:
generated resource modules are never checked, and the panel mixins plus
the item models carry `ignore_errors` because a mixin's `self._x` attributes are
declared on the composed `IndividualHDA`, which mypy cannot see from the mixin.
Remove a module from that second list once it passes; do not add to it.

## Layers and ratchets

`tests/test_architecture.py` encodes the module rules as AST checks (function-level
imports included, `TYPE_CHECKING` blocks excluded):

| Layer | Modules | Rule |
|---|---|---|
| host boundary | `libs/host.py`, `libs/houdini_api.py`, the pypanel | only place `hou` is imported |
| domain | `libs/database/*`, `libs/domain.py`, `libs/repository.py`, `libs/settings_store.py`, … | no Qt, no `hou`, no `public` |
| Qt libs | the rest of `libs/` | no `hou` |
| model / view / widgets / app | everything else | no `hou`; nothing imports `main` |

Ratchets are exact sets or counts that may only shrink: `PUBLIC_IMPORTERS`
(modules still importing the `public` facade; new code imports `libs.keys`,
`libs.paths`, `libs.platform_info`, `libs.host` directly), `SHARED_PANEL_STATE`
(panel attributes written by more than one mixin), `LOCAL_DB_SITES` (direct SQLite
facade uses, see above) and `HOU_IMPORTERS` (empty). Adding a violation fails the
suite; removing one requires updating the constant, which is the intended review
point.

Module homes after the split: constants in `libs/keys.py`, paths and the SQLite
file layout in `libs/paths.py`, OS predicates in `libs/platform_info.py`,
`IS_HOUDINI` in `libs/host.py`, the About/License HTML in
`widgets/panel/presentation.py`, tree nodes in `model/tree_nodes.py` and the shared
font/padding setters in `model/model_style.py`. `public.py` only re-exports.

## Proxy models and themes

Shared predicates are in `model/proxy_filters.py`. Tree descendant propagation
uses Qt's recursive filtering; record/file constraints must match the same row.
Selection uses explicit source/proxy mapping. Model mutations must emit the
appropriate structural/data notifications before dependent proxies are read.
Dark resources are registered by `libs.qt_helpers.dark_stylesheet()` itself, and
default theme overrides are combined with Houdini's stylesheet on the panel only.

## Service boundaries

`widgets/panel/services.py` is the composition root. `PanelServices` selects
concrete adapters and the panel accepts it through an optional constructor
argument, so a dependency can be replaced without modifying feature methods.

| Extension point | Contract | Default |
| --- | --- | --- |
| Library storage | `LibraryRepository` (`libs/repository.py`) | `SqliteLibraryRepository` via `PanelServices.repository(context)` |
| Naming | `AssetNames` | `HoudiniAPI` |
| Rename persistence | `RenameRepository` (inside the SQLite adapter) | `SQLiteRenameRepository` |
| Durable file/DB operations | `OperationFactory` | `durable_operation` |
| Database, archives, tasks | callables on `PanelServices` | `SQLite3DatabaseAPI`, `ArchiveTransfer`, `TaskController` |
| AI backend | `AIProvider` | `NullProvider` via `make_provider` |

`AssetStore` emits changes through `RowNotifications`, with `QtAssetNotifications`
coordinating list/table models. `ArchiveTransfer` owns path-based archive work.
Rename planning/execution uses `RenamePlan` and `SQLiteRenameRepository`.
`TaskController` owns file jobs and process startup/completion; callers cannot
replace its active-job properties.

## Library repository

`libs/repository.py` is the storage boundary: `LibraryRepository` (list, categories,
histories, search, tags/notes, favorite, rename, delete, `register_asset`,
`add_version`, `revision`), `RegistrationPayload`/`RegistrationResult`, the
`LibraryError` hierarchy and `LibrarySettings`. It imports neither Qt nor HOM.
`libs/database/sqlite_repository.py` adapts the existing `SQLite3DatabaseAPI` facade
and the journaled file commands; registration bodies live there. Rules:

- The panel gathers everything HOM knows (node info, HDA file, thumbnail, hip, frame
  range) on the GUI thread into a `RegistrationPayload`; the repository only writes.
- Local mode calls the repository synchronously (milliseconds). The HTTP adapter
  for server mode (Phase 2) plugs into `PanelServices.repository`; the panel then
  wraps writes in `_start_file_job` without changing the call sites.
- Lookups the panel needs (`has_asset`, `asset_identity`, `asset_names`,
  `has_history`, `note_history`, `latest_video`, `record_detail`, …) and small
  writes (`set_thumbnail`, `set_video`, `add_history_row`, `delete_note_history`,
  `delete_scene_record`) are repository methods too; the adapter turns the facade's
  `None` results into `LibraryError`.
- Three direct facade uses (`_db_api_wrap`) remain and are pinned by the
  `LOCAL_DB_SITES` ratchet: the two database-cleanup passes in `asset_management`
  (unused records, missing files) and the scene-record placement in
  `houdini_actions`. They are local-only maintenance and are disabled in server mode.
- Errors surface as `LibraryError` subclasses; `LibraryConflict` means reload and retry.

## Identity and LibraryContext

`libs/identity.current_user()` is `IHDA_USER` or the OS login. A local SQLite library
adopts the single user row it already has (`resolve_local_user`), so libraries
created as `anonymous` open unchanged. `LibraryContext` (`libs/domain.py`) is an
immutable snapshot of user, data directory, database path, asset root and per-user
HDA root, rebuilt only when Preferences change (which already requires a restart).
Mixins read `self._library`; the Preference dialog is not a settings service.

## Search

Asset search runs in the repository (`search_asset_ids`, implemented over SQLite
`LIKE`/`GLOB` in `libs/library_explorer.py`): whitespace tokens are ANDed, `*`/`?` are
wildcards, and `name:`/`tag:`/`type:`/`note:` prefixes restrict a token. Tags come from
the trigger-maintained `asset_tags` index; notes and definition comments are
searchable through the `Note`/`All` fields. `libs/asset_search.AssetSearch` runs the
query off the GUI thread and drops superseded results; the list/table proxies then
show only the returned ids (`set_id_filter`). Empty queries never start a job. FTS5
was rejected because its tokenizers break one- and two-character Korean searches;
the swap point is `search_asset_ids` alone. `AssetSearch.rewrite` is the hook where
the AI natural-language search will translate text into this syntax.

## Change detection

`widgets/panel/library_sync.py` polls `repository.revision()` every 10 s on a third
`TaskController` and reloads rows, categories, histories and icons when it changes,
keeping the selection if the asset still exists. The toolbar Reload action runs the
same `reload_library()`. Locally the revision is the database file mtime; the server
returns a counter bumped by every write.

## Optional media modules

`widgets/video_player.make_video_player` and `widgets/web_view.make_web_view` import
`QtMultimedia`/`QtWebEngine` lazily and return a placeholder widget with the same
method surface when a Houdini build lacks them, so the panel always opens.

## AI provider

`libs/ai_provider.py` is the only AI-facing module and imports neither Qt nor
HOM (the domain import-guard test enforces this). It defines `AISettings`
(backend kind, endpoint, model, API-key environment variable name), `Prompt`
(text, system, optional image bytes), the `AIProvider` protocol with a single
`complete(prompt) -> str`, `NullProvider`, and `make_provider(settings)`.

Rules for adding a real backend or feature:

- Backends implement `complete` only and are selected in `make_provider` by
  `settings.kind` (`local`, `anthropic`, `openai`). Use the standard library
  (`urllib.request`) with an explicit timeout on every request; do not add
  packages to Houdini's Python. Read the API key from
  `os.environ[settings.api_key_env]` at call time; never persist the key.
- Features (asset description/tags, natural-language search, effect generation
  from text or images) are functions layered on `complete`: build a `Prompt`
  from plain data, parse the returned text. They live in `libs/`, not in mixins.
- The panel obtains a provider with `self._services.ai(self._preference.ai_settings)`
  and runs the call on `self._ai_tasks` (a second `TaskController`), never on the
  archive/encoder controller, so network latency does not block imports or
  encoding and does not take the whole-window lock. One AI call runs at a time;
  the completion callback executes on the GUI thread; `closeEvent` drains it.
- Preferences keep the settings under one `"ai"` key in `preference.json`; the
  "AI (Optional)" group is built in `widgets/preference/preference.py`. `FIELDS`
  in `libs/ai_provider.py` lists the fields each backend reads; the dialog enables
  only those (with `PLACEHOLDERS` as hints) and a backend must not read any other.

Implemented so far:

- `libs/ai_backends.py`: `OllamaProvider` (`POST /api/chat`, base64 images, 60 s
  timeout, no retries) and `AIError`. Requests go through a proxy-free opener so a
  studio `HTTP_PROXY` never captures localhost. `make_provider` dispatches
  `kind == "local"` here; `anthropic`/`openai` still resolve to `NullProvider`.
- `libs/ollama.py`: server management for the Local AI Models dialog — version
  probe, installed models, streaming `pull` with progress and cancel, GPU memory
  detection (`nvidia-smi`, macOS unified memory) and the `RECOMMENDED` catalog of
  vision-capable multilingual models with `choose_recommended(vram_gb)`. The
  catalog was verified against ollama.com on 2026-09-14; update the tuple when
  models move on.
- `widgets/ai_models/dialog.py` (`LocalModelsDialog`, opened from Tools > Local AI
  Models… or Preferences > AI): all HTTP on its own `TaskController`; the pull
  reports progress by emitting a dialog signal from the worker thread. "Use as AI
  backend" only fills the Preference fields; OK saves them. No automatic
  installation of Ollama itself — the dialog shows the download page and the OS
  install command.
- Feature A, `libs/ai_features.py` + `widgets/panel/ai_actions.py`: the AI button
  next to the tag editor (and the asset context menu) asks the model for a summary
  and tags from stored metadata, the studio tag vocabulary and the thumbnail. The
  prompt never contains paths, users or hip locations (tested). The answer only
  fills the note/tag editors; the user's Save click persists it.

## Personal/team switching in the main panel

`MainLibraryIntegration` connects the existing asset models and metadata editors to
`WorkspacePresenter`. The library selector lives in `AssetBrowserView`; connection
and member settings live in `widgets/library_connection`. There is no separate
workspace browser. `MainAssetActions` owns Qt menus and file selection; the presenter
owns commands, drafts, revisions and retries. `PanelCatalog` prepares remote metadata
on a worker. The existing bounded `ThumbnailCache` accepts a file resolver and
downloads visible previews on its image workers; QPixmap creation stays on the GUI thread. `asset_row` / `history_row` adapt documents for the existing
models; `DocumentSearch` searches an immutable snapshot with the existing token syntax.

A team connection is applied only after its initial read succeeds. The personal
repository/context and draft state are kept for switching back. During team use,
`window._repository` and `window._library` are `None`; local-only maintenance and
scene-record actions are disabled. Existing feature boundaries route remote intentions
to the injected presenter. File downloads happen before GUI-thread Houdini imports.
Project identity in drag payloads prevents cross-library ID collisions.

The server contract, transactions and deployment are described in
[TEAM_LIBRARY.md](TEAM_LIBRARY.md). HTTP commands retain optimistic revisions and
atomic request receipts. Recovery/comparison controls appear only after a failure.
The legacy `PanelServices.settings.mode` is not the user-facing library selector;
source switching is coordinated by the integration above.

### Library metadata and lifecycle v2

The v4 SQLite schema/rebuild is a frozen migration input (`database_migrations_v4`).
The ordered migrator adds identity, preferences, audit, version metadata, file references,
and trash state without replacing integer IDs. Legacy facade writes share these rules
through transaction-local request context and database triggers. Missing file diagnostics
never delete metadata. Personal lifecycle operations are implemented by `PersonalLifecycle`;
`LocalManagement` and `RemoteManagement` implement the focused management view port.

On the server, `LifecycleStore` joins the existing authorized catalog transaction. Preferences
have their own revision, while shared mutations append audit events and advance the project
revision. Retry receipts and audit records commit with mutations. Version snapshots retain
creation metadata when previews change. Foreign-key-cascaded file references are checked across
all projects before explicit cleanup. The API is v2; old pending commands are retained for
manual review, not silently replayed against the changed contract.

The UI remains code-built. Main-library selection is unchanged. Trash and version details
are small modal views with worker-owned IO; SQL and filesystem deletion never run in the view.

### Personal → Team copying

`PersonalCopySource` reads a SQLite transaction and hashes a portable snapshot without
writing the personal library. `CopyPresenter` prepares the destination and finds saved
work; `CopyAssetDialog` owns only form state and worker lifetimes. `CopyTransfer` depends
on the narrow `CopyDestination` protocol; `HttpCopyDestination` supplies authentication,
capability checks and blob/command transport. `CopyJobStore` atomically saves the frozen
selection and request identity under a process lock, without saving credentials.

The server's `copy_asset` command validates nested versions with existing create rules.
`copy_import` runs under the same project lock, authorization, receipt and transaction as
other writes. New asset/version identities and source provenance commit together; the
project revision advances once. Active and trashed assets participate in source/name
conflict checks. Uploads are content-addressed and precede registration. A lost commit
response is resolved by replaying the exact saved command before accessing source files.
Definitive rejected commands can recheck/reupload missing blobs; uncertain requests retain
their identity. Existing schema JSON fields hold provenance; no migration is needed.

### Server backup and isolated restore

`BackupService` coordinates a `BackupDatabase` protocol, verified file copying and
atomic publication of completed bundles. `PostgresBackup` exports a repeatable-read
snapshot, inventories every application table, and gives the same snapshot to
`pg_dump`. App tables and their sequences/constraints are dumped explicitly, so
restoration does not recreate the target database's existing public namespace.
`backup_files` owns manifest validation and file hashing; `backup_cli` supplies
administrator commands and environment-based connection configuration.

`storage_lock` is a Qt-free cross-process lock shared by upload, cleanup and backup.
It holds immutable blob contents stable while metadata changes can continue under
the exported database snapshot. Backup inventory includes registered unreferenced
uploads and trashed asset files; unregistered temporary files are excluded.

Restore requires an empty dedicated database and an absent blob destination. A
PostgreSQL advisory lock serializes restore commands to that database. Files and
dump are verified and staged before a single-transaction restore. Table hashes,
row counts and ownership are compared before publishing the staged blob directory.
No existing database is cleared, and service configuration is not changed. A failure
after the database commit can leave the isolated target populated; the command
never exposes an unverified blob destination or silently drops that database.

CLI passwords use a temporary protected pgpass file, never subprocess arguments or
backup manifests. The optional admin container includes PostgreSQL 16 client tools;
the Houdini client and main UI gain no server maintenance dependencies.

### Core value objects, copy ports and resource policies

`libs/file_integrity.py` defines immutable `FileContent(digest, size)` values and
streaming `measure_file()`. Generated equality and hashing use exactly the same
fields. Renaming a file preserves content equality; `Blob` equality still includes
its filename. The `Blob.content` property is excluded from dataclass serialization,
so wire references, command fingerprints and pending requests retain their format.
Cancellation is supplied as a callback; the shared reader has no Qt dependency.

Copy responsibilities now have separate homes:

| Responsibility | Module |
| --- | --- |
| Copy orchestration and uncertain-response replay | `libs/team/copy_workflow.py` |
| Destination and journal protocols | `libs/team/copy_ports.py` |
| HTTP destination adapter | `libs/team/copy_destination.py` |
| Atomic JSON persistence and process locking | `libs/team/copy_journal.py` |
| Compatibility imports for existing callers | `libs/team/copy_transfer.py` |

The workflow acquires `CopyJournal.locked()` instead of knowing a local lock path.
Its prepare, upload and submit steps are separate methods. The presenter accepts
destination/journal factories. A memory-backed journal test verifies uncertain
request replay without filesystem persistence; architecture tests prevent importing
concrete HTTP/SQLite/journal adapters into the workflow.

Configuration locations:

| Meaning | Location |
| --- | --- |
| API version and route prefix | `libs/team/contracts.py`: `API_VERSION`, `API_PREFIX` |
| Shared command/body/copy caps and default upload size | `libs/team/limits.py` |
| HTTP response/diagnostic/chunk budgets | injectable `HttpLimits` |
| SQLAlchemy connection/query/lock timeouts | injectable `DatabaseTimeouts` in `ihda_server/database_policy.py` |
| File hashing/copy chunk default | `FILE_READ_CHUNK_BYTES` in `libs/file_integrity.py` |
| Backup manifest size | `MAX_MANIFEST_BYTES` in `ihda_server/backup_files.py` |
| Restore lock identity and inventory batch size | named constants in `ihda_server/backup_postgres.py` |

For example, construct `HttpTransport(url, credential, limits=HttpLimits(response_bytes=8 * 1024**2))`
or `make_engine(url, timeouts=DatabaseTimeouts(statement_ms=15_000))`. Policies validate values
before use. Existing defaults remain unchanged. Protocol caps are shared validation rules;
changes require coordinated client/server review. The restore advisory lock key is a stable
cross-process identity, so deployments must continue using the same key.

Use operator overloading for value semantics with an unambiguous meaning. File content
supports equality, inequality and hashing. Service actions use named methods so database,
HTTP and file writes are explicit. Version labels remain user-defined strings; this change
does not introduce a numeric ordering rule for existing labels.

### Panel state and library interaction refactoring

The main panel keeps its Python layouts and named controls. Selection updates now
use `SelectionState.select_asset/select_history/select_category` rather than
assigning individual fields across mixins. `PanelSelectionPresenter` sequences
selection, detail display and dependent-view refresh through `SelectionView`;
Qt slots only decode model roles and forward input. Its `restore` method
rebuilds names, paths, versions and row positions from asset/history IDs after a
reload. The Qt adapter blocks selection signals during model resets, restores both
list/table indexes and the history filter, and then displays the current details.
The ALL history option survives reloads. Missing records clear their selection.

`LibrarySyncPresenter` owns the known revision, pending reload and close state. It
depends on `SyncView` and `SyncExecutor`; the panel supplies repository reads and Qt
model updates. Results from a replaced repository or from before a metadata save
are rejected. A save-invalidated result schedules a fresh read when work permits;
controller idle or the next poll performs the retry. Search filters and unsaved
metadata drafts remain owned by their existing feature presenters.

`PanelLibrarySession` is the port for selection/details, metadata save, refresh
and history requests. `PersonalPanelSession` connects local presenters;
`TeamPanelSession` connects the team integration. `LibraryCapabilities` describes
metadata editing, local file controls, member administration and the existing
save-confirmation policy. Storage-specific asset import, copy and recovery remain
in their dedicated integrations. Adding a backend should implement the required
ports rather than adding mode checks to the note and refresh slots.

Team history responses carry a selection generation, so A → B → A cannot install
the first A request. The history cache is marked loaded only on successful current
results. Busy requests wait for idle, failed requests can be retried, and a late
history response does not switch the user's current page. Dirty Team drafts retain
their original revision until explicit conflict review; refresh must not silently
rebase edits and bypass revision checks.

Shared toolbar icons, compact margins, spacing, tag color and asset/history column
widths live in `widgets/ui_tokens.py`. Values use Qt logical pixels; font and zoom
preferences continue to take priority. Keep feature-specific geometry in its layout.
This removes selection from the shared-panel-state ratchet without pretending that
all host and model mixins have been eliminated.

### Local registration capture and commit

`libs/asset_registration.py` contains `RegistrationService`. Its small ports are
`RegistrationCapture` (write HDA/optional thumbnail to supplied temporary paths)
and `RegistrationWriter` (commit prepared metadata, with reference-aware cleanup
on failure). `HoudiniRegistrationCapture` is the GUI-thread adapter in
`widgets/asset_lifecycle/capture.py`. `PanelServices.registration` selects the
service; the existing `AssetCommandPresenter` executes it before updating views.

The panel collects metadata and confirms new versions before capture. Both new
assets and added versions follow the same sequence:

1. Reject existing destination files, including dangling symlinks.
2. Capture into a private `.ihda-registration-*` directory. Require a nonempty HDA;
   thumbnail absence remains supported when a viewport is unavailable.
3. Publish using exclusive file creation. On a pre-commit publication failure,
   remove only files this attempt created, preserving a competing destination.
4. Delegate metadata commit to the existing local lifecycle/repository. Its SQL
   transaction and reference-aware cleanup remain authoritative once invoked.
5. Update views only after success. A view update failure reports that the asset
   was saved and requests a reload; it is not reported as a rolled-back save.

Display/render flags and the batch overlay are restored with `finally`, including
cancelled and failed operations. A failure to inspect DB references retains files
and logs the cleanup issue without replacing the original registration error.

This provides retry after a proven rollback, not a durable registration receipt.
An abrupt process exit can leave temporary/unreferenced files; existing library
inspection/cleanup can identify them. Do not automatically delete files when DB
commit status cannot be verified. Team registration continues using its existing
upload, command and pending-request receipt path, rather than local file cleanup.

### Rename and Trash presentation boundaries

`LocalAssetLifecycle.rename` validates names through `libs/asset_names.py` before
building a rename plan. The rename dialog re-exports/uses that same validation;
node-type conflicts are checked in the application service. File/SQL mutations
still use the existing rename journal and transaction, including rollback when a
history update fails. The panel keeps the dialog open on failure and always closes
the busy overlay. It captures the selected asset before executing the command.

`AssetCommandPresenter` accepts an optional committed-display-error callback.
The panel uses it to report a successful library change whose UI update failed and
request a reload, without classifying the change as a failed storage transaction.
The default presenter behavior still propagates display errors for other clients.

Asset and version Trash commands perform all destructive-looking UI updates only
inside committed callbacks. In a mixed batch, a failed asset retains its rows,
histories, selection and draft. Successful updates resolve row positions by ID.
Historical selection data is refreshed after path relocation and row shifts.
`_trash_history_rows` is the shared adapter for selected-assets/all-history menus;
it deduplicates records and skips current versions, while the repository remains
the authoritative protection at commit time. Note history and media files are
retained. Deleting a version no longer constructs physical file-removal requests.

The separate scene-record cleanup paths are outside this slice; they remain a
candidate for the remaining main-window/application-service refactoring.
