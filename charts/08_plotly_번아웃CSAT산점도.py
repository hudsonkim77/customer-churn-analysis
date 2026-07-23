from google.cloud import bigquery
import pandas as pd
import plotly.express as px

PROJECT_ID = "hudson-bq-practice-2026"
DATASET = f"{PROJECT_ID}.practice_dataset"

client = bigquery.Client(project=PROJECT_ID)

agents = client.query(
    f"SELECT agent_id, overtime_hours_avg FROM `{DATASET}.data_agents`"
).result().to_dataframe()

consultations = client.query(
    f"SELECT consult_id, agent_id FROM `{DATASET}.data_consultations`"
).result().to_dataframe()

satisfaction = client.query(
    f"SELECT consult_id, csat FROM `{DATASET}.data_satisfaction`"
).result().to_dataframe()

merged = satisfaction.merge(consultations, on="consult_id", how="inner")
avg_csat_per_agent = (
    merged.groupby("agent_id")["csat"].mean().round(2).rename("avg_csat").reset_index()
)

df = agents.merge(avg_csat_per_agent, on="agent_id", how="inner")

r = round(df["overtime_hours_avg"].corr(df["avg_csat"]), 2)

BLUE = "#3987e5"
DARK_SURFACE = "#1a1a19"
TEXT = "#ffffff"

fig = px.scatter(
    df,
    x="overtime_hours_avg",
    y="avg_csat",
    trendline="ols",
    custom_data=["agent_id", "overtime_hours_avg", "avg_csat"],
    labels={"overtime_hours_avg": "평균 초과근무 시간(월, 시간)", "avg_csat": "상담원별 CSAT 평균"},
    title="번아웃(초과근무 시간) vs CSAT 평균",
    color_discrete_sequence=[BLUE],
)
fig.update_traces(
    hovertemplate=(
        "agent_id: %{customdata[0]}<br>초과근무 시간: %{customdata[1]}시간<br>"
        "CSAT 평균: %{customdata[2]}<extra></extra>"
    ),
    selector=dict(mode="markers"),
)
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
    paper_bgcolor=DARK_SURFACE,
    plot_bgcolor=DARK_SURFACE,
    font_color=TEXT,
    xaxis=dict(gridcolor="#2c2c2a", linecolor="#383835"),
    yaxis=dict(gridcolor="#2c2c2a", linecolor="#383835"),
)

if __name__ == "__main__":
    print(df.to_string(index=False))
    print(f"correlation r = {r}")
    fig.show()
