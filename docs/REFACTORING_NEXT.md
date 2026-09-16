# Refactoring continuation

## Completed in the registration slice

- Personal new-registration and add-version capture share `RegistrationService`.
- Houdini calls sit behind `RegistrationCapture`; SQL stays in the existing local
  lifecycle/repository adapter. Qt confirmations/model updates remain in the panel.
- Staged capture, exclusive publication, SQL rollback/retry, preservation after an
  uncertain commit, flag restoration and overlay cleanup have regression tests in
  `tests/test_registration_workflow.py`.
- Schema and Team API/pending-command formats are unchanged.

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

## Next bounded slice

Scene-record cleanup still performs legacy UI/DB work together and needs
commit-before-display treatment. Extract its application operation and then
continue with model binding and Houdini-action adapters one responsibility at a
time. The other 12 Mixins have not all been removed.

Later: asynchronous executor lifecycle; Qt model/data conversion duplication;
remaining direct repository/public facade dependencies and type-check exclusions.
These remain after the registration, rename/Trash and composition slices.

## Operational limits

Native Houdini validation is still needed for this slice: drop a new node, add a
version, cancel an update, and verify node display/render flags and preview capture.
The agent tests use fake host adapters plus actual SQLite; they do not replace HOM
execution. Ordinary rollback supports retry; crash-resumable local registration
receipts were not introduced. Existing inspection/cleanup handles orphan detection.

Keep `widgetType__purpose` names, Python-only layouts, small focused dialogs and
SOLID boundaries. Do not create a new standalone Personal/Team workspace screen.

Additional native Houdini checks: rename an asset with historical previews, cancel
a rename, move an asset/old version to Trash, and restore through Library Tools.

For composition: open/close and recreate a Houdini panel, close during an archive
job, reload Personal/Team libraries, request an AI suggestion, and close with
Library Manager/metadata dialogs open. Check that callbacks do not fire twice.
