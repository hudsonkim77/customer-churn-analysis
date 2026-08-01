---
date: 2026-07-30
category: 설계
data: data_retention_campaign
tags: [캠페인, 이탈방지, 리텐션]
source: "[[raw/data_retention_campaign_clean.csv]] (아직 raw/ 미편입 — 원본 `data_retention_campaign_raw.csv`, 정제본 경로는 [[2026-07-25]] 로그 기준이나 현재 홈 디렉토리에서 재확인 안 됨. 정제 내역은 `정제_규칙.md` 참고)"
status: "설계 진행 중 — 컬럼 정의 표만 작성됨. 그레인·연결 키·정합성 규칙·심을 패턴 섹션은 아직 없음"
---

# 리텐션 캠페인 테이블 설계서

## 개요

고객 리텐션(이탈 방지) 캠페인 발송·응답·전환 로그. 원본 500행, 정제 후 481행(완전중복 15행 + 참조무결성 위반 4행 제거). [[manager_note]]의 VIP 응대 개선 예고, [[i-009-이탈방지-처방]]과 실증적으로 연결될 가능성이 있는 데이터로 보임(추정 — 미확정).

## 컬럼 정의 표

| 컬럼명 | 타입 | 의미 |
|---|---|---|
| log_id | STRING | 캠페인 발송 로그 ID(PK). 정제 후 완전중복 제거로 유일성 확보 |
| customer_id | STRING | 고객 ID(FK → [[data_customers]]). 정제 후 유효 범위(C001~C500) 내로 제한됨 |
| send_date | DATE | 제안 발송일. ISO(`YYYY-MM-DD`)로 통일 |
| channel | STRING | 발송 채널. 값 4종: 문자 / 이메일 / 앱푸시 / 전화 |
| offer_type | STRING | 제안 유형. 값 3종: 할인 / 포인트 / 사은품 |
| discount_pct | INTEGER | 할인율(%). 0~100 정수. `offer_type`이 할인이 아니면 구조적 결측으로 `해당없음` |
| response_date | DATE | 고객 응답일. ISO 통일. 미응답이거나 `send_date`보다 이르면 결측 처리 |
| responded_yn | STRING (Y/N) | 응답 여부. `response_date` 유무 기준으로 재계산된 값 |
| converted_yn | STRING (Y/N/해당없음) | 전환(수락·유지) 여부. `9999`·`N/A` 등 비정상값은 `해당없음` |
| agent_id | STRING | 담당 상담원 ID(FK → [[agents]]). 전화 채널만 해당, 그 외는 `해당없음`. 대문자 통일, AG01~AG20 범위 |

## 비고

- 근거: `정제_규칙.md`의 [정제규칙]·[정제실행]·[결과검증] 섹션.
- 이 노트는 day2 설계서 항목 중 컬럼 정의 표만 우선 채운 상태다. 그레인 명시("한 행 = ___ 1개"), 연결 키 정리, 정합성 규칙(5개 이상), 심을 패턴, 미생성/생성 상태 표기는 아직 작성되지 않음.
