# Runtime settings and constant ownership

Preferences → **Performance and connections** contains optional tuning controls.
Save with OK, then close and reopen the panel to apply them. Running jobs and open
connections keep the settings with which they were created. The content scrolls while OK/Cancel remain visible on smaller screens.
Cancel discards edits;
**Restore performance defaults** changes only this group until OK is pressed.

| Setting | Default | Allowed values |
| --- | --- | --- |
| Browser/history search delay | 200 ms | 1–5,000 ms |
| Library Tools Explorer search delay | 250 ms | 1–5,000 ms |
| Library refresh interval | 10 seconds | 1–300 seconds |
| Team request socket timeout | 30 seconds | 1–300 seconds |
| Team request page size | 100 assets | 1–200 assets |
| Explorer page size | 200 assets | 1–1,000 assets |
| Maximum registration/import batch | 30 nodes | 1–100 nodes |
| Batch confirmation threshold | 10 nodes | 1–maximum batch |

Browser/history debouncing retains the existing immediate-search behavior for small
libraries. The refresh interval controls Personal-library change polling; Team
reload behavior is unchanged. A socket timeout is not a deadline for a complete large-file transfer.
Team page size controls each metadata request, not the total number of assets
shown: the main browser continues fetching all pages. Previously the main Team
adapter always fetched 200 rows per request even though the catalog/presenter
default was 100; it now follows the shared 100-row default and the preference.
Explorer fetches one page at a time and its button and end-of-results status use
the configured size. Team node batches now use the same limit and confirmation
policy as Personal batches.

## Persistence and injection

Values are stored in the `runtime` object in the existing `preference.json` under
the user's configuration directory. No new environment variables, database schema,
server settings or credentials are introduced. Existing unknown JSON keys survive
saving. Older files without this object retain previous defaults.

Missing keys use defaults. Wrong types (including booleans), non-integers and
out-of-range values fall back per field and are logged. An inconsistent batch pair
falls back together. UI relationship errors prevent saving; settings writes use
the existing atomic replacement mechanism. A malformed entire JSON file follows
the existing recovery behavior in `libs.settings_store`.

`RuntimeSettings` is pure Python. `PanelServices.from_saved_settings()` reads it
once and assembles the panel policies. Supplying `PanelServices` explicitly bypasses
that loading; supplied dependencies and policies remain authoritative. Child
dialogs receive the panel's snapshot, not a fresh read of a possibly newer file.

## Audit decisions

| Area / locations | Ownership and decision |
| --- | --- |
| About, `libs.keys.Value`, FastAPI version | `libs.app_metadata.VERSION`; packaging metadata and runtime agreement tested; API and DB versions remain independent |
| Ollama backend, model manager and settings hints | `libs.ai_defaults`; user endpoint/model continue to override defaults; recommendation content unchanged |
| Team catalog, personal adapter, tracking and HTTP contracts | `libs.search_limits`; shared page maximum and query length; not user-adjustable server limits |
| Explorer, browser query results | Separate page/result bounds in `libs.search_limits`; do not equate different limits merely because numbers coincide |
| Search, refresh, node batches | `RuntimeSettings` defaults and existing `SearchPolicy` / `PanelPolicy`; no separate persisted global state |
| Team socket timeout, Copy to Team | Runtime snapshot passed to connection dialogs and `HttpTransport`; positive finite timeout validation |
| Deferred callbacks | `CallbackPolicy.retry_delay_ms`; zero-delay Qt dispatch retains its event-loop semantics |
| Media inspection | `MediaPolicy` passed to synchronous ffprobe and the video player's asynchronous process jobs |
| Thumbnails | `ThumbnailPolicy` supplies entry/byte budgets, decode edge, worker count and pending request count; explicit legacy constructor overrides still work |
| Model/display columns and dragging | Stable `IntEnum` identities in `libs.model_columns`; shared by models, history/table proxies, drag compatibility names and width/resize bindings |
| Shared toolbar icons | Existing `widgets.ui_tokens`; screen-specific geometry and different semantic roles remain local |
| Paths, product links | Existing environment/path owner retained; historical Houdini preference fallback and product metadata named centrally; unique site destinations remain local |
| SQLite, PostgreSQL, archives, HTTP response/upload caps | Existing owning policies/constants retained; not added to Preferences |
| Historical migrations, saved keys, Qt roles, HDA formats | Fixed compatibility contracts retained; no renumbering or bulk string replacement |
| Generated Qt resources, test fixtures, samples | Not subject to mechanical constant extraction; distribution images include license notices |

Ordinary indices, arithmetic identities, Qt sentinel values and single-purpose
strings are intentionally not all wrapped in constants. New configurable values
must reach their consumer and be tested with a non-default value; a named constant
alone does not establish a usable configuration boundary.

## Scene-record cleanup

Personal scene-record selection collects stable IDs from the source tree before
opening confirmation, including children of a selected parent. A model reset in
the confirmation event loop cannot change the deletion target. Both explicit deletion and missing-file cleanup use
`SceneRecordCleanup`. Each successful database deletion is reflected in the view;
failed records remain. An inaccessible path is reported and retained. Missing HIP
or HDA paths retain the existing cleanup eligibility rule. Neither command deletes
HIP/HDA files. A post-commit display failure triggers a record-tree reload and is
reported separately from a database failure. Team scene observations are not part
of this operation.
