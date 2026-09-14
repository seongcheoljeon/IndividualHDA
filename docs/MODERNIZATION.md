# Houdini 21+ modernization

## Contract

Keep Designer layouts, labels, shortcuts, middle-button drag/drop, asset IDs,
version/history behavior and existing library locations. Target Houdini 21+
standard Qt 6 builds and Python 3.11+. Do not install a separate Qt into Houdini.

## Implementation sequence

1. Port Python 2 semantics and Qt APIs, remove runtime module reloads and vendored
   Python backport dependencies; smoke-test widgets and models.
2. Version SQLite schemas, back up before upgrading, migrate in a transaction,
   preserve legacy rows and IDs; index relational lookups and fix category cleanup.
   Parameterize user data, add explicit connection/transaction lifetime handling.
3. Separate external process/file work from Qt/HOM work. Encode/probe asynchronously,
   deliver results on the UI thread, and clean up pending operations on shutdown.
4. Use native Unicode paths, argument-vector process launch, executable discovery,
   safe archives and consistent settings across Windows, macOS and Linux.
5. Add regression coverage for migrations, quoting, archive safety, process failures,
   models, playlist behavior and panel creation. Document real-host checks separately.

## Verification boundary

Automated Python/Qt tests can run without Houdini. Real asset capture/import,
viewport flipbooks, host drag/drop, codec availability and native desktop behavior
must also be checked inside licensed Houdini on each OS. Passing headless tests
alone is not proof of those host integrations.

## References

- https://www.sidefx.com/docs/houdini/news/21/platforms.html
- https://www.sidefx.com/docs/houdini/hom/cb/qt.html
- https://doc.qt.io/qtforpython-6/faq/porting_from2.html
- https://doc.qt.io/qt-6/qtmultimedia-changes-qt6.html

## Implementation status

- [x] Python 3 and Qt 6 APIs, original Designer layouts and theme resources.
- [x] Database versioning/backups/migrations, bound SQL parameters, normalized tags,
      indexes, transaction groups for asset registration/update and version history.
- [x] Asynchronous encoders/probes/archives, bounded probing concurrency, process
      cancellation, owned worker shutdown and queued log delivery.
- [x] Portable paths/process arguments, atomic settings/video replacement, private
      HDA staging, archive relocation and rollback with retained recovery copies.
- [x] Regression suite, real Windows Houdini 21 HDA roundtrip and panel smoke test,
      three-OS CI definition, installation and recovery documentation.
- [ ] Interactive viewport/drag/drop/codec acceptance across all three OSes.
- [ ] Houdini 22 host execution: its installed hython crashes even without the project.

See [validation details](VALIDATION.md) for tested behavior and remaining host checks.

## Structural refactoring

Panel features and database domains are now separate modules, preserving the
`main.IndividualHDA` and `libs.sqlite3_db_api.SQLite3DatabaseAPI` entry points.
See [module responsibilities and extension rules](ARCHITECTURE.md).

The second structural pass reduces `main.py` to 266 lines and separates the
remaining panel responsibilities into 13 feature modules. Maintained production
signatures (1,105) and panel hooks now have annotations compatible with Python
3.11. Host destruction has a dedicated synchronous cleanup hook; queued HOM calls
are suppressed once panel shutdown begins. The current regression suite has 40
tests, with mypy covering 17 core modules.

The subsequent model/proxy/theme audit brings the regression suite to **59 tests**.
See [the audit report](AUDIT.md) for defects corrected and validation limits.


## Follow-up items 2–5

See [REFACTOR_2_5.md](REFACTOR_2_5.md) for explicit state owners, typed payloads, schema v2 crash recovery, asynchronous bounded thumbnails, measured performance and remaining limitations.
