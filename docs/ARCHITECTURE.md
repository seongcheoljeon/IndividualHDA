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

The 59-test suite includes populated-panel search, model notifications, archive
roundtrips and rollback, schema migration, and process lifecycle checks. New
structural-refactor cases verify rollback across catalog/assets/nodes/history and
actual panel background completion, failure, duplicate-job prevention and deferred
close, host destruction and annotation coverage. Windows Houdini 21.0.559 also passed the native HDA roundtrip and panel smoke
script after extraction. Platform and interactive limitations are recorded in
[VALIDATION.md](VALIDATION.md).

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
hooks. Test helpers are annotated too. Generated Designer/resource modules and
vendored dependencies are excluded from manual annotation edits.

The syntax target is Python 3.11, matching the installed Houdini 21 build. Modern
union/container annotations, postponed annotation evaluation, `Self`, `ParamSpec`
and `TypeVar` preserve host compatibility and decorator signatures. An AST test
checks both signature coverage and Python 3.11 syntax. Ruff enforces signature
annotations on future changes.

`Any` remains at dynamic boundaries such as Qt item roles, signal payloads and
heterogeneous legacy asset dictionaries. It does not establish a fully static
schema for those values. `python -m mypy` checks the 17 database, filesystem,
serialization and process modules configured in `pyproject.toml`. It does not
claim that the complete Qt mixin graph or generated widgets pass strict type
checking; imported host/widget implementations are outside that configured check.

## Proxy and theme audit

Shared predicates are in `model/proxy_filters.py`. Tree descendant propagation
uses Qt's recursive filtering; record/file constraints must match the same row.
Selection uses explicit source/proxy mapping. Model mutations must emit the
appropriate structural/data notifications before dependent proxies are read.
Dark resources are registered by the loader itself, and default theme overrides
are combined with Houdini's stylesheet on the panel only.
See [AUDIT.md](AUDIT.md) for findings, fixes and acceptance limits.


## Follow-up items 2–5

See [REFACTOR_2_5.md](REFACTOR_2_5.md) for explicit state owners, typed payloads, schema v2 crash recovery, asynchronous bounded thumbnails, measured performance and remaining limitations.


## SOLID service boundaries

See [SOLID.md](SOLID.md) for the current dependency map. `PanelServices` selects
concrete adapters; the panel accepts it through an optional constructor argument.
`AssetStore` emits changes through `RowNotifications`, with `QtAssetNotifications`
coordinating list/table models. `ArchiveTransfer` owns path-based archive work and
`DataStream` delegates for legacy dialog callers. `LibraryReader` owns snapshot
connection cleanup. Rename planning/execution uses `RenamePlan` and
`SQLiteRenameRepository`. `TaskController` now owns process startup/completion as
well as file jobs; callers cannot replace its active-job properties.
