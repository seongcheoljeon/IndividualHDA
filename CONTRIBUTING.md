# Contributing

IndividualHDA is MIT-licensed. Start with a small change in one feature and keep
personal SQLite, team SQLite/PostgreSQL, saved settings, and Houdini entry points
compatible unless the change explicitly includes a migration.

## Set up a checkout

Use Python 3.11 or newer. From the repository root:

```sh
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m tools.dev_app
```

The developer panel uses the real UI and a temporary three-asset library. It does
not use your saved settings or library and deletes its samples when closed.
Houdini capture/import is unavailable; the sample HDA files are placeholders.
To check startup and shutdown headlessly, run `python -m tools.dev_app --smoke`.
Linux needs the Qt runtime libraries listed in `.github/workflows/tests.yml`.

For core-only work install `requirements-core.txt`; for server-only work install
`requirements-test-server.txt`. Neither environment requires Houdini or PySide6.
The full developer environment includes optional server/Qt test dependencies.

## Choose the change boundary

| Change | Start here | Verify |
| --- | --- | --- |
| UI controls or presentation | Owning `widgets/<feature>/layout.py`, view/presenter; panel `*Bindings` wired in `widgets/panel/composition.py` | `python -m tools.check qt`, developer panel |
| Personal data/query behavior | `libs/repository.py`, `libs/database/sqlite_repository.py`, named row converters | Relevant repository tests, Qt suite for file-journal/lifecycle cases, core suite |
| Team/server behavior | `libs/team/contracts.py`, `ihda_server/service.py` and storage adapters | Server suite, PostgreSQL suite, Qt suite for panel integration |

For a UI change, trace the control signal to its owning feature or presenter,
change that behavior there, and update its explicit binding only if it needs a new
collaborator. Preserve persisted control names. Do not add feature Mixins or
route new internal methods through `main.py`.

For a repository change, define the named input/result at the repository boundary,
implement the operation in storage, and test failures as well as commits. Keep SQL
out of panel features. Reuse transaction/journal/recovery services for file changes.
Personal storage uses sqlite3; team storage uses SQLAlchemy for both databases.

Use frozen keyword-only records from `libs/asset_contracts.py` and
`libs/scene_contracts.py`. Access `asset.hda_id`, and use
`replace(asset, hda_name="Water")` to produce an updated record. Do not pass
partial dictionaries to model stores or add positional row/key-list adapters.
Use explicit SQL projections and named bindings (`WHERE id=:asset_id`). Decode
wire/storage mappings once with `decode_record`, and use `record_document` only
when serializing. Add columns through `libs/model_columns.py`, where identity,
label and accessor are defined together. Keep legacy on-disk readers confined
to `libs/legacy_documents.py`; never make an old list shape a live API.

Browser, detail, team and scene integrations get their own bindings rather than
`IndividualHDA`. Wire new callbacks in `PanelComposition`; keep shared state in
its existing owner. Domain commands receive storage and journaling capabilities;
the SQLite adapter selects the concrete transaction and file-operation policy.


For a server change, update the shared contract and service first, then adapters.
Exercise authorization, stale revision/conflict behavior and both SQL dialects.
Do not make UI widgets part of service tests.

Houdini work belongs behind `libs/host_ports.py` and `libs/houdini_api.py`; inject
capture/callback/scene fakes through `PanelServices` in tests. Host calls run on the
GUI thread. Slow I/O goes through the existing task controllers. On library changes,
check the session identity before applying asynchronous results.

## Extension points

The code is arranged so that one kind of change touches one place. Use these
entry points instead of reaching into another module's internals:

| You want to… | Do this | Not this |
| --- | --- | --- |
| Call another panel feature from a feature | Add the member to that feature's protocol in `widgets/panel/ports.py` (drop the underscore on the method) and use it through `self.bindings.<feature>` | Call `self.bindings.<feature>._name` |
| Behave differently for personal vs team libraries | Add a method to `LibraryPort` in `widgets/panel/library_port.py` and implement it in `PersonalLibrary` and `TeamLibrary`; the composition root (`_active_library`) picks the adapter | Branch on `team.active` in a feature |
| Add a kind of library (archive, read-only mirror, …) | Write one `LibraryPort` adapter and choose it in `widgets/panel/composition.py` | Edit every feature |
| Read `hda_key` / `hda_history` rows | Filter with `rows.LIVE_ASSET_IDS` / `LIVE_HISTORY_IDS` (`libs/database/rows.py`); trashed assets keep their rows until purge | Write the `deleted_at` subquery by hand, or skip it |
| Write several rows in one storage method | `with self.transaction():` (SAVEPOINT-reentrant) and let SQLite errors propagate; the repository maps them to `LibraryError` | `try/except` + `_rollback()` around each statement |
| Add a server catalog method | Take the connection from `self.reading(project_id, user_id)` or `self.writing(...)` in `ihda_server/access.py`; reads go in `CatalogQueries`, writes in `SqlCatalog` | `self._engine.connect()` and a manual `authorize()` |
| Add a team operation | Add it to `Operation` in `libs/team/contracts.py` (the gate reads that literal), a branch in `SqlCatalog._apply` and `LifecycleStore.change_lifecycle`, and a label in `widgets/library_metadata/dialog.py:_activity`; `libs/history_activity.py` decides whether it shows as a History row | A second hand-written list of operations |
| Show something new in the History list | Build rows with `libs/history_activity.py` (`kind != "version"`); never insert into `hda_history` — the v6 trigger turns every row into a version | Synthetic history rows |
| Record an audit event on the server | `ihda_server/audit.py:record_event` | Import `LifecycleStore` from `tracking` |
| Add a widget to the main window | The page's `build_*` in `widgets/panel/layout_*.py` (or `MainWindowLayout._build_*`), declare its attribute on `MainWindowLayout`, then the feature's `*Bindings` and `composition.py` | — |
| Ask for an asset's name, category, version or change description | `widgets/registration_dialog.py:RegistrationDialog` with a `libs/registration_request.RegistrationRequest`; rules live in `registration_request.validate` | A chain of `QInputDialog` prompts or a `QMessageBox` with a checkbox |
| Change how an item looks (grid card, table row, tree badge) | Paint it in `widgets/item_delegates.py`; read roles the model already provides, take colours from `option.palette`, and start with `theme_background()` so QSS hover/selection still applies | New `FontRole`/`BackgroundRole` branches in a model's `data()` |
| Tell the user something happened | `self.bindings.presentation.notify(message, action="Undo", on_action=…, level=…)` — a toast (`widgets/toast.py`), the status bar and the log in one call; keep `QMessageBox` for questions and irreversible steps (purge, dependents) | An information `QMessageBox`, or a log line the user never sees |
| Free disk space after a purge | `ManagementGateway.reclaim(apply)`; purging only queues paths in `file_cleanup`, `libs/library_files.cleanup` deletes the unreferenced ones and empty directories | Delete files inside the purge transaction |

## Guard tests

`tests/test_architecture.py` fails the build when a rule is broken. Each counter is
"only shrinks": lowering it means you paid debt, so update the constant; raising it
is the signal to use the extension point above instead.

| Constant / test | Means | When it fails |
| --- | --- | --- |
| `test_domain_libs_have_no_qt`, `test_only_the_host_boundary_imports_hou` | `libs/` is domain code; only `libs.host`/`libs.houdini_api` import `hou` | Move the Qt/HOM use behind `libs/qt_helpers.py`, `HoudiniAPI`, or add a real Qt wrapper to `QT_LIBS` |
| `CROSS_FEATURE_PRIVATE = {}` | No feature reads another feature's `_member` through its bindings | Expose it on the port |
| `TEAM_ACTIVE_BRANCHES = 1` | Only the composition root asks whether a team library is active | Put the behavior on `LibraryPort` |
| `REPOSITORY_METHODS`, `DEAD_REPOSITORY_METHODS` | `LibraryRepository` does not grow and every method has a production caller | Add to the right role protocol (`LibraryReads` / `AssetWrites` / `SceneRecordRepository`) and call it, or drop it |
| `SOFT_DELETE_UNFILTERED` | Per-file count of raw `hda_key`/`hda_history` reads without a live filter | Use `LIVE_ASSET_IDS` / `LIVE_HISTORY_IDS` |
| `LAZY_IMPORT_SITES` | Per-module count of imports inside functions (most hide a cycle) | Break the cycle (see `ihda_server/audit.py` for the pattern) or defer only an optional dependency |
| `test_catalog_methods_cannot_bypass_project_authorization` | `catalog.py` / `queries.py` never touch the engine directly | Use `reading()` / `writing()` |
| `test_every_referenced_icon_resolves` | Every `:/…/icons/x.png` (including `libs/ui_icons.Icon`) exists in a registered resource module | Register the icon in `icons.qrc` and regenerate `icons_rc.py` |

## Checks

```sh
python -m tools.check core
python -m tools.check server
python -m tools.check qt
python -m tools.check lint
python -m tools.check all --coverage
```

`tools/test_suites.py` defines suite membership. New tests default to Qt; add
Qt-free test modules to the appropriate manifest. Shared fixtures live in
`tests/support`, not another test module. `--suite` filters before module imports,
so core/server tests can run in their minimal environments.

CI also runs the Qt suite on macOS and Windows, which local Linux runs do not
catch. Before pushing, check the usual suspects:

- Regenerate `*_rc.py` with `pyside6-rcc --no-zstd`; the macOS/Windows PySide6
  wheels cannot open zstd-compressed resources.
- Build module names from `path.parts`, not `str(path)` (backslashes).
- Compare stored paths as `Path(...)`, not as strings; SQLite rows hold POSIX text.
- Give child Pythons `-X utf8` and normalize Hangul to NFC before comparing.
- Poll for a condition instead of `qWait(fixed)`; runners are slow.
- Guard Qt wrappers with `shiboken6.isValid` after `deleteLater`.
- Always pass `encoding="utf-8"` to `read_text`/`write_text` (a guard test enforces it).
- SQLAlchemy `inspect()` in server tests needs the fixture's translated schema.

PostgreSQL checks use a **disposable test database** and may reset its tables.
Set `IHDA_TEST_POSTGRES_URL` to a `postgresql+psycopg://...` URL, then run:

```sh
python -m tools.check postgres
```

Missing PostgreSQL configuration fails this command instead of silently skipping.
CI uses the same commands and provisions PostgreSQL 16. Normal full-suite runs
without that variable skip PostgreSQL-only cases. Native Houdini validation remains
necessary for capture/import, callbacks, scene saving and display/render flags;
headless tests do not replace it.

Keep PRs focused, explain resulting behavior and list checks actually run. For a
visible UI change include an image if useful; for storage changes explain migration
and rollback implications. See [architecture](docs/ARCHITECTURE.md),
[UI editing](docs/UI_EDITING.md) and [validation history](docs/VALIDATION.md).
