# Integrity review

This follow-up preserves the panel layout and interaction flow while correcting
file references, asynchronous completion and resource ownership.

## Corrections

- Asset renaming now relocates older-version video paths when the containing
  asset directory moves. History rows retain their individual HDA and media
  filenames. External media paths remain intact. A pure `relocated_path` helper
  replays the same ordered moves for the database and Qt history model, and
  thumbnail caches refresh after the rename commits.
- History deletion checks current assets and surviving histories before moving
  a file to recovery storage. Shared HDA, thumbnail and video files stay available.
  The service also rejects deletion of the latest history, reinforcing the UI rule.
- Video completion updates the encoded asset by ID even if selection changes
  during encoding. Its history snapshot comes from that asset; the DB connection
  closes on success and failure. Row lookups resolve the current asset index after
  insertion instead of relying on an old row number stored in selection or data.
- Thumbnail shutdown rejects late queued results and new decode requests.
  Duplicate/stale completions cannot overwrite a newer pending request. Invalid
  cache limits fail immediately.
- Failed import staging cleanup retains its recovery location and logs cleanup
  failure without replacing the original import exception. Import activation
  conflicts during close use the existing error dialog instead of escaping the
  close handler.

No database schema bump is required for these changes. The existing operation
journal and transaction boundaries continue to protect file moves and DB writes.

## Verification

`tests/test_integrity_followup.py` covers older-version media relocation in both
SQLite and the Qt model, external media preservation, shared-file deletion,
latest-history protection, shutdown callbacks, invalid cache limits, staging
cleanup failures, selection changes during encoding and row lookup after insertion.

- Full regression: **93 passed**, 7.98 seconds.
- Ruff lint/format: passed, 121 Python files.
- Mypy: passed, 34 configured source files; the dynamic UI graph is not fully
  covered by static typing.
- Native Windows Houdini **21.0.559 / Python 3.11.7 / Qt 6.5.3**: HDA export/import,
  original-node preservation, Unicode SQLite paths and offscreen panel lifecycle
  passed using temporary test data.

Interactive viewport capture, drag/drop and codec acceptance on Windows, macOS
and Linux remain pending. The installed Houdini 22 build previously failed before
project import and is not a verified target. Full DB reads and Qt proxy sorting
remain synchronous; this review does not claim new large-library performance
measurements. Shared-file reference queries search filename candidates across
current and history tables and have not been benchmarked at large history sizes.
