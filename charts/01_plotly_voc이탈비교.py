import pandas as pd
import plotly.express as px

RAW = r"C:\Users\김형성\my-wiki-02\raw"

voc = pd.read_csv(f"{RAW}\\data_voc.csv", encoding="utf-8-sig")
customers = pd.read_csv(f"{RAW}\\data_customers.csv", encoding="utf-8-sig")

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
    title="전체 고객 vs 해지관련 부정 VOC 이력 고객 이탈율 비교",
)
fig.update_traces(
    hovertemplate=(
        "<b>%{x}</b><br>고객 수: %{customdata[0]}명<br>"
        "이탈 고객 수: %{customdata[1]}명<br>이탈율: %{y}%<extra></extra>"
    )
)
fig.update_layout(showlegend=False)

if __name__ == "__main__":
    print(df.to_string(index=False))
    fig.show()
