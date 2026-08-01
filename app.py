import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from report_pdf import build_report_pdf

RAW = Path(__file__).parent / "raw"
DATA_DIR = Path(__file__).parent / "data"
REACT_DASHBOARD_URL = "https://customer-churn-dashboard-web-jpfl.vercel.app"


@st.cache_data
def load_data():
    consultations = pd.concat(
        [
            pd.read_csv(RAW / "data_consultations.csv", encoding="utf-8-sig"),
            pd.read_csv(DATA_DIR / "data_consultations_2025_snapshot.csv", encoding="utf-8-sig"),
        ],
        ignore_index=True,
    )
    return {
        "customers": pd.read_csv(RAW / "data_customers.csv", encoding="utf-8-sig"),
        "voc": pd.read_csv(RAW / "data_voc.csv", encoding="utf-8-sig"),
        "consultations": consultations,
        "satisfaction": pd.read_csv(RAW / "data_satisfaction.csv", encoding="utf-8-sig"),
        "usage": pd.read_csv(RAW / "data_usage_history.csv", encoding="utf-8-sig"),
    }


@st.cache_data
def load_agent_data():
    """상담원 관점 섹션 데이터: 로딩 속도를 위해 BigQuery 라이브 조회 없이
    항상 로컬 스냅샷 CSV만 사용한다 (배포 환경 콜드 스타트 지연 원인이었음, DEPLOY.md 참고)."""
    agents = pd.read_csv(DATA_DIR / "agents_snapshot.csv", encoding="utf-8-sig")
    agent_consultations = pd.read_csv(
        DATA_DIR / "agent_consultations_snapshot.csv", encoding="utf-8-sig"
    )
    snapshot_date = datetime.fromtimestamp(
        (DATA_DIR / "agents_snapshot.csv").stat().st_mtime
    ).strftime("%m월 %d일")
    return agents, agent_consultations, snapshot_date


def chart_voc_churn(customers, voc):
    target_ids = voc.loc[
        (voc["category"] == "해지관련") & (voc["sentiment"] == "부정"), "customer_id"
    ].unique()

    overall_n = len(customers)
    overall_churned = int((customers["churn_yn"] == "Y").sum())
    overall_rate = round(100 * overall_churned / overall_n, 1)

    target_customers = customers[customers["customer_id"].isin(target_ids)]
    target_n = len(target_customers)
    target_churned = int((target_customers["churn_yn"] == "Y").sum())
    target_rate = round(100 * target_churned / target_n, 1) if target_n else 0.0

    df = pd.DataFrame(
        {
            "group": ["전체 고객", "해지관련 부정 VOC 이력 있음"],
            "churn_rate": [overall_rate, target_rate],
            "n_customers": [overall_n, target_n],
            "n_churned": [overall_churned, target_churned],
        }
    )

    fig = px.bar(
        df,
        x="group",
        y="churn_rate",
        color="group",
        color_discrete_map={
            "전체 고객": "#3987e5",
            "해지관련 부정 VOC 이력 있음": "#d03b3b",
        },
        custom_data=["n_customers", "n_churned"],
        labels={"churn_rate": "이탈율 (%)", "group": ""},
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{x}</b><br>고객 수: %{customdata[0]}명<br>"
            "이탈 고객 수: %{customdata[1]}명<br>이탈율: %{y}%<extra></extra>"
        )
    )
    fig.update_layout(
        showlegend=False,
        paper_bgcolor="#1a1a19",
        plot_bgcolor="#1a1a19",
        font_color="#ffffff",
        xaxis=dict(gridcolor="#2c2c2a", linecolor="#383835"),
        yaxis=dict(gridcolor="#2c2c2a", linecolor="#383835"),
    )
    return fig


def chart_channel_csat_recontact(consultations, satisfaction):
    merged = satisfaction.merge(
        consultations[["consult_id", "channel"]], on="consult_id", how="inner"
    )
    csat_by_channel = merged.groupby("channel")["csat"].mean().round(2).rename("avg_csat")
    recontact_by_channel = (
        consultations.groupby("channel")["is_recontact"]
        .apply(lambda s: round(100 * (s == "Y").mean(), 1))
        .rename("recontact_rate")
    )
    result = pd.concat([csat_by_channel, recontact_by_channel], axis=1).reset_index()
    result = result.sort_values("avg_csat", ascending=True)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=result["channel"],
            y=result["avg_csat"],
            name="평균 CSAT",
            yaxis="y1",
            marker_color="#3987e5",
            hovertemplate="채널: %{x}<br>평균 CSAT: %{y}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=result["channel"],
            y=result["recontact_rate"],
            name="재문의율(%)",
            yaxis="y2",
            mode="lines+markers",
            line=dict(color="#d03b3b"),
            marker=dict(color="#d03b3b"),
            hovertemplate="채널: %{x}<br>재문의율: %{y}%<extra></extra>",
        )
    )
    fig.update_layout(
        xaxis=dict(
            title="채널",
            categoryorder="array",
            categoryarray=result["channel"],
            gridcolor="#2c2c2a",
            linecolor="#383835",
        ),
        yaxis=dict(title="평균 CSAT", side="left", gridcolor="#2c2c2a", linecolor="#383835"),
        yaxis2=dict(title="재문의율 (%)", side="right", overlaying="y", gridcolor="#2c2c2a"),
        hovermode="x unified",
        paper_bgcolor="#1a1a19",
        plot_bgcolor="#1a1a19",
        font_color="#ffffff",
    )
    return fig


def chart_recontact_bucket_churn(consultations, customers):
    recontact_counts = (
        consultations[consultations["is_recontact"] == "Y"]
        .groupby("customer_id")
        .size()
        .rename("recontact_count")
    )
    df = customers.merge(recontact_counts, on="customer_id", how="left")
    df["recontact_count"] = df["recontact_count"].fillna(0).astype(int)

    def bucket(n):
        if n == 0:
            return "0회"
        elif n == 1:
            return "1회"
        return "2회 이상"

    df["bucket"] = df["recontact_count"].apply(bucket)
    overall_rate = round(100 * (customers["churn_yn"] == "Y").mean(), 1)

    order = ["0회", "1회", "2회 이상"]
    summary = (
        df.groupby("bucket")
        .agg(n=("customer_id", "count"), churned=("churn_yn", lambda s: int((s == "Y").sum())))
        .reindex(order)
        .reset_index()
    )
    summary["churn_rate"] = round(100 * summary["churned"] / summary["n"], 1)

    fig = px.bar(
        summary,
        x="bucket",
        y="churn_rate",
        color="bucket",
        color_discrete_map={"0회": "#3987e5", "1회": "#3987e5", "2회 이상": "#d03b3b"},
        custom_data=["n", "churned"],
        labels={"churn_rate": "이탈율 (%)", "bucket": "재문의 횟수"},
        category_orders={"bucket": order},
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{x}</b><br>고객 수: %{customdata[0]}명<br>"
            "이탈 고객 수: %{customdata[1]}명<br>이탈율: %{y}%<extra></extra>"
        )
    )
    fig.add_hline(
        y=overall_rate,
        line_dash="dash",
        line_color="#898781",
        annotation_text=f"전체 평균 이탈율 {overall_rate}%",
        annotation_position="top left",
        annotation_font_color="#c3c2b7",
    )
    fig.update_layout(
        showlegend=False,
        paper_bgcolor="#1a1a19",
        plot_bgcolor="#1a1a19",
        font_color="#ffffff",
        xaxis=dict(gridcolor="#2c2c2a", linecolor="#383835"),
        yaxis=dict(gridcolor="#2c2c2a", linecolor="#383835"),
    )
    return fig


def chart_plan_churn(customers):
    summary = (
        customers.groupby("plan")
        .agg(n=("customer_id", "count"), churned=("churn_yn", lambda s: int((s == "Y").sum())))
        .reset_index()
    )
    summary["churn_rate"] = round(100 * summary["churned"] / summary["n"], 1)
    summary = summary.sort_values("churn_rate", ascending=False)
    max_rate_plan = summary.iloc[0]["plan"]
    color_map = {p: ("#d03b3b" if p == max_rate_plan else "#3987e5") for p in summary["plan"]}

    fig = px.bar(
        summary,
        x="plan",
        y="churn_rate",
        color="plan",
        color_discrete_map=color_map,
        custom_data=["n", "churned"],
        labels={"churn_rate": "이탈율 (%)", "plan": "요금제"},
        category_orders={"plan": list(summary["plan"])},
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{x}</b><br>고객 수: %{customdata[0]}명<br>"
            "이탈 고객 수: %{customdata[1]}명<br>이탈율: %{y}%<extra></extra>"
        )
    )
    fig.update_layout(
        showlegend=False,
        paper_bgcolor="#1a1a19",
        plot_bgcolor="#1a1a19",
        font_color="#ffffff",
        xaxis=dict(gridcolor="#2c2c2a", linecolor="#383835"),
        yaxis=dict(gridcolor="#2c2c2a", linecolor="#383835"),
    )
    return fig


def chart_region_churn(customers):
    summary = (
        customers.groupby("region")
        .agg(n=("customer_id", "count"), churned=("churn_yn", lambda s: int((s == "Y").sum())))
        .reset_index()
    )
    summary["churn_rate"] = round(100 * summary["churned"] / summary["n"], 1)
    summary = summary.sort_values("churn_rate", ascending=False)
    max_rate_region = summary.iloc[0]["region"]
    color_map = {r: ("#d03b3b" if r == max_rate_region else "#3987e5") for r in summary["region"]}

    fig = px.bar(
        summary,
        x="region",
        y="churn_rate",
        color="region",
        color_discrete_map=color_map,
        custom_data=["n", "churned"],
        labels={"churn_rate": "이탈율 (%)", "region": "지역"},
        category_orders={"region": list(summary["region"])},
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{x}</b><br>고객 수: %{customdata[0]}명<br>"
            "이탈 고객 수: %{customdata[1]}명<br>이탈율: %{y}%<extra></extra>"
        )
    )
    fig.update_layout(
        showlegend=False,
        paper_bgcolor="#1a1a19",
        plot_bgcolor="#1a1a19",
        font_color="#ffffff",
        xaxis=dict(gridcolor="#2c2c2a", linecolor="#383835"),
        yaxis=dict(gridcolor="#2c2c2a", linecolor="#383835"),
    )
    return fig


def chart_tenure_usage_scatter(customers, usage):
    customers = customers.copy()
    customers["join_date"] = pd.to_datetime(customers["join_date"])
    cutoff = pd.Timestamp("2024-12-31")
    customers["tenure_months"] = (
        (cutoff.year - customers["join_date"].dt.year) * 12
        + (cutoff.month - customers["join_date"].dt.month)
    )
    avg_usage = usage.groupby("customer_id")["data_gb"].mean().round(2).rename("avg_data_gb")
    df = customers.merge(avg_usage, on="customer_id", how="left")

    fig = px.scatter(
        df,
        x="tenure_months",
        y="avg_data_gb",
        color="churn_yn",
        color_discrete_map={"Y": "#d03b3b", "N": "#3987e5"},
        custom_data=["customer_id", "tenure_months", "avg_data_gb", "churn_yn"],
        labels={
            "tenure_months": "가입기간 (개월)",
            "avg_data_gb": "평균 데이터 사용량 (GB)",
            "churn_yn": "이탈 여부",
        },
    )
    fig.update_traces(
        hovertemplate=(
            "고객ID: %{customdata[0]}<br>가입기간: %{customdata[1]}개월<br>"
            "평균 데이터 사용량: %{customdata[2]}GB<br>이탈 여부: %{customdata[3]}<extra></extra>"
        )
    )
    fig.update_layout(
        paper_bgcolor="#1a1a19",
        plot_bgcolor="#1a1a19",
        font_color="#ffffff",
        xaxis=dict(gridcolor="#2c2c2a", linecolor="#383835"),
        yaxis=dict(gridcolor="#2c2c2a", linecolor="#383835"),
    )
    return fig


def chart_agent_enps(agents):
    BLUE, RED, TEXT = "#3987e5", "#d03b3b", "#ffffff"

    def classify(score):
        if score >= 9:
            return "promoter"
        elif score >= 7:
            return "passive"
        return "detractor"

    n = len(agents)
    if n == 0:
        enps = 0.0
    else:
        cls = agents["agent_satisfaction"].apply(classify)
        enps = round(100 * (cls == "promoter").sum() / n - 100 * (cls == "detractor").sum() / n, 1)

    color = RED if enps < 0 else BLUE
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=enps,
            title={"text": "eNPS", "font": {"color": TEXT, "size": 20}},
            number={"font": {"color": color, "size": 40}},
            gauge={
                "axis": {"range": [-100, 100], "tickcolor": TEXT},
                "bar": {"color": color},
                "steps": [
                    {"range": [-100, 0], "color": "rgba(208, 59, 59, 0.25)"},
                    {"range": [0, 100], "color": "rgba(57, 135, 229, 0.15)"},
                ],
                "threshold": {"line": {"color": TEXT, "width": 2}, "thickness": 0.8, "value": enps},
            },
        )
    )
    fig.update_layout(
        paper_bgcolor="#1a1a19",
        plot_bgcolor="#1a1a19",
        font_color=TEXT,
        height=320,
    )
    return fig


def chart_agent_burnout_csat(agents, agent_consultations):
    BLUE, TEXT = "#3987e5", "#ffffff"

    avg_csat = (
        agent_consultations.groupby("agent_id")["csat"]
        .mean()
        .round(2)
        .rename("avg_csat")
        .reset_index()
    )
    df = agents.merge(avg_csat, on="agent_id", how="inner")

    fig = px.scatter(
        df,
        x="overtime_hours_avg",
        y="avg_csat",
        trendline="ols" if len(df) >= 2 else None,
        custom_data=["agent_id", "overtime_hours_avg", "avg_csat"],
        labels={"overtime_hours_avg": "평균 초과근무 시간(월, 시간)", "avg_csat": "상담원별 CSAT 평균"},
        color_discrete_sequence=[BLUE],
    )
    fig.update_traces(
        hovertemplate=(
            "agent_id: %{customdata[0]}<br>초과근무 시간: %{customdata[1]}시간<br>"
            "CSAT 평균: %{customdata[2]}<extra></extra>"
        ),
        selector=dict(mode="markers"),
    )
    if len(df) >= 2 and df["overtime_hours_avg"].std() > 0:
        r = round(df["overtime_hours_avg"].corr(df["avg_csat"]), 2)
        fig.add_annotation(
            xref="paper",
            yref="paper",
            x=0.98,
            y=0.98,
            text=f"r = {r}",
            showarrow=False,
            font=dict(size=16, color=TEXT),
            bgcolor="rgba(255,255,255,0.08)",
            bordercolor=TEXT,
            borderwidth=1,
        )
    fig.update_layout(
        paper_bgcolor="#1a1a19",
        plot_bgcolor="#1a1a19",
        font_color=TEXT,
        height=320,
        xaxis=dict(gridcolor="#2c2c2a", linecolor="#383835"),
        yaxis=dict(gridcolor="#2c2c2a", linecolor="#383835"),
    )
    return fig


def chart_agent_training_comparison(agents, agent_consultations):
    BLUE, GRAY, TEXT = "#3987e5", "#898781", "#ffffff"

    avg_csat = agent_consultations.groupby("agent_id")["csat"].mean().rename("avg_csat")
    recontact_rate = (
        agent_consultations.groupby("agent_id")["is_recontact"]
        .apply(lambda s: round(100 * (s == "Y").mean(), 2))
        .rename("recontact_rate")
    )
    df = agents.merge(avg_csat, on="agent_id").merge(recontact_rate, on="agent_id")

    csat_by_group = df.groupby("training_completed_yn")["avg_csat"].mean().round(3)
    recontact_by_group = df.groupby("training_completed_yn")["recontact_rate"].mean().round(2)

    labels = ["N (미이수)", "Y (교육이수)"]
    colors = [GRAY, BLUE]
    csat_values = [
        round(csat_by_group.get("N", float("nan")), 3),
        round(csat_by_group.get("Y", float("nan")), 3),
    ]
    recontact_values = [
        round(recontact_by_group.get("N", float("nan")), 2),
        round(recontact_by_group.get("Y", float("nan")), 2),
    ]

    fig = make_subplots(rows=1, cols=2, subplot_titles=("CSAT 평균", "재문의율 평균 (%)"))
    fig.add_trace(
        go.Bar(
            x=labels,
            y=csat_values,
            marker_color=colors,
            text=csat_values,
            texttemplate="%{text}",
            textposition="outside",
            hovertemplate="%{x}<br>CSAT 평균: %{y}<extra></extra>",
            showlegend=False,
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(
            x=labels,
            y=recontact_values,
            marker_color=colors,
            text=[f"{v}%" for v in recontact_values],
            texttemplate="%{text}",
            textposition="outside",
            hovertemplate="%{x}<br>재문의율: %{y}%<extra></extra>",
            showlegend=False,
        ),
        row=1,
        col=2,
    )
    fig.update_layout(
        paper_bgcolor="#1a1a19",
        plot_bgcolor="#1a1a19",
        font_color=TEXT,
        height=320,
    )
    fig.update_xaxes(gridcolor="#2c2c2a", linecolor="#383835")
    fig.update_yaxes(gridcolor="#2c2c2a", linecolor="#383835")
    return fig


REPORT_SECTION_RE = re.compile(r"^## (\d+)\.\s+(.+)$", re.MULTILINE)


# 섹션 번호대별 네온 그룹 색상 (다크모드 전용): 1-3 그린 / 4-6 핑크 / 7-8 시안
REPORT_SECTION_GROUPS = {"a": "#3bffa0", "b": "#ff4fd8", "c": "#33e0ff"}


def _section_group(num):
    n = int(num)
    if n <= 3:
        return "a"
    if n <= 6:
        return "b"
    return "c"


def render_report_with_toc(report_text):
    """리포트의 '## N. 제목' 대제목 8개를 목차로 뽑아 상단에 배치하고,
    각 대제목 우측에 '목차 바로가기' 링크를 붙인 HTML+마크다운 혼합 문자열을 만든다.
    섹션 번호대(1-3/4-6/7-8)별로 네온 그린·핑크·시안 3색을 구분해 입힌다."""
    sections = REPORT_SECTION_RE.findall(report_text)

    toc_items = "\n".join(
        f'    <li><a href="#report-sec-{num}" class="group-{_section_group(num)}">{num}. {title.strip()}</a></li>'
        for num, title in sections
    )

    color_rules = "\n".join(
        f"""
.report-toc a.group-{g} {{ color: {c}; }}
.report-heading-row.group-{g} {{ border-bottom: 2px solid {c}; box-shadow: 0 1px 8px -2px {c}; }}
.report-heading-row.group-{g} h2 {{ color: {c}; text-shadow: 0 0 10px {c}66; }}
.report-back-to-toc.group-{g}:hover {{ color: {c}; text-shadow: 0 0 6px {c}88; }}
""".strip("\n")
        for g, c in REPORT_SECTION_GROUPS.items()
    )

    style_and_toc = f"""
<style>
.report-toc {{
    background: #1a1a19;
    border: 1px solid #383835;
    border-radius: 10px;
    padding: 1.1rem 1.5rem;
    margin-bottom: 1.8rem;
    scroll-margin-top: 4.5rem;
}}
.report-toc-title {{
    font-weight: 700;
    font-size: 1.05rem;
    color: #ffffff;
    margin-bottom: 0.5rem;
}}
.report-toc ol {{
    margin: 0;
    padding-left: 1.3rem;
    line-height: 2;
}}
.report-toc a {{
    text-decoration: none;
}}
.report-toc a:hover {{
    text-decoration: underline;
}}
.report-heading-row {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding-bottom: 0.4rem;
    margin-top: 2.2rem;
    margin-bottom: 0.9rem;
    scroll-margin-top: 4.5rem;
}}
.report-heading-row h2 {{
    margin: 0;
    padding: 0;
    border: none;
}}
.report-back-to-toc {{
    font-size: 0.82rem;
    color: #898781;
    text-decoration: none;
    white-space: nowrap;
    margin-left: 1rem;
}}
.report-back-to-toc:hover {{
    text-decoration: underline;
}}
{color_rules}
</style>
<div class="report-toc" id="report-toc">
  <div class="report-toc-title">📑 목차</div>
  <ol>
{toc_items}
  </ol>
</div>

"""

    def replace_heading(match):
        num, title = match.group(1), match.group(2).strip()
        grp = _section_group(num)
        return (
            f'<div class="report-heading-row group-{grp}" id="report-sec-{num}">'
            f"<h2>{num}. {title}</h2>"
            f'<a class="report-back-to-toc group-{grp}" href="#report-toc">목차 바로가기 ↑</a>'
            f"</div>"
        )

    body = REPORT_SECTION_RE.sub(replace_heading, report_text)
    return style_and_toc + body


st.set_page_config(page_title="고객은 왜 이탈하는가", layout="wide")

PROJECT_MENU = [
    {
        "week": "2주차",
        "title": "구매 협력사 성과·리스크 분석",
        "url": "https://risk-analysis-week2-hskim.streamlit.app/",
        "current": False,
    },
    {
        "week": "3주차",
        "title": "고객은 왜 이탈하는가",
        "url": None,
        "current": True,
    },
    {
        "week": "4주차",
        "title": "마케팅 채널 효율",
        "url": "https://marketing-channel-efficiency-week4-uuqc2z7cabyqkqowfeturz.streamlit.app/",
        "current": False,
    },
]

st.markdown(
    """
    <style>
    .project-menu-badge {
        font-weight: 800; letter-spacing: 0.02em; font-size: 0.95rem;
        color: #3bffa0; text-shadow: 0 0 10px #3bffa066;
    }
    [data-testid="stSidebar"] {
        background-color: #2a2a30;
        border-right: 1px solid rgba(255,255,255,0.12);
    }
    [data-testid="stSidebar"] [data-testid^="stBaseButton"],
    [data-testid="stSidebar"] [data-testid^="stBaseLinkButton"] {
        justify-content: flex-start !important;
        text-align: left !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown('<span class="project-menu-badge">● 프로젝트 메뉴</span>', unsafe_allow_html=True)
    st.caption("클릭하면 해당 주차 배포 앱으로 이동합니다")
    for item in PROJECT_MENU:
        label = f"{'▶ ' if item['current'] else ''}{item['week']} · {item['title']}"
        if item["current"]:
            st.button(label, disabled=True, use_container_width=True, key="nav_current")
        else:
            st.link_button(label, item["url"], use_container_width=True)

col_title, col_link = st.columns([5, 1.4])
with col_title:
    st.title("고객은 왜 이탈하는가 — 이탈 원인 진단 대시보드")
with col_link:
    st.link_button("📱 대시보드 반응형 버전", REACT_DASHBOARD_URL, use_container_width=True)

data = load_data()

tab_dashboard, tab_report = st.tabs(["대시보드", "개선 제안 리포트"])

with tab_dashboard:
    customers = data["customers"]

    total_n = len(customers)
    churned_n = int((customers["churn_yn"] == "Y").sum())
    churn_rate = round(100 * churned_n / total_n, 1)

    col1, col2, col3 = st.columns(3)
    col1.metric("전체 고객 수", f"{total_n}명")
    col2.metric("이탈 고객 수", f"{churned_n}명")
    col3.metric("전체 이탈율", f"{churn_rate}%")

    st.subheader("① VOC로 본 이탈")
    st.plotly_chart(chart_voc_churn(data["customers"], data["voc"]), use_container_width=True)

    st.subheader("② 채널·만족도로 본 이탈")
    st.plotly_chart(
        chart_channel_csat_recontact(data["consultations"], data["satisfaction"]),
        use_container_width=True,
    )

    st.subheader("③ 재문의 반복으로 본 이탈")
    st.plotly_chart(
        chart_recontact_bucket_churn(data["consultations"], data["customers"]),
        use_container_width=True,
    )

    st.subheader("④ 요금제로 본 이탈")
    st.plotly_chart(chart_plan_churn(data["customers"]), use_container_width=True)

    st.subheader("⑤ 지역으로 본 이탈")
    st.plotly_chart(chart_region_churn(data["customers"]), use_container_width=True)

    st.subheader("⑥ 가입기간·이용량으로 본 이탈")
    st.plotly_chart(
        chart_tenure_usage_scatter(data["customers"], data["usage"]), use_container_width=True
    )

    st.subheader("상담원 관점: 직원만족도와 고객 경험")
    agents_df, agent_consultations_df, snapshot_date = load_agent_data()
    st.caption(f"🟡 스냅샷 데이터({snapshot_date} 기준) — 로딩 속도를 위해 항상 스냅샷을 사용합니다")

    teams = sorted(agents_df["team"].unique())
    selected_team = st.selectbox("팀 선택", ["전체"] + teams)
    if selected_team == "전체":
        filtered_agents = agents_df
    else:
        filtered_agents = agents_df[agents_df["team"] == selected_team]

    st.caption(f"선택된 팀 상담원 수: {len(filtered_agents)}명 (표본 30명 미만 — 참고용)")

    st.plotly_chart(chart_agent_enps(filtered_agents), use_container_width=True)

    col_burnout, col_training = st.columns(2)
    col_burnout.plotly_chart(
        chart_agent_burnout_csat(filtered_agents, agent_consultations_df),
        use_container_width=True,
    )
    col_training.plotly_chart(
        chart_agent_training_comparison(filtered_agents, agent_consultations_df),
        use_container_width=True,
    )

# 파일명은 영문(ASCII)이어야 한다 — 한글 파일명은 Streamlit Cloud의 정적 서빙
# 레이어에서 URL 인코딩이 안 맞아 404가 났다(직접 검증함, report_pdf.py 참고).
STATIC_REPORT_PDF = Path(__file__).parent / "static" / "report.pdf"


with tab_report:
    report_path = Path(__file__).parent / "report" / "고객서비스_만족도개선_리포트.md"
    report_text = report_path.read_text(encoding="utf-8-sig")
    if report_text.startswith("---"):
        end = report_text.find("---", 3)
        if end != -1:
            report_text = report_text[end + 3 :].lstrip("\n")

    col_spacer, col_pdf_btn = st.columns([5, 1.4])
    with col_pdf_btn:
        show_pdf = st.button("📄 PDF로 보기", use_container_width=True)

    if show_pdf:
        # Streamlit Cloud의 정적 파일 서빙은 배포 시점에 저장소에 이미 있던 파일만
        # 서빙하고 앱 실행 중에 쓴 파일은 반영하지 않는다(직접 검증함). 그래서 매
        # 클릭마다 새로 만들지 않고, report_pdf.py를 미리 실행해 커밋해둔 static/의
        # 고정 파일을 쓴다 — st.link_button은 그 자체로 새 탭을 여니 여기엔 커스텀
        # JS가 필요 없다(커스텀 JS는 항상 sandbox iframe에서만 실행되고, 그 안에서
        # 만든 Blob은 새 탭으로 못 넘어간다는 것도 별도로 검증했음).
        if STATIC_REPORT_PDF.exists():
            pdf_bytes = STATIC_REPORT_PDF.read_bytes()
        else:
            # 로컬에서 아직 `python report_pdf.py`를 실행해보지 않았을 때의 대비책.
            with st.spinner("공문서 형식 PDF 생성 중..."):
                pdf_bytes = build_report_pdf(report_text)

        col_open, col_download = st.columns(2)
        with col_open:
            st.link_button(
                "🔗 새 창에서 PDF 열기 (인쇄/다운로드)",
                "app/static/report.pdf",
                use_container_width=True,
            )
        with col_download:
            st.download_button(
                "⬇️ PDF 다운로드",
                data=pdf_bytes,
                file_name="고객서비스_만족도개선_리포트.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

    st.markdown(render_report_with_toc(report_text), unsafe_allow_html=True)
