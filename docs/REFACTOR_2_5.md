# Refactoring items 2–5

Implemented without changing Designer layouts, widget names, menu structure or gestures.

## 2. Explicit owners

- `libs/domain.py`: `SelectionState` owns separate asset/history selections. Replaces the scattered current-item fields across panel mixins.
- `libs/asset_store.py`: `AssetStore` owns shared list/table rows, maintains the ID→source-row index, validates IDs and brackets mutations with notifications to both Qt models.
- `libs/task_controller.py`: `TaskController` owns file-job completion and file/video job state. Completion is consumed once, including synchronous draining during Houdini panel destruction. Dialogs and feedback stay in the panel.
- `libs/asset_commands.py`: deletion commands receive a database and explicit asset/file inputs. UI changes happen only after successful file/DB changes.

Feature mixins still exist for UI wiring. This is a reduction of shared-state coupling, not a claim that the entire panel is now independently type checked.

## 3. Data contracts

`AssetData`, `HistoryData` and `SceneRecord` define database/UI payload fields, including nullable paths and media. Database return contracts and list/table/history model constructor inputs use these types. Qt callback payloads and some legacy mutation methods remain dynamic.

Mypy now checks 26 source files, including the new owners, journal, cache and three Qt source models (previously 17). The project retains the Python 3.11 syntax baseline required by the installed Houdini 21 build. Qt model enums use scoped Qt 6 names; fractional icon dimensions are converted explicitly to integers.

## 4. Persistent recovery

Schema version 2 adds `operation_commits`. Existing databases receive the normal pre-migration SQLite backup. Nested transactions now use savepoints.

`MoveJournal` writes and flushes rename intent before touching a file. For rename/delete operations, SQLite records the operation ID in the same transaction as the metadata change. Recovery checks this marker to distinguish an interrupted operation from a committed operation whose journal cleanup was interrupted. Import activation journals the asset-directory and database swaps as one operation. Startup recovery runs before opening the library database.

Failure recovery reverses moves in order, is repeatable, and refuses to overwrite conflicting files. `QLockFile` prevents overlapping journal operations/recovery; a live process is never declared stale merely because a timer expired. This is not a general lock against external programs or every legacy writer.

Deletes retain hidden `.ihda-deleted-*` recovery files beside their original location. Imports retain `.previous-*` copies. These consume storage and are not automatically purged. Staged imported files are flushed on the archive worker; journal files and POSIX parent directories are flushed around moves. Python does not expose equivalent directory fsync on Windows. Process-crash tests passed; hardware power-loss behavior and network filesystem durability were not simulated.

Covered workflows: import activation, asset rename, asset deletion and history deletion. HOM asset creation and preview rendering retain their existing transaction/error handling and are not covered by the move journal. The GUI thread still owns all HOM operations.

## 5. Large-library measurements and bounded work

`benchmarks/benchmark_library.py` seeds 10,000 and 50,000 assets with matching histories in a temporary SQLite library. The checked-in JSON contains median timings from three repetitions, measured on Linux/WSL, Python 3.12.3, Qt 6.11.2. This is a synthetic warm-cache workload, not a production-library or network-share guarantee. Thumbnail rows intentionally reference one 256×256 image, so this does not measure memory use for thousands of unique images.

| Measurement | 10,000 assets | 50,000 assets |
| --- | ---: | ---: |
| 100 ID lookups, previous algorithm | 34.610 ms | 190.829 ms |
| 100 ID lookups, maintained index | 0.007 ms | 0.007 ms |
| Thumbnail startup, previous eager loop | 81.197 ms | 347.386 ms |
| Thumbnail startup, path registration | 42.338 ms | 177.736 ms |
| Asset DB query | 161.235 ms | 834.911 ms |
| History DB query | 184.678 ms | 675.729 ms |
| Filter then clear | 114.288 ms | 520.260 ms |
| Sort ascending and descending | 428.013 ms | 2384.386 ms |

Initial thumbnail decoding is now zero. Visible requests decode independent QImages on two Qt worker threads, with at most 32 outstanding requests. The GUI thread creates QPixmaps and repaints views. An LRU cache limits retained pixmaps to 256 entries / approximately 64 MiB; decoding dimensions are capped at 1024 pixels. Versioned requests cannot reinstall images after a path change or deletion. History cache clearing preserves the object referenced by models.

Full DB snapshots and Qt proxy sorting remain synchronous; the measured 50,000-row sort is still a remaining responsiveness limitation. The measurements do not support claiming that every large-library interaction is instantaneous.

Reproduce with:

```sh
python benchmarks/benchmark_library.py --counts 10000 50000 --output docs/benchmark-results.json
```

Implementation references: [SideFX Qt integration](https://www.sidefx.com/docs/houdini/hom/cb/qt.html), [Qt thread support](https://doc.qt.io/qt-6/threads-modules.html), [Qt process locking](https://doc.qt.io/qt-6/qlockfile.html). The implementation stays compatible with the installed Houdini Qt 6.5.3 APIs.

## Verification

- Full regression suite: **72 passed** (7.10 s).
- Ruff lint and formatting: passed; 110 maintained Python files formatted.
- Mypy: passed for 26 configured source files.
- `git diff --check`: passed.
- Native Windows Houdini **21.0.559 / Python 3.11 / Qt 6.5.3** smoke: HDA export/import, original-node preservation, Unicode SQLite paths, panel construction and shutdown passed during this change.
- Crash tests cover each of four import renames, SQLite commit before/after boundaries, conflict retention, repeat recovery and nested transaction rejection. Ordinary deletion rollback, schema 1→2 migration, cache bounds and stale image rejection also pass.
- Interactive three-OS acceptance and hardware power-loss testing remain unperformed. Houdini 22 retains the previously documented environment startup failure, independent of importing this project.
