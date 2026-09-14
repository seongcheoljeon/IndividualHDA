# Model, proxy, theme and structural audit

Audit scope: maintained application Python, the six source models and six
QSortFilterProxyModel subclasses, panel selection/mutation paths, theme/resource
loading, Houdini callbacks, database/session code and asynchronous file/process
boundaries. Generated UI/resource payloads and vendored packages are inspected at
the integration boundary rather than rewritten. Existing Designer layouts remain
unchanged. Static inspection is not proof of the absence of every defect.

## Findings and fixes

| Area | Failure | Correction |
| --- | --- | --- |
| Flat proxies | Missing tags/type/favorite values could cause join, regex or boolean errors; duplicated name filtering | Shared null-safe `AssetProxyModel` with one text predicate |
| History dates | A date-only upper bound excluded timestamps later that day; None input raised in the setter | Validated inclusive calendar-day bounds; None clears the filter |
| Tree proxies | Repeated Python subtree/ancestor searches; different children could satisfy text and asset predicates separately | Qt recursive descendant propagation, ancestor text context and per-row attribute predicates |
| Counts | Counting began beneath only the first root | Iterative traversal from the invisible root, including all top-level branches |
| Selection | Source row numbers were used directly as sorted/filtered proxy rows | `mapFromSource` with invalid/hidden-result handling |
| ID lookup | Stored item_row values depended on prior calls to data() | Derive row numbers by enumerating current source storage |
| Multiple deletion | Later reads used ordinary proxy indexes after earlier rows changed | Capture selected asset/history data first; resolve asset rows again by ID |
| Category search | Recursive calls dropped both the search name and the returned result | Propagate the name/result through traversal; accept an unspecified root |
| Live edits | Asset/history dictionaries changed without dataChanged | Notify all columns/roles in both shared asset models and the history model |
| List columns | PySide exposes the base QAbstractListModel columnCount as inaccessible | Explicit one-column implementation for the list model |
| Tree insertion | begin/endInsertRows announced rows that never existed | Reject generic empty insertion; domain add/reload paths remain authoritative |
| Table/history insertion | insertRow did not match Qt's positional parent contract | Correct Qt signatures; reject insertion without domain data |
| Removal | Invalid ranges and multi-row counts were not honored; delete_node reversed parent/child lookup | Validate bounds, announce the full range, remove every requested row and use index.row() |
| Default initialization | Missing font/icon/cache defaults and InsideModel(None) could fail | Safe defaults for all six source models |
| Dark theme | Resource registration was missing | Explicit lazy resource-module import; always close the QSS QFile |
| Host theme | Custom overrides replaced the just-applied Houdini stylesheet | Compose the host stylesheet and local overrides; reset houdiniStyle on dark mode |
| Houdini category lookup | Detecting the network context created temporary scene nodes | Read `pwd().childTypeCategory()` directly |
| Empty layout | Averaging positions divided by zero for empty/indirect-only input | Keep the origin offset when no movable items contribute |

QSortFilterProxyModel remains appropriate. The defects were in predicates,
notifications and index handling. Native `recursiveFilteringEnabled` is available
in the Houdini 21 Qt 6.5 baseline; this implementation does not require newer
beginFilterChange/endFilterChange APIs. See the
[Qt proxy contract](https://doc.qt.io/qt-6/qsortfilterproxymodel.html).
The network category read uses the documented
[SideFX OpNode API](https://www.sidefx.com/docs/houdini/hom/hou/OpNode.html#childTypeCategory).

## Verification

- **59 pytest cases passed**. The 19 added audit cases cover every proxy type,
  every source model with QAbstractItemModelTester at default initialization,
  populated category multi-row removal, null metadata, combined tree filters,
  multi-root counts, sorting/mapping, live edit notifications, deletion through
  a changing proxy, inclusive date bounds, resource URLs, theme restoration and
  read-only Houdini category lookup.
- Existing tests still cover populated panel search, shared list/table model
  notifications, DB migration/rollback, archive traversal/recovery, process
  cancellation, host shutdown and Python 3.11 annotation coverage.
- Ruff lint/format and git whitespace checks passed.
- Mypy passed for the **17 configured core modules**. This is not a claim that
  generated widgets or the complete Qt mixin graph pass strict static checking.
- Windows Houdini **21.0.559**, Python **3.11.7**, Qt **6.5.3**: native hython smoke
  passed HDA export/import, original node preservation, SQLite/Unicode, dark/default
  theme switching, empty position handling and offscreen panel construction/close.

Interactive viewport capture, real desktop middle-button drag/drop, codec
availability and visual comparisons on Windows/macOS/Linux remain manual host
acceptance checks. CI is configured for all three operating systems; it was not
executed remotely in this session. Houdini 22 remains blocked by the previously
recorded installation-level hython crash. See [VALIDATION.md](VALIDATION.md).


## Follow-up items 2–5

See [REFACTOR_2_5.md](REFACTOR_2_5.md) for explicit state owners, typed payloads, schema v2 crash recovery, asynchronous bounded thumbnails, measured performance and remaining limitations.
