# DEPLOY.md — 상담원 관점 섹션 배포 가이드

`app.py`의 "상담원 관점: 직원만족도와 고객 경험" 섹션은 **항상 로컬 스냅샷 CSV만 사용한다** (2026-07-25 변경, 아래 "왜 라이브 조회를 없앴는가" 참고). BigQuery를 직접 조회하지 않으므로 서비스 계정 키·ADC·Secrets 설정이 전혀 필요 없다.

## 현재 구조

- `load_agent_data()` — `data/agents_snapshot.csv`, `data/agent_consultations_snapshot.csv`를 그대로 읽어 반환한다. `@st.cache_data`로 캐시되어 세션당 한 번만 읽는다.
- 화면에는 `🟡 스냅샷 데이터(생성일 기준) — 로딩 속도를 위해 항상 스냅샷을 사용합니다` 배지가 항상 표시된다.
- 스냅샷 데이터를 갱신하려면 BigQuery에서 `data_agents`·`data_consultations`⋈`data_satisfaction`을 다시 조회해 `data/agents_snapshot.csv`·`data/agent_consultations_snapshot.csv`를 덮어쓰면 된다 (Y/N 문자열 형식 유지).

## 왜 라이브 조회를 없앴는가 (2026-07-25)

이전에는 "서비스 계정 키가 있으면 라이브 조회, 없으면 ADC, 그마저 실패하면 스냅샷"으로 자동 전환하는 3단계 구조였다(아래 "이전 구조(폐기됨)" 참고). 문제는:

- Streamlit Cloud에는 서비스 계정 키를 등록하지 않아 항상 스냅샷으로 귀결되는데, 그 판단에 도달하기까지 매번 `bigquery.Client()` 생성과 실패하는 쿼리 시도가 실행되어 **불필요한 로딩 지연**이 계속 쌓였다.
- 실사용(시연) 중 로딩이 오래 걸려 실패한 사례가 있었음 — 콜드 스타트(Streamlit Cloud 무료 티어의 앱 재기동 지연)에 이 불필요한 라이브 시도 지연까지 겹쳐 체감 로딩 시간이 더 늘어난 것으로 판단.
- 실제로 배포 환경에서 라이브 조회가 성공한 적이 없었으므로(서비스 계정 키 미등록), 이 경로를 유지할 실익이 없었다.

그래서 `get_bigquery_client()`·`_to_yn()`·`load_agent_data()`의 라이브 조회 분기를 전부 제거하고, 항상 스냅샷만 읽도록 단순화했다. `requirements.txt`에서도 `google-cloud-bigquery`·`db-dtypes`·`google-auth`를 제거해 배포 빌드 자체도 가벼워졌다.

## 이전 구조 (폐기됨, 이력만 남김)

<details>
<summary>2026-07-25 이전에 쓰던 라이브/스냅샷 3단계 폴백 구조 (더 이상 사용하지 않음)</summary>

- **로컬 ADC**: `gcloud auth application-default login`으로 로그인해두면 `google-cloud-bigquery` 클라이언트가 자동으로 그 인증 정보를 찾아 썼다.
- **배포 서버(Streamlit Cloud)**: ADC 파일이 없어, 서비스 계정 키를 Secrets에 등록하지 않으면 인증이 항상 실패 → 스냅샷 폴백.
- `get_bigquery_client()`가 `st.secrets["gcp_service_account"]`를 먼저 찾고, 없으면 ADC로 시도하는 함수였음.
- `load_agent_data()`가 라이브 쿼리를 시도하고 실패 시 스냅샷을 읽으며 `("live"|"snapshot", 날짜)`를 반환해 🟢/🟡 배지로 구분 표시했음.
- Streamlit Secrets에 서비스 계정 키(JSON)를 등록하면 배포 서버에서도 🟢 라이브 조회가 가능했음 — 실제로는 한 번도 등록한 적 없어 배포 환경은 항상 🟡였음.

</details>

## 자주 겪을 만한 문제와 해결법

| 증상 | 원인 | 해결 |
|---|---|---|
| 🟡 스냅샷 데이터가 최신 값과 다름 | 스냅샷은 생성 시점의 "사진" — BigQuery 실제 값이 이후 바뀌어도 스냅샷은 그대로 | 배지에 표시된 생성일 확인, 필요하면 스냅샷 재생성(`agents`·`agent_consultations` 쿼리를 다시 실행해 `data/*_snapshot.csv` 갱신) |
| 리포트 탭 목차 클릭 시 대제목이 안 보이고 스크롤이 지나쳐 버림 | Streamlit 상단 고정 바(Deploy/메뉴)에 앵커 대상이 가려짐 | `render_report_with_toc()`의 `.report-toc`·`.report-heading-row`에 `scroll-margin-top: 4.5rem`을 넣어 앵커 이동 시 여백을 확보하도록 수정(2026-07-25) |
| 앱 전체 로딩이 느림(특히 시연 중) | Streamlit Cloud 무료 티어 콜드 스타트(비활성 상태였다가 깨어나는 지연, 보통 20~60초) | 코드 문제가 아님. 몇 분 내 재접속하면 빨라짐. 위 라이브 조회 제거로 콜드 스타트 위의 추가 지연은 없앴음 |

## 검증 기록

- **2026-07-25**: 라이브 조회 제거 후 로컬 재실행 → 🟡 스냅샷 배지 정상 표시, 팀 필터(전체/1팀/2팀/3팀) 전환 정상, 대시보드 탭 차트 9개·리포트 탭(10,985자) 회귀 없음, 콘솔 에러 없음. 리포트 목차 앵커 이동도 대제목이 가려지지 않고 정상 표시됨.

## 관련 문서 — 시리즈 공통 배포 원칙

2·3(이 프로젝트)·4주차가 한 시리즈로 묶이면서, 배포 관련 원칙은 `../4주차/deploy.md`에
공통으로 정리해뒀다(git init→GitHub→Streamlit Cloud 배포 절차, BigQuery 무료 티어 DML 제약과
우회법, Private 저장소 배포 시 GitHub OAuth 권한 문제 등). 이 문서(`DEPLOY.md`)는 그 원칙을
"상담원 관점 섹션"이라는 이 프로젝트 특정 사례에 처음 적용했던 이력이자, 같은 원칙("라이브 시도
자체가 배포 환경에서는 지연 비용")이 처음 발견된 자리다 — 4주차의 `FORCE_SNAPSHOT` 기본값 설계도
이 문서의 결론을 그대로 이어받은 것이다.

2026-08-01부터는 사이드바에 2·3·4주차를 오가는 프로젝트 메뉴도 추가됐다(`design.md` §4 참고).

같은 날, 그 사이드바 메뉴의 좌측 정렬 CSS가 배포 화면에서 실제로는 안 먹히던 문제를 겪으며
"CSS 수정이 안 먹힐 때는 스크린샷 재확인이 아니라 DOM을 실제로 순회해서 확인한다"는 일반 원칙이
나왔다 — `../4주차/deploy.md` §6에 정리, 이 프로젝트의 실제 사례는 `design.md` §4에 있다.
