# SQLite schema review

`model/sqlite3_db_schema.py` provides the base tables and triggers. It is not the
complete deployed schema: `libs/database_migrations.py` adds versioned indexes,
normalized tags and tag synchronization triggers. Base tables include operation
commit markers and numeric CHECK constraints. Production connections enable
foreign keys before invoking migration.

## Version 3 corrections

1. The base category cleanup trigger lacked the user ID predicate. Migration
   already corrected this in v2, but using the base SQL directly behaved
   differently. Both paths now use the same owner-scoped trigger definition.
2. The normalized tag UPDATE trigger cleared only the new asset ID. Moving a
   tag record between assets could leave stale tags attached to the old asset.
   Version 3 replaces the trigger and clears both owners. Upgrade rebuilds
   `asset_tags` from the authoritative legacy `tag_info` field to remove stale
   derived rows while preserving source data.
3. Latest-history queries filter by asset and maximize ID; the existing index
   interposed version between those columns. A dedicated `(hda_key_id, id)` index
   supports this query. Six filename indexes with matching NOCASE collation
   support shared-file reference checks across current and history tables.

Upgrades retain IDs and table data, back up an existing database before mutation,
and install changes in one transaction. Operation commit markers are preserved.
Foreign-key failures abort the upgrade. Version 3 required no table rebuild or ID reassignment; version 4 performs the
transactional reconstruction described below. Older app versions that only support schema v2 reject a v3 database;
use the pre-upgrade backup with the corresponding asset files when rolling back.

## Version 4 structural upgrade

- Removed redundant `UNIQUE(id, hda_key_id)`, `UNIQUE(id, info_id)` and repeated
  primary-key uniqueness declarations. Actual one-to-one asset relationships
  retain `UNIQUE(hda_key_id)`; business-key and foreign-key constraints remain.
- Replaced misleading `VARCHAR(n)` declarations with `TEXT`. Existing local date
  strings are kept as `TEXT` without guessing a timezone or changing their value.
- Added table-level enforcement through column CHECK constraints: boolean fields
  must store integer 0/1; load counts and connection indexes must store nonnegative
  integers. Redundant legacy favorite/load-count validation triggers are removed.
- Frame start/end and FPS now declare `REAL`. Values must be finite numbers; FPS
  must be positive. Negative and fractional frame numbers remain valid. Database
  API annotations match these floating-point values.
- History video filename and directory must either both be NULL or both be present.
  Operation commit IDs are explicitly NOT NULL and nonempty.

Existing base tables are copied into new constrained tables, then replaced inside
one transaction. The dedicated `database_rebuild` module preserves column order,
IDs, AUTOINCREMENT high-water marks (including deleted IDs), explicit indexes,
triggers and views. Triggers are suspended while copying so the operation does not
manufacture new note history or fire user audit hooks. Normalized tags are rebuilt
from their source field after table replacement.

The migration follows SQLite's [documented reconstruction procedure](https://www.sqlite.org/lang_altertable.html#making_other_kinds_of_table_schema_changes).
Foreign-key enforcement is disabled before the transaction, checked before commit,
and restored afterward, including failures. An active caller transaction is
rejected before backup to prevent implicit commit or backup deadlock. Unexpected
columns, conflicting migration temporary names and invalid source values cause
rollback rather than silent deletion, truncation or guessed corrections. Errors
identify the failing table; pre-upgrade backup files remain available.

Upgrades retain the existing `sqlite_sequence` high-water marks to avoid reusing
previously allocated IDs. See [SQLite AUTOINCREMENT](https://www.sqlite.org/autoinc.html).

## Remaining compatibility boundaries

History metadata remains a snapshot; user/category/name fields need not equal the
current asset metadata. Text lengths are not arbitrarily capped. No whole-database
STRICT conversion or retrospective timezone conversion is performed. A malformed
legacy library may need a data-specific repair after migration rejects it; its
values are not automatically guessed. Custom extra columns require an explicit
migration extension. Older app versions cannot open schema v4.

This upgrade copies table contents and creates indexes, so first open requires
time and free disk space proportional to library size plus the backup. It remains
synchronous at database initialization. Index overhead and upgrade duration for
large production libraries have not been benchmarked.

## Version 3 verification (historical)

The regression suite passed **96 tests** (8.46 s), including owner-scoped cleanup,
tag reassignment and parent-ID cascade, v2-to-v3 backup/data preservation, stale-tag
repair and EXPLAIN QUERY PLAN assertions for the new lookup indexes. Existing
migration rollback and recovery tests also passed.

Native Windows Houdini 21.0.559 / Qt 6.5.3 passed HDA export/import, original-node
preservation, Unicode SQLite paths and offscreen panel lifecycle after the schema
change. Interactive three-platform acceptance remains outside this check.


## Version 4 verification (current)

The full regression suite passed **116 tests** (10.69 s). Ruff lint/format and
mypy passed; mypy covers 35 configured files. `git diff --check` passed.

A frozen copy of the original schema is kept in `tests/fixtures/schema_legacy.sql`.
The new tests cover data/history preservation, deleted-ID high-water marks, custom
views/indexes/triggers, fractional and negative frames, fractional FPS, invalid
write rejection, paired optional video paths, nonempty operation IDs, rollback on
invalid old data or extra columns, and rejection of active caller transactions.

Native Windows Houdini **21.0.559 / Qt 6.5.3** passed legacy table reconstruction,
fractional FPS preservation and numeric constraint rejection, in addition to HDA
export/import, original-node preservation, Unicode SQLite paths and offscreen
panel construction/shutdown. All migration runs used temporary test libraries;
the user's live library has not been upgraded during development.
