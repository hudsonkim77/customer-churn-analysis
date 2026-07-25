# DEPLOY.md — 상담원 관점 섹션 배포 가이드

`app.py`의 "상담원 관점: 직원만족도와 고객 경험" 섹션은 BigQuery를 직접 조회한다. 이 문서는 그 조회가 로컬에서는 잘 되다가 배포 서버에서는 왜 깨질 수 있는지, 그리고 이 프로젝트가 그 문제를 어떻게 대응해뒀는지를 설명한다.

## 왜 이런 구조가 필요한가

- **로컬 ADC**: 이 컴퓨터에서 `gcloud auth application-default login`으로 로그인해두면, `google-cloud-bigquery` 클라이언트가 별다른 설정 없이 그 인증 정보(ADC)를 자동으로 찾아 쓴다. `%APPDATA%\gcloud\application_default_credentials.json`에 저장되며, **이 컴퓨터에만 있는 파일**이다.
- **배포 서버(Streamlit Cloud)**: 내 컴퓨터가 아니므로 이 ADC 파일이 없다. 아무 대응 없이 `bigquery.Client()`를 그대로 호출하면 배포 환경에서는 인증 에러로 앱이 멈춘다.
- **해결 방향**: "서비스 계정 키가 있으면 그걸로, 없으면(로컬처럼) ADC로, 그마저도 실패하면 미리 받아둔 로컬 스냅샷으로" — 3단계로 자동 전환하게 만들어서, 서비스 계정 키를 만들 수 있는 사람도 못 만드는 사람도 배포 자체는 똑같이 성공하게 한다.

```
로컬(개발 중)         배포 서버(Streamlit Cloud)
  ADC 있음               서비스 계정 키 있음 → 라이브 조회
    ↓                    서비스 계정 키 없음 → 인증 실패 → 스냅샷 폴백
🟢 BigQuery 라이브 조회
```

## 로컬에서 그냥 실행하면 어떻게 되는가

`streamlit run app.py`로 그냥 실행하면 `.streamlit/secrets.toml`이 없으므로 `st.secrets["gcp_service_account"]` 접근이 실패하고, 곧바로 기존 ADC로 인증을 시도한다. 이 컴퓨터엔 ADC가 있으므로 **🟢 BigQuery 라이브 데이터**로 정상 표시된다 — 지금까지와 동작이 같다.

ADC 자체를 못 찾게 만든 경우(예: `GOOGLE_APPLICATION_CREDENTIALS` 환경변수를 존재하지 않는 경로로 지정하고 실행)에는 라이브 조회가 실패하고 자동으로 `data/agents_snapshot.csv`, `data/agent_consultations_snapshot.csv`를 읽어 **🟡 로컬 스냅샷 데이터(생성일 기준)** 배지와 함께 표시된다. 둘 다 정상 동작이며, 에러 화면은 뜨지 않아야 한다.

## 코드 구조

- `get_bigquery_client()` — `st.secrets["gcp_service_account"]`가 있으면 그 서비스 계정으로, 없거나 실패하면(예외를 폭넓게 잡음) ADC로 `bigquery.Client`를 생성한다.
- `load_agent_data()` — `get_bigquery_client()`로 상담원 단위(`data_agents`)·상담 단위(`data_consultations` ⋈ `data_satisfaction`) 쿼리를 라이브로 시도하고, 어떤 이유로든(인증 실패·네트워크 오류 등) 실패하면 `data/agents_snapshot.csv`·`data/agent_consultations_snapshot.csv`를 대신 읽는다. `("live"|"snapshot", 스냅샷 날짜)`를 함께 반환해 화면에 배지로 표시할 수 있게 한다.
- 스냅샷 CSV는 `training_completed_yn`·`is_recontact`를 BigQuery의 boolean이 아니라 raw CSV와 같은 `Y`/`N` 문자열로 저장해, 라이브/스냅샷 어느 쪽에서 와도 차트 함수가 같은 형식을 받도록 맞춰뒀다.

## Streamlit Cloud 배포 순서 (GitHub push → 배포)

1. 이 저장소를 GitHub에 push (이미 되어 있음: `hudsonkim77/customer-churn-analysis`)
2. `requirements.txt`에 `google-cloud-bigquery`, `db-dtypes`, `google-auth`가 포함되어 있는지 확인(이미 추가됨) — 없으면 배포 서버에서 `import` 자체가 실패한다
3. Streamlit Community Cloud에서 앱을 최초 배포하거나, 이미 배포되어 있다면 `git push`만으로 자동 재배포된다
4. (선택) 서비스 계정 키를 아래 "Secrets 등록 방법"대로 등록하면 배포 서버에서도 🟢 라이브 조회가 가능해진다. 등록하지 않으면 🟡 스냅샷으로 표시되며, 이 역시 정상 동작이다

## (선택) Streamlit Secrets에 서비스 계정 키 등록하는 방법

BigQuery 서비스 계정 키를 만들 수 있는 사람만 해당한다.

1. GCP 콘솔 → IAM 및 관리자 → 서비스 계정 → 새 서비스 계정 생성(또는 기존 계정 사용), `BigQuery 데이터 뷰어`·`BigQuery 작업 사용자` 역할 부여
2. 해당 서비스 계정의 키(JSON) 생성·다운로드
3. Streamlit Cloud 앱 관리 화면 → Settings → Secrets에 아래 형식으로 붙여넣기(JSON 키 파일의 각 필드를 그대로 옮김):

```toml
[gcp_service_account]
type = "service_account"
project_id = "hudson-bq-practice-2026"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "...@....iam.gserviceaccount.com"
client_id = "..."
token_uri = "https://oauth2.googleapis.com/token"
```

4. 저장하면 앱이 재시작되며, 이후부터는 배포 서버에서도 🟢 라이브 데이터가 표시된다
5. 로컬에서 이 경로를 테스트하고 싶다면 저장소 루트에 `.streamlit/secrets.toml`을 같은 형식으로 만들면 된다(단, 이 파일은 `.gitignore`에 넣어 커밋하지 말 것 — 실제 키가 들어가는 파일이다)

## 자주 겪을 만한 문제와 해결법

| 증상 | 원인 | 해결 |
|---|---|---|
| 배포 서버에서 앱 전체가 크래시(ImportError) | `requirements.txt`에 `google-cloud-bigquery` 등이 빠짐 | `requirements.txt` 확인 후 재배포 |
| 로컬에서 잘 되던 게 배포하면 🟡만 계속 뜸 | 서비스 계정 키를 Secrets에 등록 안 함 | 정상 동작. 라이브로 보고 싶으면 위 "Secrets 등록 방법" 진행 |
| 🟡 스냅샷 데이터가 최신 값과 다름 | 스냅샷은 생성 시점의 "사진" — BigQuery 실제 값이 이후 바뀌어도 스냅샷은 그대로 | 배지에 표시된 생성일 확인, 필요하면 스냅샷 재생성(`agents`·`agent_consultations` 쿼리를 다시 실행해 `data/*_snapshot.csv` 갱신) |
| `secrets.toml`을 로컬에 만들었는데 오히려 에러 남 | 키 형식이 틀렸거나 만료됨, 그런데도 ADC로 안 넘어감 | `get_bigquery_client()`의 except가 모든 예외를 넓게 잡고 있는지 확인(특정 예외 타입만 잡으면 이런 경우 못 잡음) |
| 팀 필터 선택 후 잠깐 느려짐 | `load_agent_data()`가 매번 새로 조회 | `@st.cache_data(ttl=600)`로 10분간 캐시하게 되어 있음 — 최초 1회만 느리고 이후는 캐시 사용 |

## 검증 기록 (2026-07-25)

- 로컬에서 그냥 실행 → 🟢 BigQuery 라이브 데이터, eNPS -45(전체) 등 기존 값과 정확히 일치 확인
- `GOOGLE_APPLICATION_CREDENTIALS`를 존재하지 않는 경로로 지정하고 실행 → 🟡 로컬 스냅샷 데이터(07월 25일 기준)로 자동 전환, 팀 필터(3팀 등) 전환도 에러 없이 정상 작동 확인
