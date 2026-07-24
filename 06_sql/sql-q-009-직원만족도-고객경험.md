---
date: 2026-07-24
category: SQL
data: "[[agents]], [[data_consultations]], [[data_satisfaction]]"
source_question: "[[q-009-직원만족도-고객경험]]"
tags: [만족도분석, 상담원분석, SQL]
---

[[q-009-직원만족도-고객경험]]에 답하기 위해 `charts/07`~`09`(및 `app.py`의 "상담원 관점" 섹션)가 BigQuery에서 조회한 내용을 정리한 노트. 실제 파이썬 코드는 원본 컬럼만 조회해 pandas로 집계했는데, 그 집계를 BigQuery SQL로 재현하면 아래와 같다. 테이블명은 `project.dataset.*`로 표기했으니 실제 프로젝트/데이터셋명(`hudson-bq-practice-2026.practice_dataset`)으로 바꿔서 사용한다.

## 1. 팀별 eNPS (charts/07 재현)

```sql
SELECT
  team,
  COUNT(*) AS n,
  COUNTIF(agent_satisfaction >= 9) AS promoters,
  COUNTIF(agent_satisfaction <= 6) AS detractors,
  ROUND(COUNTIF(agent_satisfaction >= 9) / COUNT(*) * 100
      - COUNTIF(agent_satisfaction <= 6) / COUNT(*) * 100, 1) AS enps
FROM `project.dataset.data_agents`
GROUP BY team

UNION ALL

SELECT
  '전체' AS team,
  COUNT(*) AS n,
  COUNTIF(agent_satisfaction >= 9) AS promoters,
  COUNTIF(agent_satisfaction <= 6) AS detractors,
  ROUND(COUNTIF(agent_satisfaction >= 9) / COUNT(*) * 100
      - COUNTIF(agent_satisfaction <= 6) / COUNT(*) * 100, 1) AS enps
FROM `project.dataset.data_agents`;
```

## 2. 상담원별 번아웃(초과근무)-CSAT (charts/08 재현)

```sql
WITH agent_csat AS (
  SELECT
    c.agent_id,
    ROUND(AVG(s.csat), 2) AS avg_csat
  FROM `project.dataset.data_consultations` c
  JOIN `project.dataset.data_satisfaction` s USING (consult_id)
  GROUP BY c.agent_id
)
SELECT
  a.agent_id,
  a.overtime_hours_avg,
  ac.avg_csat
FROM `project.dataset.data_agents` a
JOIN agent_csat ac USING (agent_id)
ORDER BY a.overtime_hours_avg;
```

상관계수(r)는 BigQuery의 `CORR()` 집계함수로도 바로 낼 수 있다: `SELECT CORR(a.overtime_hours_avg, ac.avg_csat) FROM ... `(위 쿼리를 서브쿼리로 감싸서 사용).

## 3. 교육이수 여부별 CSAT·재문의율 (charts/09 재현)

```sql
WITH agent_metrics AS (
  SELECT
    c.agent_id,
    AVG(s.csat) AS avg_csat,
    AVG(CASE WHEN c.is_recontact = 'Y' THEN 1.0 ELSE 0.0 END) * 100 AS recontact_rate
  FROM `project.dataset.data_consultations` c
  JOIN `project.dataset.data_satisfaction` s USING (consult_id)
  GROUP BY c.agent_id
)
SELECT
  a.training_completed_yn,
  COUNT(*) AS n_agents,
  ROUND(AVG(m.avg_csat), 3) AS avg_csat,
  ROUND(AVG(m.recontact_rate), 2) AS avg_recontact_rate
FROM `project.dataset.data_agents` a
JOIN agent_metrics m USING (agent_id)
GROUP BY a.training_completed_yn;
```

## 기술 노트

- 실제 `charts/07~09.py`는 위 집계를 BigQuery SQL이 아니라 원본 컬럼만 `SELECT`해서 pandas `groupby`/`corr`로 계산한다 — 결과 수치는 동일해야 하지만, 데이터가 커지면 이 노트의 SQL처럼 서버 측(BigQuery)에서 집계하는 편이 네트워크로 넘어오는 행 수를 줄여 더 효율적이다
- `data_agents` 테이블은 2026-07-23 기준 `raw/data_agents.csv`([[agents]] 참고)와 값이 일치함을 재검증한 상태 — 위 쿼리들의 결과는 그 스냅샷과 같아야 함

## 관련 질문

- [[q-009-직원만족도-고객경험]]
