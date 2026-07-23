from google.cloud import bigquery
from plotly.subplots import make_subplots
import plotly.graph_objects as go

PROJECT_ID = "hudson-bq-practice-2026"
DATASET = f"{PROJECT_ID}.practice_dataset"

client = bigquery.Client(project=PROJECT_ID)

agents = client.query(
    f"SELECT agent_id, training_completed_yn FROM `{DATASET}.data_agents`"
).result().to_dataframe()

consultations = client.query(
    f"SELECT consult_id, agent_id, is_recontact FROM `{DATASET}.data_consultations`"
).result().to_dataframe()

satisfaction = client.query(
    f"SELECT consult_id, csat FROM `{DATASET}.data_satisfaction`"
).result().to_dataframe()

merged = satisfaction.merge(consultations, on="consult_id", how="inner")
avg_csat = merged.groupby("agent_id")["csat"].mean().rename("avg_csat")
recontact_rate = (
    consultations.groupby("agent_id")["is_recontact"].mean().mul(100).rename("recontact_rate")
)

df = agents.merge(avg_csat, on="agent_id").merge(recontact_rate, on="agent_id")

csat_by_group = df.groupby("training_completed_yn")["avg_csat"].mean().round(3)
recontact_by_group = df.groupby("training_completed_yn")["recontact_rate"].mean().round(2)

BLUE = "#3987e5"  # Y (교육이수) - 강조색
GRAY = "#898781"  # N (미이수) - 회색 계열
DARK_SURFACE = "#1a1a19"
TEXT = "#ffffff"

labels = ["N (미이수)", "Y (교육이수)"]
colors = [GRAY, BLUE]

csat_values = [round(csat_by_group.get(False), 3), round(csat_by_group.get(True), 3)]
recontact_values = [round(recontact_by_group.get(False), 2), round(recontact_by_group.get(True), 2)]

fig = make_subplots(
    rows=1,
    cols=2,
    subplot_titles=("CSAT 평균", "재문의율 평균 (%)"),
)

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
    title="교육 이수 여부(Y/N)에 따른 CSAT·재문의율 비교",
    paper_bgcolor=DARK_SURFACE,
    plot_bgcolor=DARK_SURFACE,
    font_color=TEXT,
)
fig.update_xaxes(gridcolor="#2c2c2a", linecolor="#383835")
fig.update_yaxes(gridcolor="#2c2c2a", linecolor="#383835")

if __name__ == "__main__":
    print("CSAT by group:", csat_by_group.to_dict())
    print("Recontact rate by group:", recontact_by_group.to_dict())
    fig.show()
