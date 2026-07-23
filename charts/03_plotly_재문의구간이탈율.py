import pandas as pd
import plotly.express as px

RAW = r"C:\Users\김형성\my-wiki-02\raw"

consultations = pd.read_csv(f"{RAW}\\data_consultations.csv", encoding="utf-8-sig")
customers = pd.read_csv(f"{RAW}\\data_customers.csv", encoding="utf-8-sig")

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
    title="재문의 횟수 구간별 이탈율",
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

if __name__ == "__main__":
    print(summary.to_string(index=False))
    print(f"overall churn rate: {overall_rate}%")
    fig.show()
