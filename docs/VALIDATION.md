# Validation and recovery

## Local checks

```sh
python -m ruff check .
python -m ruff format --check .
python -m mypy
python -m pytest -q
```

- Linux Python 3.11 / PySide6 6.x (offscreen): the regression suite covers schema
  upgrade, backup contents, migration rejection/rollback, quoted Unicode values,
  normalized tags, transaction rollback, archive traversal, relocation, WAL
  snapshots, import rollback, Qt model notifications, drag payloads, search,
  process failure, cancellation, playlist behavior, settings atomicity, populated
  panel startup, panel worker success/failure/deferred close with GUI-thread
  delivery, host-destruction cleanup, Library Tools service paths, AI provider
  settings roundtrip, and complete signature annotation coverage with Python 3.11
  syntax.
- Windows Houdini 21.0.559 / Python 3.11.7 / Qt 6.5.3: `hython tests/houdini_smoke.py`
  creates a temporary SOP asset, exports and reimports it, verifies original node
  identity and absence of leaked wrapper output nodes, compares versions without
  changing installed definitions, exercises SQLite/Unicode and legacy migration,
  and constructs/closes the panel and six-tab manager offscreen, including
  dark/default theme switching.
- CI also runs the suite on Python 3.12. Whether Houdini 21 ships a Python 3.12
  build has not been confirmed against SideFX's platform notes; 3.11 is the
  verified host interpreter.
- No existing user library or HIP was used for tests.

The local Qt tests run with a temporary configuration (`IHDA_CONFIG_DIR`). A
restrictive sandbox can block Qt's native audio initialization; run the UI suite
outside it in offscreen mode.

## Interactive acceptance checks still required

On each of Windows, macOS and Linux, using a disposable library and HIP:

1. Start the Python panel, choose a data folder, restart and check settings.
2. Register SOP, OBJ, VOP and subnet nodes via middle-button drag/drop. Compare
   original nodes, wires, names, flags and embedded definitions before/after.
3. Update a version; inspect history; rename, favorite, tag, edit notes, search
   names/tags/types; switch list/table/history views and remove selected rows.
4. Import old and new versions, including connected and nested nodes.
5. Capture a thumbnail and flipbook; interrupt/fail capture and verify the original
   timeline, playback range and FPS are restored.
6. Encode with FFmpeg paths containing spaces/non-ASCII characters; verify odd-sized
   frames and fractional FPS, playback, volume, seeking and all five playlist modes.
7. Import/export between OSes. Asset paths relocate; external HIP paths remain the
   original paths and require the artist's storage/mount mapping.
8. Close during encoding, metadata probes and export. Verify no orphan processes,
   thread destruction errors or partial replacement of previous videos.

Native desktop behavior and macOS execution are not established by the local
headless tests. The OS CI matrix is configured but has not been run from this workspace.

## SQLite migration and backups

The current schema version is `SCHEMA_VERSION = 4` in `libs/database_migrations.py`.
The original tables, primary keys, asset IDs, version strings and local timestamp
values remain across upgrades. Version steps: v1 indexes, trigger-maintained
`asset_tags`, favorite/load-count validation and user-scoped category cleanup;
v2 `operation_commits` for crash recovery and savepoint-based nested transactions;
v3 user predicate on the category-cleanup trigger and synced tag index; v4 removal
of redundant UNIQUE constraints, typed/constrained numeric columns (fractional FPS
preserved, zero FPS rejected) and in-place legacy table rebuilds.

An existing unversioned database is backed up next to itself as
`ihda.db.pre-v<N>-<UTC timestamp>-<unique suffix>.bak` before migration. DDL, indexes,
triggers and `user_version` advance in one transaction. Foreign-key violations
abort the upgrade; newer unsupported schema versions are refused. Migration
backups are not silently overwritten or deleted.

The default journal mode is retained for compatibility. Connections enable foreign
keys and a five-second busy timeout. Each background operation opens and closes its
own connection. Exports use SQLite's backup API so committed WAL data is included.

To restore a pre-upgrade DB, close every iHDA panel/process using it, preserve the
current database and its sidecars, and copy the desired `.bak` to `ihda.db`.
Use the old app for a true downgrade; this app upgrades older versions on reopening.

## Archive imports

Extraction occurs in a unique staging directory on the destination filesystem.
Absolute/traversal/Windows drive paths, symlinks and duplicate case-folded names
are rejected. A manifest records the original asset root; legacy archives derive
it from their stored asset paths. The staged database is migrated and checked
before the active library is touched.

Import first creates a full ZIP backup in the data folder's `backup` directory.
On panel close, file renames activate the staged database/assets. Exceptions roll
back those renames. Old assets and DB remain as `.previous-<unique suffix>` recovery
copies. These are retained intentionally and may be removed after verifying the
import. A sudden OS/process failure between filesystem renames is not a cross-file
atomic transaction; the retained ZIP and `.previous-*` files provide recovery.

For recovery, close the app, preserve all current/staged files, then restore a
matching database and asset directory from the same backup. Never mix a DB from
one backup with assets from another. Reopen and verify history and file locations.

## Scope

Houdini 21+ standard Qt 6 builds are the target; separate Qt 5 builds are excluded.
This remains a single-user library. Viewport/HOM operations deliberately execute
on the main thread. External encoders/probes use QProcess; file archives use an
owned worker and finish before panel/application shutdown. This is not a migration
to an asset server or a redesign of the UI.


## Library Tools

Service paths, staged restoration, path backups, recovery files, malformed
backups and search paging/cancellation are covered by the regression suite; see
[LIBRARY_TOOLS.md](LIBRARY_TOOLS.md) for behavior, limits and how to reproduce the
explorer measurements. Full interactive acceptance on Windows, macOS and Linux
remains pending.

## Asset browser MVP migration — 2026-09-15

Validated with Python 3.11.15 / PySide6 6.11.2 and the offscreen Qt platform:

- Full regression run: **203 passed**. The final widget naming/layout grouping
  was subsequently checked by the coverage runs below. This was the initial
  browser-only step; see the full Python-layout migration below.
- `ruff check .`, `ruff format --check .`, `mypy`, and `git diff --check`: passed.
- Coverage: **66.08% overall** (60% required), **99%** across the new browser/search
  modules; the presenter and search gateway each reached 100%.
- Coverage was collected in two runs: 202 tests with
  `-k 'not test_download_recommended_then_use'`, then that test alone with
  `--cov-append`. The unmodified AI download test intermittently failed waiting
  for its follow-up refresh during an instrumented full run, but passed alone.
  The follow-up refresh timing issue was subsequently fixed in the full layout
  migration below; no test was permanently skipped or weakened.
- Browser checks cover delayed responses, cancellation, library replacement,
  close, search errors retaining results, list/table filters and selection,
  multi-selection clicks, old splitter-state compatibility, saved zoom restore,
  and imports without Qt/Houdini/SQLite in the presenter/search contract.
- A standalone offscreen render was inspected. Real Houdini embedded/floating
  windows, native menus and Houdini drag/drop were **not run** in this environment.
- FastAPI/PostgreSQL, permissions, remote file storage and migrations are future
  work; this change only adds an injectable search boundary and local adapter.


## Full Python layout migration — 2026-09-15

- Removed all seven application `.ui` files and all seven generated layout
  modules. Runtime imports now use maintained `layout.py` modules and `build_ui()`;
  layout creation has no Designer, XML-loader or UI-compiler dependency.
- Compared the pre-migration and final layouts: **414 Qt objects** matched for
  their applicable text, tooltip, font, size constraints, size policy, control
  defaults, orientation, tab, spacing and margin properties after accounting for
  intentional descriptive layout/widget renames.
- Final full regression run, including coverage in a **single invocation**:
  **210 passed**, **68.29% overall coverage** (60% required). All seven new layout
  modules and `widgets/layout_helpers.py` reached 100% statement coverage.
- `ruff check .`, `ruff format --check .`, `mypy` and `git diff --check`: passed.
  All layout modules are included in the maintained-code checks; the old generated
  layout exclusions and compiler-drift test have been removed.
- Replaced the compiler test with runtime construction, dialog accept/reject,
  tab/menu/embedding contracts and a check that application Designer sources do
  not return. Existing populated-panel, settings and optional-media tests passed.
- Fixed the AI dialog follow-up refresh race found during repeated coverage runs:
  download/delete completions request refresh at `TaskController.idle`, after the
  previous worker is released. Four deterministic cases cover completion arriving
  before worker termination and closing before idle for both operations.
- Houdini's `hou` module is unavailable in this environment. Real host embedding,
  native drag/drop, menus and visual acceptance still require a Houdini session.
- Screen locations, naming rules and the direct-code editing workflow are in
  [UI_EDITING.md](UI_EDITING.md).

## Feature presenters and metadata saves — 2026-09-15

Extended the code UI migration with presenters for metadata editing, lifecycle
commands, media metadata, history dates, detail display and dialog policies.
Existing Qt models, host callbacks and local transaction/recovery services remain
in their adapters. No FastAPI/PostgreSQL server was introduced in this change.

Validation:

- Full suite: **247 passed in 46.49 seconds**.
- Coverage: **69.90%** across libs/model/view/widgets/main/public/ui_settings;
  required minimum is 60%.
- Ruff check and format check passed (192 maintained Python files).
- mypy passed (156 source files); no additional ignore overrides were introduced.
- `git diff --check` passed.

Tests cover delayed metadata completion after selection changes, newer edits made
while saving, error/retry, library replacement, deleted assets, rejected submissions,
and retaining drafts on same-library preference changes. Real panel save buttons
persist notes/tags through a TaskController and SQLite and update shared models.
Reload tests reject results captured before a write or from another repository.

Lifecycle tests exercise registration, version creation, protected latest history,
rename and deletion against a temporary SQLite library. Command/media tests verify
that storage failures do not publish UI updates. Dialog tests verify that invalid
inputs do not emit accepted, including the actual button-box path. Additional
checks cover immutable detail records, missing thumbnails, history date validation,
stale explorer pages, AI action availability, and host-scaled web zoom.

Empty tag saves now create a valid empty tag value and return an empty list on
asset/history reads. Missing/deleted-asset writes report failure. Presenter imports
are checked for Qt/Houdini/main/concrete-database dependencies.

The user confirmed the preceding Python-layout migration runs in Houdini. This
follow-up was validated with offscreen Qt and local SQLite; native Houdini checks
for registration, rename/delete, note/tag saves and preview capture are still needed.
Drafts are retained in memory during a panel session; they are not restart recovery.

## Personal / Team workspace — 2026-09-15

Verified locally on Linux / Python 3.11 with offscreen Qt:

- Full suite, including the server: **273 passed**, **70.38% coverage** (60% gate).
- Actual PostgreSQL 16.15: shared backend/HTTP/workspace tests **25 passed**.
  A preceding combined architecture/Qt/PostgreSQL run passed **44 tests**.
- CLI initialization, user/project creation, token issuance, production
  `create_app` startup and token revocation passed against the temporary PostgreSQL DB.
- Ruff check and format: **214 files**; mypy: **175 source files**; `git diff --check` passed.
- `docker compose config --quiet` passed. Image build/container execution was not
  tested because this environment has no running Docker daemon.
- Two upstream TestClient deprecation warnings remain (httpx and BlockingPortal).

The real HTTP fixture runs Uvicorn in a separate process, matching deployment.
An earlier in-process server thread caused WebEngine garbage collection on the
wrong thread and exited with code 133 in the full suite. Process isolation fixed
that test interaction; the full suite above completed after the fix.

```sh
QT_QPA_PLATFORM=offscreen QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu \
  python -m pytest -q \
  --cov=ihda_server --cov=libs --cov=model --cov=view --cov=widgets \
  --cov=main --cov=public --cov=ui_settings --cov-fail-under=60
```

The tests use disposable databases/files and loopback HTTP. They do not establish
acceptance of the new workspace's native Houdini capture/thumbnail/import flow,
Windows/macOS behavior, or a deployed HTTPS proxy. Those checks remain manual/CI
follow-up. See [TEAM_LIBRARY.md](TEAM_LIBRARY.md) for setup, scope, backup and retry
procedures. The temporary PostgreSQL process was stopped after validation.

## Main-panel personal/team integration — 2026-09-15

This supersedes the separate workspace UI described in the preceding validation.

- Full suite: **275 passed**, **70.17% coverage**, including the server (60% gate).
- Actual PostgreSQL 16.15: **26 passed** across backend, presenter and main-panel integration tests.
- Ruff check / formatting: **222 files**; mypy: **182 source files**; diff whitespace check passed.
- The main-panel test verifies widget reuse, personal draft/database preservation,
  remote note saves off the GUI thread, note search, history rendering, conflict
  comparison, read-only role controls, failed source changes and stale personal AI replies.
- Connection settings require a verified project and do not persist credentials.
- The thumbnail resolver test verifies lazy file resolution outside the GUI thread.
- Rendered and inspected the main panel offscreen. No separate asset workspace is created.
- Full-suite Qt cleanup now retires each finished test's leftover windows using
  deferred deletion on the GUI thread, then collects Python wrappers. Collecting
  wrappers before retiring their native windows caused a segmentation fault;
  leaving them for an HTTP worker caused WebEngine thread-affinity failures.
  The complete suite above passed with the final cleanup ordering.
- Two upstream TestClient deprecation warnings remain. Native Houdini drag/drop,
  node capture and imports still require host acceptance testing. The test-only
  PostgreSQL process was stopped after verification.

## 2026-09-15 — Library metadata and lifecycle v2

- Full regression suite: **291 passed**, coverage **70.21%** (required 60%).
  Log: `/tmp/ihda-v2-verified-full.log`.
- Actual PostgreSQL 16 integration/contract tests: **41 passed**, including the v1→v2
  upgrade, personal preferences, idempotent usage, trash/restore and shared-file cleanup.
  Log: `/tmp/ihda-v2-verified-pg.log`.
- Final dialog shutdown/menu changes: **22 UI/architecture tests passed**.
  Log: `/tmp/ihda-v2-ui-final.log`.
- Ruff check and format: **237 files** passed. Mypy: **194 source files** passed.
  `git diff --check` passed.
- Qt offscreen rendering of Version details inspected (`/tmp/ihda-version-details-v2.png`).
- Added tests for rollback/retry of personal migrations, legacy pending preservation,
  trash-containing backup validation, and retained integrity hashes after description edits.
- Corrected archive relocation to snapshot paths before preview synchronization triggers run;
  controlled maintenance can relocate trashed metadata without enabling ordinary edits to Trash.
- Test-client dependencies still emit two upstream deprecation warnings.

Native Houdini acceptance remains manual: restart Houdini, register/update a personal HDA with
an optional version description, drag/import from Personal and Team, verify per-user favorites,
move an old version and an asset to Trash, restore them, and verify HDA files remain importable.
Confirm that closing a metadata dialog or destroying the panel drains its background work.
Existing real libraries/production servers were not upgraded during development; temporary
SQLite databases and isolated PostgreSQL schemas were used for validation.

## 2026-09-15 — Personal → Team copy

The user confirmed native Houdini validation of the preceding metadata/lifecycle work.
This follow-up adds the copy workflow without a schema migration.

- Full regression suite: **303 passed**, coverage **70.52%** (required 60%).
- PostgreSQL integration group: **53 passed**. After the final capability guard,
  UTF-8 transport and UI refinements, copy/transport contracts were rerun against
  PostgreSQL: **29 passed**.
- Ruff check/format: passed (**245 files**); mypy: **201 source files**, passed.
- Copy coverage includes read-only source preservation, multiple versions, Unicode
  notes/tags, source provenance and new destination UUIDs, independent preferences,
  current-only copies, optional missing previews, required missing HDA rejection,
  repeated legacy labels, cancellation, source content changes, partial upload
  resumption, lost commit replies with deleted source files, atomic rollback,
  missing blob repair, viewer rejection, Trash conflicts, concurrent copying by
  different users, and dialog shutdown with a running upload.
- Offscreen Qt preview/copy and worker ownership tests passed; the copy dialog was
  rendered and visually inspected. Tests used disposable SQLite/PostgreSQL data.
- Two upstream TestClient deprecation warnings remain.

New native acceptance scope: select a personal HDA → Copy to team… → choose a
project → Preview → Copy, then open the project and import the copied current and
historical versions. Confirm thumbnail/video playback and that the personal
library remains unchanged. This new copy flow has not been run in native Houdini
by the agent; the user's preceding host validation covers the earlier work.

## 2026-09-15 — Team backup and isolated restore

- Full regression suite: **316 passed, 1 skipped**, coverage **70.52%**.
  The skipped pg_dump/pg_restore test requires an explicit PostgreSQL test URL;
  it was run successfully in the separate integration job below.
- PostgreSQL 16 integration group: **52 passed**. Final dedicated backup tests:
  **14 passed**, including a real pg_dump/pg_restore round trip.
- Ruff check/format: **251 files**, passed. Mypy: **206 source files**, passed.
- Actual restore retained Unicode notes, Trash, preferences and token authentication;
  a subsequent registration proved sequence values support new writes. A project
  created after snapshot export was absent from the restored snapshot, as intended.
- Failure tests cover missing/corrupt/unlisted files, omitted inventory entries,
  traversal, incomplete manifests, symbolic links, failed dump publication,
  restore comparison failure, existing-target rejection and competing storage locks.
- A subprocess blocked all Qt/Houdini imports and successfully ran offline backup
  verification and the server storage lock. Password transport uses a temporary
  protected pgpass file; tests assert passwords are absent from process arguments
  and the file is removed afterwards.
- Compose configuration validation and CLI help passed. The Docker daemon is not
  available in this environment, so building/running `deploy/Admin.Dockerfile`
  remains an operator acceptance check. Native PostgreSQL 16 client tools were
  exercised directly for the integration tests.
- Tests used disposable files, databases and schemas. No existing personal library,
  production DB, deployment configuration or scheduled job was activated.

Before deployment, build the admin image, create a backup on the intended volume,
run verify-backup, and restore into a new empty UTF-8 DB and absent blob path. Use
an isolated API instance to verify browsing/downloading before any production
configuration switch. PostgreSQL roles, TLS and host storage backups remain separate.

## 2026-09-15 — Core class and policy refactoring

- Full suite: **325 passed, 1 skipped**, coverage **70.68%**. The PostgreSQL-only
  backup round trip skipped in the default run passed in the integration group.
- Final PostgreSQL integration group: **76 passed**, including copy, restore,
  migration and main-panel integration. A discovered import error in the local
  management adapter was fixed before this final successful run.
- Ruff check/format: **259 files**, passed. Mypy: **213 source files**, passed.
- New tests cover immutable file-content equality/hash behavior across renames,
  preserved Blob wire fields, empty-file cancellation, invalid policy rejection,
  applied HTTP response limits and SQLite lock timeout, in-memory journal replay
  after a lost reply, and the copy workflow's concrete-adapter import boundary.
- Existing tests verify API v2 endpoints, pending request fingerprints, copy-journal
  and backup formats, source preservation, cached downloads, and Qt dialog ownership.
- Scope: shared file integrity, copy service/adapters, HTTP/DB resource policies and
  shared protocol/audit limits. Native Houdini interaction was not rerun by the agent.
  Main-panel/UI class restructuring and search scalability remain separate work.

## Panel state / session refactoring — 2026-09-15

Final validation after selection/details dispatch, reload lifecycle, library session
ports, Team history guards, and shared UI defaults:

- Full offscreen suite with coverage: **335 passed, 1 skipped**, **70.93%** coverage
  (required minimum 60%). The optional PostgreSQL backup round-trip is skipped
  without its environment; this change does not modify server backup code.
- PostgreSQL 16 run of `test_main_team.py`, `test_panel_refactoring.py`, and
  `test_architecture.py`: **19 passed**. Team connection, writes, history failure /
  retry, refresh while viewing history, and return to Personal use the existing UI.
  Disposable test resources were cleaned and the temporary PostgreSQL server stopped.
- Ruff check and format: **264 files**; mypy: **217 source files**; diff whitespace
  checks passed. Two existing upstream TestClient deprecation warnings remain.
- Selection checks cover complete field refresh after rename/version changes,
  historical version identity, deleted selections, and both list/table Qt indexes.
  Lifecycle checks cover rejected/busy submissions, saves invalidating snapshots,
  library changes, A → B → A selection changes, empty history and closed presenters.
- Architecture checks restrict shared-state analysis to composed Mixins (independent
  presenters may use the same private field names), prohibit direct UI writes to
  selection fields, and keep the new presenters free of Qt/storage/HTTP imports.

Logs: `/tmp/ihda-panel-final-full.log`, `/tmp/ihda-panel-final-postgres.log`.
Native Houdini execution was not available in this agent environment; the user's
previous Houdini check predates this refactoring.

## Local registration service — 2026-09-15

- Targeted registration/repository/presenter/host-boundary/architecture suite:
  **62 passed** (`/tmp/ihda-registration-tests-final.log`).
- Full offscreen suite: **347 passed, 1 skipped**, **71.12%** coverage
  (`/tmp/ihda-registration-full.log`). The optional PostgreSQL backup test is
  skipped without its configured database; no server/schema changes were made.
- Ruff check/format: **267 files**, mypy: **219 source files**, diff checks passed.
  Two existing upstream TestClient deprecation warnings remain.
- New failure tests exercise partial HDA/thumbnail capture, competing publication,
  SQL history insertion rollback for new registration and version addition, retry
  without duplicate history, uncertain/postcommit failures, optional thumbnails,
  flag/overlay restoration and successful commit followed by failed display update.
- Native Houdini execution was not available. Follow-up host checks and remaining
  refactoring scope are recorded in `docs/REFACTORING_NEXT.md`.

## Rename and Trash orchestration — 2026-09-15

- Final full offscreen regression suite: **360 passed, 1 skipped**
  (`/tmp/ihda-mutations-final.log`). Two existing TestClient deprecation warnings.
- Focused mutation/registration/presenter/recovery/architecture tests: **81 passed**
  (`/tmp/ihda-mutations-targeted-final.log`). Proxy ordering tests: **18 passed**
  (`/tmp/ihda-mutations-proxy.log`).
- Ruff check/format: **269 files**; mypy: **220 source files**; diff checks passed.
- Coverage instrumentation reached **72.01%** before adapting the legacy proxy
  test fixture to ID-based deletion. Application sources were unchanged between
  that coverage run and the final successful full regression run.
- New regressions cover rename SQL failure and journal rollback, invalid names,
  mixed successful/failed asset deletion, current-version protection, Trash audit
  failure rollback, note/file retention, row identity after proxy reorder, committed
  display failures and rename-overlay cleanup.
- The optional PostgreSQL backup test remains skipped without its configured DB.
  This slice changes local application/UI orchestration, not server/schema formats.
- Native Houdini execution was unavailable; host follow-up steps and remaining
  refactoring are documented in `docs/REFACTORING_NEXT.md`.

## Main-window composition and lifecycle — 2026-09-15

- Full final offscreen suite: **369 passed, 1 skipped**, **72.26%** coverage
  (`/tmp/ihda-composition-full-final.log`). The optional PostgreSQL backup test is
  skipped without its configured DB; two upstream TestClient warnings remain.
- Final focused panel/Team/startup/architecture/sync suite: **37 passed**
  (`/tmp/ihda-composition-targeted-final.log`).
- Ruff check/format: **273 files**; mypy: **223 source files**; diff checks passed.
- New regressions cover acquired-resource cleanup after startup failure, ordered
  shutdown, failed-worker retry, duplicate ownership, failed import activation,
  closing-state preservation, already-deleted dialogs and reentrant close events.
- Bootstrap, archives, AI and sync no longer appear in the panel's Mixin bases.
  The shared-state ratchet dropped `_library` and `_repository`; four extracted
  adapter modules no longer use mypy's `ignore_errors` override.
- Native Houdini validation remains outstanding for this slice. Reopen panels,
  close during archive work, reload libraries, use AI and close with tool dialogs
  open as listed in `docs/REFACTORING_NEXT.md`.

## Named data and operational policies — 2026-09-16

- Final full offscreen suite: **383 passed, 1 skipped**, **72.57%** coverage
  (`/tmp/ihda-named-full-final.log`). The optional PostgreSQL backup test is
  skipped without its configured DB; two existing TestClient warnings remain.
- Focused named-data/browser/optional-media/repository/schema/registration suite:
  **59 passed** (`/tmp/ihda-named-targeted-final.log`).
- Ruff check/format: **280 files**; mypy: **229 source files**; diff checks passed.
- New tests reverse SQL result projections for assets/history/scene records, check
  duplicate aliases and missing fields, preserve connection cursor behavior,
  validate legacy row lengths, and ensure UI insertion does not mutate input.
- Nullable paths/icons/tags, Unicode paths, reordered mapping inputs, custom
  SQLite/search/polling/archive limits, rejected policy values, and page selection
  after reordering are covered. Existing defaults and schema/wire formats remain.
- Native Houdini execution was not available. Verify asset/history/detail page
  switching, registration/version addition, scene-record display, archive import
  and Personal/Team reload in Houdini before deployment.

## Version tracking and registration recovery (2026-09-16)

- Full offscreen suite: **399 passed, 2 skipped**, coverage **72.52%** (60% gate).
  The skips require the PostgreSQL backup fixture and are exercised separately.
- Actual PostgreSQL 16 suite: **69 passed**. Coverage includes v1/v2 → v3 migration, project/role isolation,
  idempotent checks and scene reports, concurrent catalog commands, copy provenance,
  and real `pg_dump`/`pg_restore` plus legacy-v2 inventory compatibility.
- Regression tests cover unique-only v5 scene backfill, ambiguous preservation,
  cross-asset current-pointer rejection, activity/current-version separation,
  dependency rename/purge retention, independent scene-version updates, durable
  outbox retries, imported check provenance, local/Team lost-response recovery,
  publication conflicts and preservation of replaced symlinks.
- Additional focused checks after the full run cover copied-check validation,
  recovery labels, and older-server copy payloads. Qt details/recovery actions use
  offscreen widgets; no native Houdini execution was performed.
- Ruff check/format: **294 files**. Mypy: **242 source files**. No new type-ignore
  exclusions were added. `git diff --check` passed.

Logs: `/tmp/ihda-tracking-all-verified.log`, `/tmp/ihda-tracking-pg-last.log`,
`/tmp/ihda-tracking-copy-validation.log`, `/tmp/ihda-tracking-recovery-labels.log`,
`/tmp/ihda-tracking-copy-compat.log`, `/tmp/ihda-tracking-types-final-result.log`.

Native Houdini follow-up: register/add a version; import Personal/Team/history
assets; save an untitled scene and allow the next sync pass; disconnect/reconnect
and retry scene delivery; exercise Pending registrations after an interrupted
capture/upload; close a panel while recovery is running. External deployment and
production database migration were not performed.

## Runtime preferences and committed scene-record cleanup — 2026-09-16

- Baseline: **402 passed, 2 skipped** on Python 3.11.15 / PySide6 6.11.2.
- Final full offscreen suite with an isolated PostgreSQL 16.15 server and real
  `pg_dump`/`pg_restore`: **416 passed, no skips**, **73.96% coverage** (60% gate).
  The two existing upstream Starlette/TestClient deprecation warnings remain.
- Ruff check and format verification passed for **304 Python files**; mypy passed
  for **250 source files**, and `git diff --check` passed. No type-check exclusion
  was added. The direct panel DB-call ratchet shrank to the Houdini-actions module.
- New regression checks cover malformed/legacy runtime settings, atomic save
  failure, Cancel/reset, snapshot application after reopening, explicit dependency
  overrides, real Qt timer values, request limits/offsets/labels, custom media
  timeout and image decode size, and node-batch confirmation limits.
- Scene-record checks exercise actual SQLite deletion, sorted/filtered parent ID
  collection, partial failures, inaccessible files, original-file preservation,
  post-commit display recovery and model reset during the confirmation dialog.
- Expanded Preferences was rendered and inspected offscreen. Content now scrolls
  while confirmation buttons remain visible; the small-screen behavior has a Qt
  regression test. Runtime defaults and retained constants are documented in
  [RUNTIME_SETTINGS.md](RUNTIME_SETTINGS.md).
- PostgreSQL CI now includes the version-tracking regression module. Deployment
  images include root license and third-party notices; images were not built in
  this environment because the Docker daemon was unavailable.
- Native Houdini 21.0.559 startup was attempted through the installed Windows
  `hython.exe`. It exited with code 3 because all usable licenses were in use,
  before the smoke script could run. Interactive HOM/drag/drop and native window
  acceptance remain pending; no production library or active Houdini scene was
  used. The isolated PostgreSQL test server was stopped after verification.

Logs: `/tmp/ihda-baseline.log`, `/tmp/ihda-final-targeted.log`,
`/tmp/ihda-record-confirmation.log`, `/tmp/ihda-runtime-verified.log`.

## Contributor-oriented composition — 2026-09-16

- Final full offscreen suite with isolated PostgreSQL 16.15 and actual
  `pg_dump`/`pg_restore`: **422 passed, no skips**, **74.76% coverage** (60% gate).
  Two upstream Starlette/TestClient deprecation warnings remain. The initial
  PostgreSQL-only run needed `IHDA_PG_BIN`; the final run supplied it and passed
  the actual snapshot/restore test. `git diff --check` also passed.

- Removed the remaining 12 panel feature Mixins; explicit frozen bindings wire
  composed features. Session, selection, models and shutdown state have named
  owners. Repository scene operations and injectable callback/capture/scene ports
  keep storage and host work at their boundaries.
- Production imports no longer use `public`; it remains available for external
  compatibility. All maintained application and developer-tool modules participate
  in mypy. Only generated resource modules retain exclusions.
- Added isolated core/server collection, shared test support, a disposable sample
  panel, the local/CI check command, contributor guide and PR template.
- Minimal core environment without PySide6: **38 passed**. Minimal server
  environment without PySide6: **28 passed, 2 PostgreSQL cases skipped**; three
  personal contract cases are assigned to Qt. PostgreSQL coverage is verified in
  the full environment separately.
- Contributor entry point, generation-based stale AI result rejection, injected
  capture failure cleanup and architecture checks: **21 passed**. Adapted feature,
  host, media, named-data, registration and runtime-settings checks: **57 passed**.
- Ruff check/format: **320 files**; mypy: **260 source files**, all passed.
- Native Houdini 21.0.559 `hython.exe` was attempted. It exited with code 3 before
  running the smoke script because all usable licenses were in use. Interactive
  capture/import, callbacks and native host UI acceptance remain unverified in
  this run. No production library or active Houdini scene was used.

Logs: `/tmp/ihda-core-isolated-final.log`, `/tmp/ihda-server-isolated.log`,
`/tmp/ihda-contributor-specific.log`, `/tmp/ihda-adapted-tests.log`,
`/tmp/ihda-lint-final2.log`, `/tmp/ihda-contributor-houdini.log`.

Final full-suite log: `/tmp/ihda-contributors-final.log`. The temporary PostgreSQL
server was stopped after verification. Windows/macOS CI and interactive Houdini
acceptance were configured/documented but were not executed locally.

## Named records and explicit dependencies — 2026-09-16

- Final full offscreen suite with isolated PostgreSQL 16.15 and actual
  `pg_dump`/`pg_restore`: **434 passed, no skips**, **75.75% coverage** (60% gate).
  Two upstream Starlette/TestClient deprecation warnings remain.
- Minimal core environment without PySide6: **47 passed**. Minimal server
  environment: **28 passed, 2 PostgreSQL cases skipped, 3 personal cases
  deselected**. PostgreSQL behavior is covered by the full run above.
- Ruff check and format verification passed for **323 Python files**; mypy passed
  for **262 source files**, without new exclusions. `git diff --check` passed.
- Regression checks cover reordered SQL projections, named connection endpoints,
  strict immutable record decoding, drag payload round trips, added registration
  job columns, scene renaming across versions, and idempotent local scene delivery.
- Recovery checks cover historical version 1 registration receipts and move
  journals, version 2 named documents, unchanged retry fingerprints, and rollback
  after capture/file-operation failures. Existing database and HTTP versions
  remain unchanged; internal Python record APIs intentionally changed.
- Architecture checks enforce explicit integration bindings, Qt/storage-free
  domain contracts, centralized model column definitions, and removal of the
  positional row facade. Developer-panel smoke coverage passes in the full suite.
- Native Houdini 21.0.559 `hython.exe` exited with code 3 before running the smoke
  script because all usable licenses were in use. Interactive capture/import,
  native callbacks and host UI acceptance remain unverified. No production
  library or active Houdini scene was used. The temporary PostgreSQL server was
  stopped after verification.

Logs: `/tmp/ihda-dependency-final.log`, `/tmp/ihda-core-dependency-final.log`,
`/tmp/ihda-server-boundaries.log`, `/tmp/ihda-validation-static.log`,
`/tmp/ihda-houdini-boundaries.log`.
