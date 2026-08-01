# design.md — 이 프로젝트(3주차)의 디자인 원칙

`customer-churn-dashboard-web/design.md`에 이 시각 언어의 전체 이력(네온 3색 그룹핑의 기원,
다크 아우로라, 글래스모피즘 등)이 자세히 기록돼 있다. 이 문서는 그중 **이 Streamlit
프로젝트(`app.py`) 자체에 실제로 적용된 부분**만 정리한다 — React 프로젝트 쪽 문서와 중복 서술하지
않는다.

## 1. 다크 테마 — 네이티브 설정

`.streamlit/config.toml`에 실제 `[theme] base="dark"`를 설정해뒀다(직접 CSS로 흉내내지 않음 —
이유는 4주차 `design.md` §6 참고, 같은 원칙을 여기서도 따른다).

```toml
[theme]
base = "dark"
primaryColor = "#3987e5"
backgroundColor = "#0d0d0d"
secondaryBackgroundColor = "#1a1a19"
textColor = "#ffffff"
```

## 2. 네온 3색 그룹핑 — 이 프로젝트가 기원

`render_report_with_toc()`(개선 제안 리포트 탭 목차)에서 섹션 번호대별로 네온 그린(1-3)/네온
핑크(4-6)/네온 시안(7-8) 3색(`REPORT_SECTION_GROUPS = {"a": "#3bffa0", "b": "#ff4fd8", "c":
"#33e0ff"}`)을 쓴 게 이 시각 언어의 시작점이다. 이후 `customer-churn-dashboard-web`과
`4주차`(마케팅 채널 효율)가 이 3색을 그대로 재사용했다.

## 3. 차트 색상 — Emphasis 패턴 (dataviz 스킬 원칙과 사후적으로 일치)

`chart_voc_churn`·`chart_plan_churn`·`chart_region_churn` 등은 전체 카테고리를 파란색
(`#3987e5`)으로 두고, **이탈율이 가장 높은 막대 하나만** 빨간색(`#d03b3b`)으로 강조한다. 이건
4주차에서 `dataviz` 스킬을 확인하고 정식화한 "Emphasis 패턴(하나만 강조, 나머지는 무채색/기본색)"과
같은 원칙이다 — 이 프로젝트가 먼저 그렇게 만들어져 있었고, 스킬 확인 후 원칙에 이름이 붙은 셈이다.
앞으로 이 프로젝트에 차트를 추가할 때도 이 패턴(명목 카테고리엔 값-그라데이션 금지, 극단값만 강조)을
유지한다.

## 4. 사이드바 프로젝트 메뉴 — 4주차에서 표준화한 패턴 이식

2·3·4주차가 한 시리즈라는 사용자 요청으로, 사이드바에 세 프로젝트를 오가는 메뉴를 추가했다
(4주차 `design.md` §7 참고). 이 프로젝트가 "3주차·현재"로 표시된다.

- 배경 `#2a2a30` + 우측 경계선으로 본문과 시각적으로 분리
- `st.link_button`은 `<a>` 태그로 렌더링되므로, 좌측 정렬 CSS는
  `[data-testid^="stBaseButton"], [data-testid^="stBaseLinkButton"]`처럼 두 testid 접두사를
  모두 잡아야 한다(하나만 잡으면 링크 버튼만 중앙정렬로 남는 버그가 남)
- 메뉴 배지 색은 이 프로젝트 고유의 네온 그린을 그대로 사용(§2와 통일)

## 5. 가져오지 않은 것

React 쪽의 애니메이션(등장 페이드인, elastic 전환)·다크/라이트 토글·aurora 배경 애니메이션은 이
프로젝트에도 적용하지 않았다 — 이유는 4주차 `design.md` §3과 동일(Streamlit 컴포넌트 구조상
제약, 이 프로젝트 규모 대비 과함).
