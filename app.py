from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

RAW = Path(__file__).parent / "raw"


@st.cache_data
def load_data():
    return {
        "customers": pd.read_csv(RAW / "data_customers.csv", encoding="utf-8-sig"),
        "voc": pd.read_csv(RAW / "data_voc.csv", encoding="utf-8-sig"),
        "consultations": pd.read_csv(RAW / "data_consultations.csv", encoding="utf-8-sig"),
        "satisfaction": pd.read_csv(RAW / "data_satisfaction.csv", encoding="utf-8-sig"),
        "usage": pd.read_csv(RAW / "data_usage_history.csv", encoding="utf-8-sig"),
    }


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
            "전체 고객": "#636EFA",
            "해지관련 부정 VOC 이력 있음": "#D62728",
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
    fig.update_layout(showlegend=False)
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
            line=dict(color="#D62728"),
            hovertemplate="채널: %{x}<br>재문의율: %{y}%<extra></extra>",
        )
    )
    fig.update_layout(
        xaxis=dict(title="채널", categoryorder="array", categoryarray=result["channel"]),
        yaxis=dict(title="평균 CSAT", side="left"),
        yaxis2=dict(title="재문의율 (%)", side="right", overlaying="y"),
        hovermode="x unified",
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
        color_discrete_map={"0회": "#636EFA", "1회": "#636EFA", "2회 이상": "#D62728"},
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
        line_color="gray",
        annotation_text=f"전체 평균 이탈율 {overall_rate}%",
        annotation_position="top left",
    )
    fig.update_layout(showlegend=False)
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
    color_map = {p: ("#D62728" if p == max_rate_plan else "#636EFA") for p in summary["plan"]}

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
    fig.update_layout(showlegend=False)
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
    color_map = {r: ("#D62728" if r == max_rate_region else "#636EFA") for r in summary["region"]}

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
    fig.update_layout(showlegend=False)
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
        color_discrete_map={"Y": "#D62728", "N": "#636EFA"},
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
    return fig


st.set_page_config(page_title="고객은 왜 이탈하는가", layout="wide")
st.title("고객은 왜 이탈하는가 — 이탈 원인 진단 대시보드")

data = load_data()
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
