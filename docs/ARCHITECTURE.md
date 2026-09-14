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
| Naming | `AssetNames` | `HoudiniAPI` |
| Rename persistence | `RenameRepository` | `SQLiteRenameRepository` |
| Durable file/DB operations | `OperationFactory` | `durable_operation` |
| Database, archives, tasks | callables on `PanelServices` | `SQLite3DatabaseAPI`, `ArchiveTransfer`, `TaskController` |
| AI backend | `AIProvider` | `NullProvider` via `make_provider` |

`AssetStore` emits changes through `RowNotifications`, with `QtAssetNotifications`
coordinating list/table models. `ArchiveTransfer` owns path-based archive work.
`LibraryReader` owns snapshot connection cleanup. Rename planning/execution uses
`RenamePlan` and `SQLiteRenameRepository`. `TaskController` owns file jobs and
process startup/completion; callers cannot replace its active-job properties.

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
