# 개인용 / 팀 라이브러리

메인 에셋 목록 위의 **Personal / Connect team…** 선택기로 라이브러리를 전환합니다.
별도의 Workspace 창은 제거했습니다. 팀에서도 기존 썸네일·목록/테이블 전환·검색·
카테고리·노트·태그 편집기를 사용합니다.

## 사용 흐름

- 개인 라이브러리는 앱을 열면 바로 사용합니다. 별도의 Connect 단계가 없습니다.
- **Connect team…**에서 서버 주소와 관리자가 발급한 토큰을 입력하고 Connect를
  누른 뒤 프로젝트를 선택해 **Open library**를 누릅니다. `IHDA_TEAM_TOKEN`이
  설정되어 있으면 토큰 입력란을 채웁니다. URL만 저장하고 토큰은 디스크에 저장하지 않습니다.
- 연결과 첫 목록 로딩이 성공한 뒤 메인 화면을 전환합니다. 실패하면 현재 라이브러리와
  편집 내용을 유지합니다. 선택기에서 Personal로 돌아가면 개인 DB와 개인 초안을 복원합니다.
- 이름·태그·타입·노트·All 검색과 `tag:water note:foam` 등의 토큰 검색을 유지합니다.
- 에셋을 선택해 기존 노트·태그 Save 버튼으로 저장합니다. 우클릭 메뉴에서 가져오기,
  영상 재생, 이력, 이름 변경, 즐겨찾기, 새 버전, 썸네일·영상 첨부, 삭제를 실행합니다.
- 빈 목록 영역을 우클릭하면 파일을 등록할 수 있습니다. Houdini 노드의 드래그 등록과
  목록 에셋의 드래그 가져오기도 팀 경로로 연결됩니다. 파일 전송은 백그라운드에서 수행합니다.
  썸네일은 화면에서 필요할 때만 받으며, 전체 이미지 다운로드가 끝날 때까지 목록을 기다리지 않습니다.
- History 탭은 팀 모드에서 선택한 에셋의 이력을 표시합니다. 이력 행 우클릭으로
  해당 버전 가져오기·영상 재생·삭제를 실행합니다. 현재 버전은 삭제할 수 없습니다.
- 연결 설정은 **Library Tools → Team connection…**, 구성원 설정은 owner에게만
  보이는 **Project members…**에 있습니다. viewer는 조회·가져오기만 가능합니다.

ID·revision·재시도 버튼·비교 편집기는 일상 화면에 표시하지 않습니다. 충돌이 발생하면
저장 상태 라벨의 **Review changes**로 최신 저장값과 초안을 비교합니다. 응답이
불확실한 저장은 같은 위치의 **Retry**로 재시도합니다. 창이 열린 동안 에셋별 초안을
유지하며, 미저장 팀 초안이 있을 때 다른 라이브러리로 전환하면 폐기 여부를 확인합니다.

개인 모드는 기존 SQLite 경로를 사용합니다. 팀 모드에서는 개인 repository와 DB 경로를
화면에서 분리하여 ID가 겹쳐도 개인 DB를 수정하지 않습니다. 개인 전용 백업·아카이브·
DB 정리·HIP 인스턴스 기록·연결 노드 보기 도구는 팀 모드에서 비활성화합니다.
팀 가져오기는 현재 HIP에 에셋을 만들지만 개인 DB의 HIP 인스턴스 기록에는 쓰지 않습니다.
개인 모드 및 Houdini 클라이언트에는 서버 패키지를 설치할 필요가 없습니다.

## 개인 에셋을 팀으로 복사

1. Personal 목록에서 에셋을 선택하고 **우클릭 → iHDA → Copy to team…**을 누릅니다.
   **Library Tools → Copy to team…**에서도 열 수 있습니다.
2. **Choose project…**에서 대상 서버와 프로젝트를 선택합니다. 메인 화면은 Personal을 유지합니다.
3. 필요하면 팀 에셋 이름을 바꾸고, 이전 버전·썸네일/영상 포함 여부를 선택합니다.
4. **Preview**에서 버전별 파일, 중복을 제외한 총 용량, 빠진 미디어, 이름 충돌을 확인합니다.
   Team version 열을 편집할 수 있으며, 같은 이름의 옛 이력은 고유한 버전명을 제안합니다.
   마지막 행이 복사 후 현재 버전입니다.
5. **Copy**를 누릅니다. 완료 후 팀 프로젝트에서 조회·가져오기할 수 있습니다.

선택한 활성 버전의 HDA, 썸네일/영상, 버전 설명·의존성 기록, 해당 시점까지의 버전 노트,
현재 에셋의 노트·태그를 복사합니다. 원본 라이브러리/에셋/버전 UUID와 버전명·작성 정보는
출처로 저장하고, 팀 에셋과 버전에는 새 UUID를 부여합니다. 개인 DB와 파일은 수정하지 않으며,
즐겨찾기·사용 횟수는 개인 설정으로 남습니다. Trash 버전, HIP/외부 의존 파일,
별도의 노트 수정 이력 전체는 복사 대상이 아닙니다. 의존성은 기록만 옮기며 자동 설치하지 않습니다.

누락된 HDA는 복사를 막고, 누락된 선택 미디어는 미리보기에서 알린 후 제외합니다.
모든 파일 업로드 후 에셋과 버전들을 한 트랜잭션으로 등록합니다. 실패 중에는 일부 버전만
있는 에셋이 보이지 않습니다. 같은 원본을 같은 프로젝트에 다시 등록하는 요청과
같은 카테고리의 이름 충돌은 Trash까지 포함해 서버에서 차단합니다.

중단 후 같은 개인 에셋과 대상 프로젝트를 선택해 **Preview → Resume**으로 재개합니다.
이미 업로드한 파일을 재사용하고, 응답만 유실된 등록은 동일 요청으로 결과를 확인합니다.
재개 기록은 설정 폴더의 `workspace/copies/`에 저장하며 토큰을 포함하지 않습니다.
아직 등록을 요청하지 않은 작업은 **Change selection**으로 다시 선택할 수 있습니다.
등록 결과가 불확실하면 먼저 Resume으로 결과를 확인해야 합니다.

서버에 `asset_copy` 기능이 있어야 하므로 서버 코드도 함께 업데이트합니다.
추가 스키마 변경은 없습니다(SQLite 5 / PostgreSQL 2 / API 2 유지).
한 번에 에셋 하나, 최대 500개 버전 및 명령 메타데이터 256 KiB를 지원합니다.
메타데이터 한도를 넘으면 업로드 전에 알립니다.

## 서버 설치

서버는 Houdini와 별도 환경에서 실행합니다. Python 3.11+와 PostgreSQL이 필요합니다.
아래 Compose 구성은 PostgreSQL 16과 별도 파일 볼륨을 사용합니다.

1. `.env.example`을 `.env`로 복사하고 `IHDA_POSTGRES_PASSWORD`에 임의의 긴
   **16진수 문자열**을 넣습니다. 이 값은 DB URL에도 사용되므로 URL 예약 문자를
   포함하지 않도록 합니다. `.env`는 버전 관리하지 않습니다.
2. DB를 시작하고 초기 스키마를 만듭니다.

   ```sh
   docker compose up -d database
   docker compose build api
   docker compose run --rm api python -m ihda_server.cli init-db
   ```

3. 사용자와 프로젝트를 만듭니다. 첫 명령이 출력한 UUID를 뒤의 `USER_UUID`에 넣습니다.

   ```sh
   docker compose run --rm api python -m ihda_server.cli create-user artist
   docker compose run --rm api python -m ihda_server.cli create-project USER_UUID Studio
   docker compose run --rm api python -m ihda_server.cli issue-token USER_UUID --days 30
   docker compose up -d api
   ```

`issue-token`의 출력은 비밀 토큰입니다. 서버 DB에는 토큰 원문 대신 SHA-256 해시를
저장합니다. 만료 기간은 1–365일이며 기본 30일입니다. 추가 사용자는 관리자가
`create-user`로 발급하고, 프로젝트 owner가 Project members 설정에서 해당 UUID에
역할을 부여합니다. viewer는 조회·다운로드, editor는 에셋 수정, owner는 구성원
관리도 가능합니다. 프로젝트에는 최소 한 명의 owner가 남아야 합니다.

사용자의 모든 토큰을 폐기하려면 다음 명령을 사용합니다.

```sh
docker compose run --rm api python -m ihda_server.cli revoke-user USER_UUID
```

### Docker 없이 실행

별도 가상 환경에서 `pip install -r requirements-server.txt`를 실행합니다.
`IHDA_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE`와
쓰기 가능한 `IHDA_BLOB_ROOT`를 설정한 뒤 동일한 CLI 명령을 실행합니다.

```sh
python -m ihda_server.cli init-db
python -m ihda_server.cli create-user artist
python -m ihda_server.cli create-project USER_UUID Studio
python -m ihda_server.cli issue-token USER_UUID --days 30
uvicorn ihda_server.app:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

`init-db`는 초기 스키마 버전 1을 설치합니다. 서버 시작은 스키마를 확인할 뿐
자동으로 변경하지 않습니다. 후속 스키마 변경에는 명시적인 마이그레이션과 복구
절차를 추가해야 합니다. SQLite 서버 어댑터는 테스트용이며 실제 서버는 PostgreSQL을
요구합니다.

### Houdini에서 연결

메인 화면의 **Connect team…** 또는 **Library Tools → Team connection…**을 사용합니다.
토큰을 붙여넣거나 Houdini 시작 환경에 `IHDA_TEAM_TOKEN`을 설정합니다. 토큰 갱신 후에는
다시 연결합니다. 로컬 테스트 URL은 `http://127.0.0.1:8000`입니다.

LAN/스튜디오 접속은 인증서가 있는 HTTPS 리버스 프록시를 통해 제공합니다.
기본 Compose는 API 포트를 호스트의 loopback에만 열며 TLS 프록시는 포함하지 않습니다.
클라이언트는 loopback 이외의 평문 HTTP와 리다이렉트를 거부합니다. 기본 파일 한도는
1 GiB이며 `IHDA_MAX_UPLOAD_BYTES`로 설정합니다. 클라이언트 소켓 제한은 기본 30초입니다.
프록시의 업로드 크기·시간 제한도 맞춰야 합니다.

## 충돌·재시도·파일 보관

수정 요청은 선택한 에셋 ID와 **편집 기준 revision**을 캡처합니다. 다른 사용자가
먼저 수정하면 저장을 거부하고 초안을 유지합니다. Review changes로 최신 저장값을
불러와 초안과 비교한 후 다시 저장합니다. 목록 Refresh는 초안의 기준 revision을
자동으로 바꾸지 않습니다. 미저장 초안은 창이 열린 동안만 보관됩니다.

네트워크 오류나 서버 오류 후에는 저장 상태 라벨의 **Retry**를 사용합니다. 같은
요청 ID를 다시 보내므로 서버에 이미 저장되었어도 중복 등록하지 않습니다.
불확실한 요청이 남아 있으면 새 쓰기는 막습니다. 요청 파일은
`workspace/pending/`에 라이브러리·프로젝트·사용자별로 분리하며 프로세스 잠금으로
덮어쓰기를 방지합니다. 보류 파일을 임의로 지우기 전에 서버 저장 결과를 확인해야
합니다. 토큰이 만료되었으면 같은 사용자로 토큰을 갱신하고 다시 연결합니다.

파일은 먼저 SHA-256 주소로 서버에 업로드하고, 해당 프로젝트에 등록된 파일만
에셋 메타데이터가 참조할 수 있습니다. 다운로드는 크기와 SHA-256을 검증하고
원자적으로 캐시에 반영합니다. 서버 경로나 클라이언트 경로를 파일 이동 명령으로
사용하지 않습니다. 개인 모드의 원본 경로는 기존 라이브러리의 메타데이터입니다.

삭제는 휴지통 상태 변경이며 에셋·버전·파일을 보존합니다. 영구 삭제는 owner만
수행할 수 있고, 참조가 없어진 파일은 아래의 명시적 정리 명령으로 제거합니다.
업로드 후 등록 취소·실패한 파일도 정리 후보가 될 수 있습니다. 요청 결과와 로컬 캐시는
자동 정리하지 않습니다. 이미 내려받은 로컬 파일은 권한을 회수해도 원격으로 삭제되지 않습니다.

## 백업과 복구

서버는 **PostgreSQL과 등록된 blob 파일을 한 세트**로 백업합니다. 관리자 명령을 제공합니다.
메인 UI에는 백업 관리 화면을 추가하지 않습니다.

### 준비

```sh
docker compose --profile tools build admin
```

관리자 이미지에는 PostgreSQL 16의 `pg_dump`/`pg_restore`와 서버 Python 환경이 있습니다.
서버와 같은 PostgreSQL 주 버전을 사용합니다. 직접 실행하는 환경에서는 해당 도구를 PATH에
설치하거나 `IHDA_PG_BIN`에 바이너리 디렉터리를 지정합니다. Qt/Houdini는 필요 없습니다.

### 백업 생성과 검사

```sh
docker compose run --rm admin backup /data/backups/team-20260915-0300
docker compose run --rm admin verify-backup /data/backups/team-20260915-0300
```

매 실행에 새 경로를 사용합니다. 기존 백업은 덮어쓰지 않습니다. 완료한 디렉터리에는
`manifest.json`, `database.dump`, `blobs/`가 있으며, 파일이 없는 라이브러리는 `blobs/`가
없을 수 있습니다. 디렉터리 전체를 별도 저장장치에 보관합니다. `backup_data` 볼륨이
운영 서버와 같은 디스크에 있으면 디스크 장애에 대한 별도 사본이 되지 않습니다.

백업은 PostgreSQL의 공유 스냅샷으로 DB 덤프와 파일 목록을 맞춥니다.
백업 동안 업로드·파일 정리는 공용 잠금으로 막고, 조회와 기존 메타데이터 편집은 가능합니다.
잠금 충돌은 재시도 가능한 오류를 반환하므로 사용자가 적은 시간에 실행합니다.
긴 백업은 API를 중지한 유지보수 시간에 실행해 업로드 재시도를 피할 수 있습니다.
스키마 마이그레이션이나 별도의 DB/파일 관리 작업과 동시에 실행하지 않습니다.

검사 항목은 덤프·파일의 크기와 SHA-256, 누락/추가 파일, 파일 목록과 DB 소유 정보의 일치,
지원 스키마, 심볼릭 링크와 경로 이탈입니다. 검사 실패·중단 시 완료 백업으로 공개하지 않습니다.
프로세스 강제 종료로 남은 `.backup-partial-*`는 실행 프로세스가 없음을 확인한 뒤 정리합니다.
`verify-backup`은 DB 접속 없이 실행하며, 파일 무결성 검사입니다. 실제 복원 가능 여부는
아래 별도 DB 복원으로 검증합니다. 명령은 성공 시 JSON과 종료 코드 0, 실패 시 종료 코드 1을
반환하므로 스케줄러에서 실행 결과를 기록할 수 있습니다. 예약 작업과 보존 기간은 운영자가 설정합니다.

### 별도 DB에 복원하고 검증

운영 DB에 덮어쓰는 옵션은 없습니다. UTF-8의 비어 있는 전용 DB를 먼저 준비합니다.
예를 들어 테스트 DB는 다음과 같이 생성합니다.

```sh
docker compose exec database createdb -U ihda -T template0 -E UTF8 ihda_restore_check
```

`.env` 또는 셸 환경의 `IHDA_RESTORE_DATABASE_URL`을 새 DB로 설정합니다.
예: `postgresql+psycopg://ihda:<DB_PASSWORD>@database:5432/ihda_restore_check`
비밀번호를 명령 인수에 넣지 않습니다.

```sh
docker compose run --rm admin restore-backup /data/backups/team-20260915-0300 \
  --blob-destination /data/restored/check-20260915
```

복원 명령은 기본적으로 `IHDA_RESTORE_DATABASE_URL`만 사용합니다. 다른 환경 변수 이름은
`--target-url-env`로 지정합니다. 대상 DB에 테이블 등이 있거나 파일 경로가 이미 존재하면
거부합니다. `init-db`를 먼저 실행하지 않습니다. 기존 데이터 삭제·DB 생성은 자동 수행하지 않습니다.

덤프를 한 트랜잭션으로 복원한 뒤 모든 앱 테이블의 행 수·내용 해시와 파일 소유 정보를 비교합니다.
파일도 다시 복사·검사하고 성공한 경우에만 지정 경로를 공개합니다. 성공 시 `restore_verified`
결과와 파일 경로 안의 `.ihda-restore.json`을 남깁니다. 시퀀스도 덤프에 포함됩니다.
DB 복원 후 검사나 파일 공개가 실패하면 **새 대상 DB에 데이터가 남을 수 있습니다**.
해당 DB를 운영에 연결하지 말고 새 빈 DB와 새 경로로 다시 시도합니다. 원래 DB는 건드리지 않습니다.

재해 복구 전환은 검증 완료 후 API를 중지하고, 검증한 DB URL과 blob 경로/볼륨을 함께 연결해
실행합니다. 도구가 운영 서비스 설정을 자동 변경하지 않습니다. 테스트 복원은 별도의 API 인스턴스로
목록·이력·다운로드까지 확인할 수 있습니다. 백업 시점의 토큰 해시와 만료 정보도 복원됩니다.

지원 범위는 현재 앱의 전용 `public` 스키마와 앱 테이블·시퀀스·제약 조건 및 등록된 파일입니다.
DB 역할·서버 설정·TLS 키·외부 HIP/의존 파일은 별도 보관합니다. 추가 스키마/테이블이 있는 DB는
거부합니다. 파일 체크섬은 손상 검사용이며 서명이 아니므로 관리자가 신뢰하는 백업만 복원합니다.
백업에는 사용자와 라이브러리 데이터가 있으므로 접근 권한을 제한합니다.

구현 근거: [PostgreSQL 16의 동기화 스냅샷](https://www.postgresql.org/docs/16/functions-admin.html#FUNCTIONS-SNAPSHOT-SYNCHRONIZATION),
[pg_dump --snapshot](https://www.postgresql.org/docs/16/app-pgdump.html),
[pg_restore --single-transaction](https://www.postgresql.org/docs/16/app-pgrestore.html).

개인용은 기존 DB·에셋 백업에 더해 `.ihda-blobs`도 보관하면 보류 요청과 파일 참조를
복구할 수 있습니다. `.ihda-cache`와 메인 화면의 `cache/`는 다시 받을 수 있는 캐시입니다.
Houdini 노드 캡처의 임시 파일은 `workspace/staging/`에 남으므로 등록 결과 확인 후
정리할 수 있습니다. 기존 Library Tools의 백업 버튼은 팀 서버를 백업하지 않습니다.

## 확장할 위치와 SOLID 경계

| 책임 | 파일 |
| --- | --- |
| 기존 메인 UI·라이브러리 선택기 | `widgets/panel/layout.py`, `widgets/asset_browser/view.py` |
| 메인 화면·저장소 전환·작업 스레드 연결 | `widgets/team_library/integration.py` |
| 에셋 메뉴와 파일 선택 | `widgets/team_library/actions.py` |
| 서버 연결·구성원 설정 | `widgets/library_connection/` |
| 기존 모델용 데이터 변환·검색 | `libs/team/presentation.py`, `libs/team/search.py` |
| 선택·초안·저장·충돌·재시도 흐름 | `widgets/team_library/presenter.py` |
| 명령·응답·오류·파일 참조 계약 | `libs/team/contracts.py` |
| 개인 DB 어댑터 | `libs/team/personal.py` |
| HTTP 어댑터·검증 캐시 | `libs/team/client.py` |
| 불확실한 쓰기 보관 | `libs/team/pending.py` |
| API 경계·입력 검증 | `ihda_server/app.py` |
| 저장소·파일·인증을 주입받는 서비스 | `ihda_server/service.py` |
| PostgreSQL 트랜잭션·프로젝트 접근 제어 | `ihda_server/catalog.py` |
| 토큰 발급·검증 | `ihda_server/auth.py` |
| 테이블·스키마 수명주기 | `ihda_server/schema.py`, `database.py` |

Presenter는 Qt, SQL, HTTP, Houdini를 임포트하지 않고 작은 Protocol에 의존합니다.
개인/팀 어댑터는 동일 명령 계약 테스트로 대체 가능성을 확인합니다. 서버는 요청별
DB 연결·트랜잭션을 사용하고, 프로젝트 단위 잠금 안에서 권한·revision·중복 요청
기록을 함께 처리합니다. 현재는 프로젝트의 쓰기를 직렬화하여 정확성을 우선합니다.
규모가 커지면 계약을 유지하면서 잠금 범위를 줄이거나 파일 저장소를 객체 저장소로
교체할 수 있습니다. 사용자 인증도 주입된 Identity 경계에서 SSO로 확장할 수 있습니다.

## 검증

```sh
QT_QPA_PLATFORM=offscreen python -m pytest -q tests/test_team_library.py tests/test_team_workspace.py tests/test_main_team.py
```

실제 PostgreSQL 검증은 **테스트 전용 DB**를 지정합니다. 테스트는 임의 스키마를
생성·삭제하므로 해당 DB에서 그 권한이 필요합니다.

```sh
IHDA_TEST_POSTGRES_URL=postgresql+psycopg://USER:PASSWORD@localhost/ihda_test \
  QT_QPA_PLATFORM=offscreen python -m pytest -q tests/test_team_library.py
```

계약 테스트는 개인 SQLite/서버 양쪽의 등록·수정·버전·미디어·삭제와 충돌을 검증하고,
실제 loopback HTTP로 업로드·다운로드·인증·중복 요청을 검증합니다. Qt 테스트는
기존 개인 DB 연결, GUI 밖 저장, 초안 유지, 종료 후 콜백 차단, 재시도를 확인합니다.
Houdini에서 실제 선택 노드 캡처·썸네일·가져오기와 HTTPS 배포는 별도 수동 확인이
필요합니다.

## 데이터 기반 v2 업그레이드

개인 DB는 스키마 5, 팀 DB는 스키마 2 / HTTP API v2를 사용합니다. 앱과 서버를 함께
업그레이드하세요. 구버전 HTTP 요청은 426 응답으로 차단하며 클라이언트는 연결 시
API 버전을 확인합니다. 개인 DB는 처음 열 때 백업 후 단계별로 업그레이드합니다.
기존 ID, 파일 위치, 확장 필드와 과거 시각은 보존합니다. 식별하기 어려운 과거 버전과
시간대는 추측하지 않으며 `migration_reports`에 기록합니다.

기존 팀 서버는 다음 순서로 전환합니다.

1. 서버를 중지합니다.
2. PostgreSQL DB와 `IHDA_BLOB_ROOT`를 함께 백업합니다.
3. 새 서버 코드로 `python -m ihda_server.cli upgrade-db`를 실행합니다.
4. 새 서버를 시작하고 새 앱으로 접속합니다.

신규 설치에는 `init-db`를 사용합니다. 기존 스키마를 앱 시작 과정에서 변경하지 않습니다.
업그레이드 실패 시 원인을 해결한 후 같은 명령을 다시 실행할 수 있습니다.
다운그레이드는 DB·파일 저장소의 백업을 함께 복원하고 이전 서버/앱으로 돌아가는 방식입니다.

### 사용자에게 보이는 변화

- 즐겨찾기·최근 사용·사용 횟수는 사용자별 정보입니다. viewer도 즐겨찾기를 바꿀 수 있습니다.
  공용 에셋 편집과 충돌하지 않습니다. 사용 횟수는 Houdini 가져오기 성공 후 기록합니다.
- 기존 팀 공용 즐겨찾기는 업그레이드 시점 구성원 각자의 즐겨찾기로 복사합니다.
- `Library Tools → Trash…`에서 삭제 항목을 복원합니다. 파일은 자동 삭제하지 않습니다.
  팀 영구 삭제는 owner만 가능하며, 먼저 휴지통에 있는 항목을 선택해야 합니다.
- `Library Tools → Version details…`에서 선택한 에셋의 버전 설명·의존성을 편집하고
  활동 및 파일 점검 상태를 확인합니다. 제작 환경과 검증된 호환성은 같은 의미가 아닙니다.
- 팀 파일 등록 시 변경 설명을 입력할 수 있습니다. 개인용 버전 갱신 확인창의
  `Add a change description`을 선택하면 설명을 함께 저장합니다.
- 이름·미디어 변경은 활동으로 기록합니다. HDA를 새로 저장한 경우에만 새 버전을 만듭니다.
- 업그레이드 전 대기 요청은 자동 재전송하지 않습니다. 상태 표시의 `Review request`로
  내용을 확인하고 보관한 뒤 최신 에셋을 확인하여 필요한 변경만 다시 적용합니다.

### 파일 점검 및 명시적 정리

개인용 파일은 업그레이드 중 이동하거나 일괄 해시 계산하지 않습니다. 다음 명령으로
필요할 때 점검합니다. 누락·불일치 파일의 메타데이터도 보존합니다.

```sh
python -m libs.library_files check /path/to/ihda.db
python -m libs.library_files cleanup /path/to/ihda.db --asset-root /path/to/assets
# 후보를 확인한 뒤:
python -m libs.library_files cleanup /path/to/ihda.db --asset-root /path/to/assets --apply
```

팀용은 서버 환경변수 설정 후 다음 명령을 사용합니다.

```sh
python -m ihda_server.cli check-files
python -m ihda_server.cli cleanup-files
# 후보를 확인한 뒤:
python -m ihda_server.cli cleanup-files --apply
```

휴지통을 포함하여 참조가 남은 파일은 정리하지 않습니다. 팀 정리는 모든 프로젝트의
참조를 확인하고 업로드·에셋 변경과 잠금을 공유합니다. 실패한 제거는 파일과 등록 정보를
남겨 다음 실행에서 재시도합니다. 개인 정리는 영구 삭제로 정리 대기열에 들어간 파일 중
지정한 에셋 루트 안에 있고 다른 레코드가 참조하지 않는 파일만 제거합니다.
원본 HIP 파일과 루트 밖 경로는 제거하지 않습니다.

승인/배포 상태, 프리셋, 완전한 의존성 자동 탐색은 이번 구현 범위에
포함하지 않습니다. UUID·원본 참조·버전별 메타데이터를 확장 기반으로 사용합니다.
