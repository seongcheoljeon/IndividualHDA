# Refactoring continuation

## Open: SVG icons (needs assets)

The UI modernization (Unreleased in CHANGELOG) stopped short of the icon set:
the 96 PNG icons stay until someone adds the Apache-2.0 Material SVGs and their
license file and confirms Houdini's bundled Qt lists `svg` in
`QImageReader.supportedImageFormats()`. The procedure is in
`docs/UI_EDITING.md` ("아이콘을 SVG로 바꾸려면"). The hover/checked colours of
the Houdini theme already follow the host palette (`ui_settings.py`), so the
theme side needs no further change for that step.

## Completed in the registration slice

- Personal new-registration and add-version capture share `RegistrationService`.
- Houdini calls sit behind `RegistrationCapture`; SQL stays in the existing local
  lifecycle/repository adapter. Qt confirmations/model updates remain in the panel.
- Staged capture, exclusive publication, SQL rollback/retry, preservation after an
  uncertain commit, flag restoration and overlay cleanup have regression tests in
  `tests/test_registration_workflow.py`.
- This earlier slice kept the schema unchanged; version tracking below adds v6/v3.

## Completed in the rename / Trash slice

- Shared rename validation now lives in `libs/asset_names.py`; application-service
  validation runs before the existing journaled file/SQL rename.
- Asset/version UI removal and selection updates happen only after commit. Mixed
  failed/successful deletions retain failed records; postcommit display errors
  report the committed state and request reload.
- Bulk history menus share an adapter, retain note history/files and skip current
  versions. Physical purge is still an explicit separate maintenance operation.
- Regression tests: `tests/test_mutation_workflow.py`, including SQL rename rollback,
  Trash audit failure, partial batches, note preservation and overlay cleanup.

## Completed in the main-window composition slice

- `main.py` delegates construction to `PanelComposition` and close policy to
  `PanelShutdown`; `PanelLifetime` closes acquired resources in dependency order.
- Bootstrap, AI, archives and library sync are composed adapters, reducing panel
  feature Mixins from 16 to 12. Existing callers use explicit forwarding methods;
  there is no dynamic method injection or attribute fallback.
- Startup failure cleans acquired resources. Failed close keeps the window in
  closing state; retry skips resources already closed. Running archive jobs still
  defer all teardown. Successful import activation is not repeated on retry.
- The four extracted modules are no longer excluded from mypy checking. Remaining
  shared window references are an explicit adapter boundary, not fully typed ports.

## Completed in the version tracking slice

- Personal schema v6 and Team schema v3, retaining Team API v2.
- Stable version dependencies, manual check/correction audit, scene outbox, and
  current-version validation; unique-only migration of legacy scene links.
- Durable registration capture/publication/receipt recovery, existing-menu dialogs,
  dependency warnings, and copy/backup preservation with source provenance.
- Remaining host validation: import Personal/Team/history assets, save an untitled
  scene, retry after disconnection, and close with recovery work in progress.

## Next bounded slice

Named-data/constants follow-up completed: runtime catalog/history/scene queries
and lifecycle/management reads use names; positional compatibility lives in one
adapter module. Internal registration and scene UI payloads are named. Page
selection and presentation widths have explicit owners, and panel/search/SQLite/
archive policies can be injected. Schema, Team wire formats and defaults are
unchanged. Scalar queries, historical migrations and published legacy tuple/list
returns intentionally retain positional contracts.

Scene-record cleanup now uses a Qt/HOM-free application operation and applies
only committed IDs to the view. Stable source-tree ID collection handles filtered
and sorted parent selections; inaccessible paths are retained. Runtime settings
and constant ownership are documented in `RUNTIME_SETTINGS.md`.

Contributor refactoring removes the remaining 12 Mixins and replaces them with
composed features and explicit bindings. Repository scene operations, injectable
host ports, isolated suites and a sample developer panel are now implemented.
See `CONTRIBUTING.md` and `ARCHITECTURE.md` for the current extension points.

Future work can further split the screen integration adapters as their UI grows.
Do not reintroduce shared Mixins, runtime public-facade imports or maintained-module
type-check exclusions. A plugin system is not needed for ordinary contributions.

## Completed in the SOLID audit slice (2026-09)

- Trashed assets no longer leak into tags, icons, thumbnails or the category tree;
  the live-row filter is one constant. Note/tag/registration writes and the
  multi-statement writers run in transactions. Empty categories disappear.
- Panel features talk through `widgets/panel/ports.py`; the personal/team split is
  behind `LibraryPort`. `LibraryRepository` is three roles; dead methods are gone.
- Item models stop stat()ing files and mutating rows while painting.
- Server: reads/writes through `ProjectAccess`, `CatalogQueries` split from
  `SqlCatalog`, `audit.py` breaks the tracking cycle, per-row queries batched,
  indexes + schema 4, events paging, REPEATABLE READ on PostgreSQL listings.
- `AssetsOperations` split (metadata/media), main-window pages build in their own
  modules, `PersonalCatalog` removed, shared icons/timestamps/headers named once.
- Purge offers to free the queued files and empty directories.
- Six only-shrink guards in `tests/test_architecture.py` (see CONTRIBUTING.md).

## Completed after the audit slice

- Optional collaborator members are declared on their protocols
  (`show_failure`, `asset_committed`, `inspects_files`/`inspect`, `last_timings`).
- File kinds, tracking pages and the AI backend kind are `Literal` types with
  validation at the boundaries where text arrives.
- Sixteen unreferenced definitions removed; entry points called by name
  (pypanel, Qt overrides, urllib hooks) stay.
- Every raw `hda_key`/`hda_history` read filters trashed rows or says why not in
  the SQL; the counter is `{}`.
- `TaskController` queues a start requested from a completion callback.
- Team operations are handlers in `ihda_server/operations.py`; `_apply` loads,
  persists and audits.
- `HoudiniAPI` is a facade over `libs/houdini/{session,nodes,editor,assets}.py`.
- Purge offers to free queued files and the directories they leave empty.

## Next bounded slice

Nothing from the audit remains. Candidates when their area grows: split
`VideoPlayer`, `PanelSelection`, `PreferenceLayout` and `MainLibraryIntegration`
the way the main-window layout was split; move model resets to row operations
where selection state matters.

## Operational limits

Native Houdini validation is still needed for this slice: drop a new node, add a
version, cancel an update, and verify node display/render flags and preview capture.
The agent tests use fake host adapters plus actual SQLite; they do not replace HOM
execution. Durable local/Team registration retry is now implemented; incomplete
captures and uncertain file ownership still require review in Library Tools.

Keep `widgetType__purpose` names, Python-only layouts, small focused dialogs and
SOLID boundaries. Do not create a new standalone Personal/Team workspace screen.

Additional native Houdini checks: rename an asset with historical previews, cancel
a rename, move an asset/old version to Trash, and restore through Library Tools.

For composition: open/close and recreate a Houdini panel, close during an archive
job, reload Personal/Team libraries, request an AI suggestion, and close with
Library Manager/metadata dialogs open. Check that callbacks do not fire twice.
