import pandas as pd
import plotly.express as px

RAW = r"C:\Users\김형성\my-wiki-02\raw"

customers = pd.read_csv(f"{RAW}\\data_customers.csv", encoding="utf-8-sig")

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
    title="요금제별 이탈율",
    category_orders={"plan": list(summary["plan"])},
)
fig.update_traces(
    hovertemplate=(
        "<b>%{x}</b><br>고객 수: %{customdata[0]}명<br>"
        "이탈 고객 수: %{customdata[1]}명<br>이탈율: %{y}%<extra></extra>"
    )
)
fig.update_layout(showlegend=False)

if __name__ == "__main__":
    print(summary.to_string(index=False))
    fig.show()
