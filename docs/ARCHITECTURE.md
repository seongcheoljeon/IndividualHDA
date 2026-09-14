# Module responsibilities

## Panel

`main.IndividualHDA` remains the panel entry point. It owns window construction,
shared UI state and shutdown. Feature wiring lives in bootstrap. Designer
layouts and widget object names are unchanged.

Feature mixins in `widgets/panel/` contain related behavior:

| Module | Responsibility |
| --- | --- |
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
deferred close, host destruction and annotation coverage. Host-side checks and
their limits are recorded in [VALIDATION.md](VALIDATION.md).

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
hooks. Test helpers are annotated too. Generated Designer/resource modules are
excluded from manual annotation edits.

The syntax target is Python 3.11, matching the installed Houdini 21 build. Modern
union/container annotations, postponed annotation evaluation, `Self`, `ParamSpec`
and `TypeVar` preserve host compatibility and decorator signatures. An AST test
checks both signature coverage and Python 3.11 syntax. Ruff enforces signature
annotations on future changes.

`Any` remains at dynamic boundaries such as Qt item roles, signal payloads and
heterogeneous legacy asset dictionaries. It does not establish a fully static
schema for those values. `python -m mypy` checks the database, filesystem,
serialization, process and service modules configured in `pyproject.toml`. It does not
claim that the complete Qt mixin graph or generated widgets pass strict type
checking; imported host/widget implementations are outside that configured check.

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
- Remaining direct facade uses (`_db_api_wrap`) are local-only paths: DB cleanup,
  path repair, backups, scene records and context-menu lookups. They are the Phase 2
  worklist and are disabled in server mode.
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
