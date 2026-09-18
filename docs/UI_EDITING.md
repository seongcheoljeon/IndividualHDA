# UI 수정 가이드

앱의 UI는 모두 Python 코드로 관리합니다. `.ui` 파일이나 변환 명령은 사용하지 않습니다.
화면별 `layout.py`는 직접 수정하는 소스이며, 자동 생성 파일이 아닙니다.

## 어디를 수정하면 되나요?

| 화면 | UI 파일 | 먼저 볼 메서드 |
| --- | --- | --- |
| 메인 창·상세·메뉴 | `widgets/panel/layout.py` | `MainWindowLayout.build_ui()` |
| 카테고리 트리 | `widgets/panel/layout_category.py` | `build_category_panel()` |
| 이력 페이지 | `widgets/panel/layout_history.py` | `build_history_search()`, `build_history_date_filter()`, `build_history_results()` |
| 씬 레코드 / 인사이드 노드 | `widgets/panel/layout_scene_records.py`, `layout_inside_nodes.py` | `build_scene_records()`, `build_inside_nodes()` |
| 검색·에셋 목록·확대·화면 전환 | `widgets/asset_browser/view.py` | `_build_toolbar()`, `_build_search_row()` |
| 개인 / 팀 라이브러리 선택 | `widgets/asset_browser/view.py` | `_build_toolbar()`의 `comboBox__library_source` |
| 팀 연결 / 구성원 설정 | `widgets/library_connection/dialog.py`, `members.py` | 각 설정 대화상자의 생성 메서드 |
| 개인 → 팀 복사 | `widgets/asset_copy/dialog.py` | `_build_layout()`; 흐름 준비는 `presenter.py` |
| 환경설정 | `widgets/preference/layout.py` | `_build_storage_settings()`, `_build_icon_sizes()`, `_build_item_padding()` |
| 이름 변경 | `widgets/rename_ihda/layout.py` | `_build_name_preview()`, `_build_name_input()` |
| 상세 보기 대화상자 | `widgets/detail_view/layout.py` | `_build_content()` |
| 영상 생성 설정 | `widgets/make_video_info/layout.py` | `_build_video_settings()`, `_build_flipbook_options()` |
| 영상 플레이어 | `widgets/video_player/layout.py` | `_build_playlist()`, `_build_playback_controls()` |
| 웹 보기 | `widgets/web_view/layout.py` | `_build_navigation()`, `_build_bookmarks_and_address()` |
| AI 모델 관리 / 라이브러리 관리 | `widgets/ai_models/dialog.py`, `widgets/library_manager/dialog.py` | 기존 코드 UI의 생성 메서드 |

`build_ui()`에는 화면을 만드는 순서가 있습니다. 해당 `_build_*` 메서드에서
위젯 생성, 이름, 텍스트, 크기, 배치가 함께 보이도록 구성했습니다.
예를 들어 이력 날짜 검색은 `layout_history.py`의 `build_history_date_filter()`에서 수정합니다.
큰 페이지는 자기 모듈의 `build_*(layout, window)` 함수에 있고, 위젯은 여전히
`MainWindowLayout`의 속성으로 선언됩니다.

## 이름 규칙

기존 스타일인 **위젯 종류 + `__` + 용도**를 사용합니다.

```python
self.pushButton__note_save
self.lineEdit__data_dirpath
self.horizontalLayout__tag_actions
self.widget__note_editor
```

- Python 속성 이름과 `setObjectName()`에 같은 이름을 사용합니다.
- `layoutWidget5`, `horizontalLayout_7` 같은 자동 번호 이름을 새로 만들지 않습니다.
- 버튼·입력창·splitter의 기존 이름은 설정 복원이나 이벤트 처리에 사용됩니다.
  이름을 바꾸면 해당 위젯의 동작 파일, 설정 코드, 테스트도 함께 확인합니다.
- 일반 데이터와 서비스에는 `search_request`, `search_gateway`처럼 역할을 나타내는
  snake_case를 사용합니다.

## 수정 방법

1. **텍스트·아이콘·크기:** 해당 위젯의 `setText()`, `setIcon()`, `setMinimumSize()` 등을 수정합니다.
   `_translate()`는 기존 번역 문맥을 유지하므로 사용자에게 보이는 문구에 사용합니다.
2. **배치:** `QVBoxLayout`, `QHBoxLayout`의 `addWidget()`, `addLayout()`, 여백·간격을 수정합니다.
3. **새 컨트롤:** 관련 `_build_*` 메서드에서 만들고 의미 있는 이름을 지정한 뒤 레이아웃에 추가합니다.
4. **클릭 동작:** 레이아웃 파일에 DB·네트워크·Houdini 작업을 넣지 않습니다.
   대응하는 동작 파일(`preference.py`, `video_player.py` 등)이나 Presenter에서 연결합니다.
   대화상자의 기본 확인/취소 연결은 `layout.py`의 `_build_dialog_buttons()`에 있습니다.
5. **공통 설정:** 글꼴·크기 정책의 작은 공통 함수는 `widgets/layout_helpers.py`에 있습니다.
   복잡한 범용 UI 생성기나 별도의 설정 문법을 도입할 필요 없이 Qt 코드를 직접 수정합니다.

현재 UI 생성은 전부 코드로 전환되었습니다. 기능별 상태 판단·검증·저장 조정은
각 기능 폴더의 `presenter.py`에서 수정합니다. 전체 파일 대응표는
[ARCHITECTURE.md](ARCHITECTURE.md)의 Feature presentation boundaries를 참고합니다.
Qt 위젯 갱신·모델 알림·Houdini 호출은 화면 파일과 패널 어댑터에 남습니다.
레이아웃 모듈에는 저장소나 서버 구현을 넣지 않습니다.

- 노트·태그 배치와 저장 상태 라벨: `widgets/panel/layout.py`의 `_build_note_and_tags()`.
- 노트·태그 편집 상태와 저장 대상: `widgets/asset_details/presenter.py`.
- 저장 후 목록·이력 갱신: `widgets/asset_details/integration.py`.
- 등록·이름 변경·삭제의 저장 성공/실패 처리: `widgets/asset_lifecycle/presenter.py`.
- 로컬 파일 이름과 경로 변경 계획: `libs/asset_lifecycle.py`, `libs/asset_rename.py`.
- 대화상자 확인 동작은 **검증 후 `dialog.accepted`**에 연결합니다.
  `buttonBox.accepted`에 메인 작업을 직접 연결하면 검증을 우회합니다.

노트·태그 초안은 현재 창이 열린 동안 자산별로 유지됩니다. 다른 라이브러리로
전환하거나 앱을 종료하기 전에는 필요한 초안을 저장합니다.

## 확인 방법

```sh
python -m pytest -q tests/test_layouts.py tests/test_asset_browser.py tests/test_feature_presenters.py tests/test_qt.py
python -m ruff check .
python -m ruff format --check .
python -m mypy
```

새 레이아웃은 정적 검사와 타입 검사 대상입니다. 테스트는 실제 Qt 화면 구성,
대화상자 확인/취소, 탭·메뉴·임베딩 영역, 설정 복원을 확인합니다.
마지막으로 Houdini에서 화면 크기 조절, 키보드 포커스, 드래그와 메뉴 동작을 확인합니다.

아이콘용 `.qrc`와 `*_rc.py`는 계속 사용합니다. UI 레이아웃 파일과 별개인 Qt 리소스이며,
이미지 리소스 변경이 필요할 때만 기존 리소스 컴파일 방식을 사용합니다.

팀 라이브러리는 기존 메인 목록과 노트·태그 위젯에 연결합니다. 화면 통합은
`widgets/team_library/integration.py`, 우클릭 동작은 `actions.py`, 저장·초안·충돌은
`presenter.py`에서 수정합니다. 별도 Workspace 레이아웃은 제거되었습니다.

## 휴지통·버전 상세 정보

`widgets/library_metadata/dialog.py`에서 두 집중형 대화상자의 코드 UI를 수정합니다.
버전 설명, 의존성 표, 활동/파일 상태가 있으며 UUID와 수정 번호는 일반 UI에서 숨깁니다.
저장 및 삭제 정책은 `libs/library_management.py`의 gateway와 각 저장소 서비스에 있습니다.
`widgets/panel/library_tools.py`가 현재 Personal/Team 소스에 맞는 gateway를 연결합니다.

## Panel behavior and shared defaults

- Toolbar icon sizes, compact spacing, tag colors, and asset/history table column
  defaults: `widgets/ui_tokens.py`.
- Selection fields and snapshot restoration: `libs/domain.py` (`SelectionState`)
  and `widgets/panel/selection_presenter.py`. Use selection methods when changing
  assets/versions so the name, path and version update together.
- Reload scheduling and stale results: `widgets/panel/sync_presenter.py`.
- Personal/Team selection, metadata save, refresh, history and capabilities:
  `widgets/panel/library_session.py`.

Continue using `widgetType__purpose` for named controls. Layout files define the
widgets; presenters decide behavior; Qt adapters map signals and model indexes.
No Designer conversion step is needed.

## Editing registration behavior

- New asset/version capture order and publication: `libs/asset_registration.py`.
- Houdini HDA and optional thumbnail capture: `widgets/asset_lifecycle/capture.py`
  (GUI thread only).
- Confirmation dialogs, metadata collection, and successful model updates:
  `widgets/panel/asset_registration.py`.
- Service composition: `PanelServices.registration` in `widgets/panel/services.py`.

Keep new filesystem writes out of metadata collection; use the capture port so
capture failures cannot leave partially prepared final files.

## Rename and Trash actions

- Shared name validation: `libs/asset_names.py` (the rename dialog imports it).
- Rename execution/validation: `LocalAssetLifecycle.rename`; existing journal and
  repository own rollback.
- Committed model changes: `_apply_renamed_asset`, `_apply_deleted_asset`, and
  `_apply_deleted_history` in `widgets/panel/asset_management.py`.
- Bulk historical-version actions: `_trash_history_rows`. Keep note history and
  files intact; current-version protection is enforced again by storage.

Do not remove model rows in callers after a command returns: the command may have
failed. Use committed callbacks and resolve model rows from stable asset/history IDs.

## Main-window assembly

- Layout and widget names: `widgets/panel/layout.py`.
- Feature creation order and resource registration: `widgets/panel/composition.py`.
- Initial model/widget configuration and signal wiring: `widgets/panel/bootstrap.py`.
- Shutdown ordering and retry policy: `widgets/panel/lifetime.py` and `shutdown.py`.
- AI, archive and sync behavior: their composed adapters in `widgets/panel/`.

Register a resource as soon as it is acquired. Stop timers before draining workers,
then dispose of dependent views. Keep `main.py` focused on Qt entry points and
explicit delegation; do not add new feature Mixins or inject methods dynamically.

## Data fields, pages and operational values

- Give multi-column SQL results explicit, unique aliases. Read by field name and
  convert at the repository boundary; do not pair query results with a separate
  positional key list. Preserve old integrations through `libs/row_contracts.py`.
- Add model rows using named payloads. Never insert fields into a caller's list.
- Switch pages with `setCurrentWidget`; use `AssetViewMode` for browser button IDs.
  Preserve existing widget names and default page order for saved settings.
- Change presentation defaults in `widgets/ui_tokens.py`. Keep values with
  different visual purposes separate, even when their numbers happen to match.
- Inject `PanelPolicy`/`SearchPolicy`, `SQLitePolicy`, or `ArchiveLimits` when a
  deployment needs different resource limits. Existing preference and Team/server
  policy systems remain authoritative for settings they already own. No extra
  preferences screen or database migration is required.

## Version tracking and recovery

- Manual check form and usage/dependent lists: `widgets/library_metadata/tracking.py`.
- Registration retry/discard: `widgets/library_metadata/recovery.py`.
- Shared deletion warning wording: `widgets/library_metadata/dependency_warning.py`.
- Menu wiring: `widgets/panel/library_tools.py`; host observation:
  `widgets/panel/scene_usage.py`. Worker lifetime belongs to composition/shutdown.
- Keep manual checks explicit and environment-specific. Imported reports show their
  source and do not claim destination validation. Hide tracking for older servers.
- Do not perform HTTP calls on the GUI thread or recapture Houdini nodes from a
  recovery worker. Workers retry captured files through the stored request ID.
