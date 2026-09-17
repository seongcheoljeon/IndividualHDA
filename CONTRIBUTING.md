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
