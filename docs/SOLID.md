# SOLID refactoring

The panel keeps its existing widgets, menus, gestures, package entry point and
Houdini main-thread ownership. The changes separate application decisions from
Qt notification code, SQLite details and service construction.

## Responsibilities and dependencies

| Principle | Applied change | Contract / implementation |
| --- | --- | --- |
| Single responsibility | Asset rows/indexes no longer implement Qt notifications | `AssetStore` → `RowNotifications` → `QtAssetNotifications` |
| Single responsibility | Archive operations receive explicit paths; legacy dialogs delegate | `ArchiveTransfer`, `DataStream`, panel archive actions |
| Open/closed | Naming, repositories, operation contexts and job factories are replaceable | `AssetNames`, `RenameRepository`, `OperationFactory`, `PanelServices` |
| Liskov substitution | Unsupported model drops no longer report successful insertion; empty population remains appendable | List/table/history models and shared contract tests |
| Interface segregation | Read, delete, rename and transaction clients use small protocols | `libs/contracts.py`, `LibraryReadRepository`, `RenameRepository` |
| Dependency inversion | The panel receives its implementations at construction | `IndividualHDA(services=PanelServices(...))` |

`widgets/panel/services.py` is the composition root. It selects the existing
SideFX-based naming API, SQLite connection factory, archive transfer service,
rename adapter and Qt task owner. Callers can replace a dependency without
modifying the panel's feature methods. All panel connection creation now uses
this injected factory, including bootstrap and preference-driven initialization.

## Asset storage and Qt

`AssetStore` depends on a row-notification protocol and defaults to a silent
observer. It can be imported and used without PySide6 or Houdini. The Qt adapter
brackets shared list/table mutations with the same notifications as before.

Mutation validation happens before notifications. Negative update indexes are
rejected. Insertion no longer performs binary search over a source list whose
order might have been changed by an in-place rename. It finds the first greater
name while retaining the relative order of existing rows. As before, ID indexes
are rebuilt on structural mutation and reused for lookups.

The shared list remains exposed for compatibility with existing Qt models;
structural changes must go through the store. This is not an immutable data model.

## Rename and deletion

`build_rename_plan` validates the selected file and constructs an immutable
`RenamePlan` without changing files or database rows. Filename generation uses
the injected naming contract. The panel still uses the existing HoudiniAPI
naming implementation by default.

`rename_asset` executes the plan through a file-operation context and a narrow
rename repository. `SQLiteRenameRepository` translates the plan into the existing
asset/history SQL operations. A rejected write raises inside the transaction,
allowing file moves and database updates to roll back together. The panel updates
its presentation after the command succeeds.

Delete commands separately accept asset-deletion and history-deletion ports.
The durable journal accepts the transaction/commit-marker protocol rather than
the concrete SQLite facade. Existing recovery scope and retained copies are
unchanged; see [the recovery report](REFACTOR_2_5.md).

## Archive and read services

`ArchiveTransfer` owns staging, backup, activation and export. It does not open
file dialogs. A second import cannot overwrite an already staged operation.
The panel selects paths before dispatching worker work. `DataStream` remains a
compatibility facade for existing callers, including optional dialog arguments
and access to staging state.

`LibraryReader` returns asset/history snapshots through a read-only protocol and
closes each connection on success or failure. Category and scene-record snapshot
helpers also now close their connections explicitly.

## Task ownership

`TaskController` creates file/process jobs through replaceable factories. Active
job properties are read-only; the panel starts and stops processes through owner
methods. File operations and video encoding share the same busy gate.

Failed startup releases ownership. Duplicate/stale process completion signals
are ignored. Completion callback failures are logged and do not leave the owner
busy. Host destruction still drains file work on the GUI thread; workers never
wait for Qt widgets or HOM calls to complete.

## Validation and scope

Contract tests exercise:

- importing and using core modules with Qt/Houdini imports prohibited;
- notification ordering with a non-Qt observer;
- repository cleanup after a failed read;
- alternate naming with the real SQLite rename adapter;
- rollback of files and SQL when history mutation fails;
- substitute process completion and file startup failure;
- empty-population and unsupported-drop behavior across three Qt models.

The existing crash-recovery, proxy, model, archive and host-boundary regression
suite remains in place. Native Houdini 21.0.559 / Qt 6.5.3 smoke checks passed
for HDA export/import, original-node preservation, Unicode SQLite paths and panel
construction/shutdown after the dependency changes.

UI mixins remain event/presentation glue, and the public SQLite facade retains
its existing inheritance-based API. Generated Designer/resource files are not
restructured by this change. Some Qt callback payloads remain dynamic; this is
not a claim of complete strict typing or universal platform validation.


Latest SOLID verification: **83 tests passed** (7.78 s), Ruff lint/format passed,
mypy passed for **33 configured source files**, and `git diff --check` passed.
Native Houdini **21.0.559 / Qt 6.5.3** smoke checks passed after the dependency
changes. Interactive three-platform acceptance remains pending.


The subsequent [integrity review](INTEGRITY_REVIEW.md) shares pure path relocation
between the SQLite adapter and history model, adds deletion-reference checks to
the narrow repository contract, and verifies asynchronous completion by asset ID.
Its latest regression result supersedes the count above: **93 tests passed**,
with mypy covering 34 configured files.
