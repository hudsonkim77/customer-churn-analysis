import pandas as pd
import plotly.graph_objects as go

RAW = r"C:\Users\김형성\my-wiki-02\raw"

consultations = pd.read_csv(f"{RAW}\\data_consultations.csv", encoding="utf-8-sig")
satisfaction = pd.read_csv(f"{RAW}\\data_satisfaction.csv", encoding="utf-8-sig")

merged = satisfaction.merge(
    consultations[["consult_id", "channel"]], on="consult_id", how="inner"
)

csat_by_channel = (
    merged.groupby("channel")["csat"].mean().round(2).rename("avg_csat")
)
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
    title="채널별 CSAT 평균 및 재문의율 (CSAT 낮은 순)",
    xaxis=dict(title="채널", categoryorder="array", categoryarray=result["channel"]),
    yaxis=dict(title="평균 CSAT", side="left"),
    yaxis2=dict(title="재문의율 (%)", side="right", overlaying="y"),
    hovermode="x unified",
)

if __name__ == "__main__":
    print(result.to_string(index=False))
    fig.show()
