import pandas as pd
import plotly.express as px

RAW = r"C:\Users\김형성\my-wiki-02\raw"

customers = pd.read_csv(f"{RAW}\\data_customers.csv", encoding="utf-8-sig")
usage = pd.read_csv(f"{RAW}\\data_usage_history.csv", encoding="utf-8-sig")

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
    title="가입기간 vs 평균 데이터 사용량 (이탈 여부별)",
)
fig.update_traces(
    hovertemplate=(
        "고객ID: %{customdata[0]}<br>가입기간: %{customdata[1]}개월<br>"
        "평균 데이터 사용량: %{customdata[2]}GB<br>이탈 여부: %{customdata[3]}<extra></extra>"
    )
)

if __name__ == "__main__":
    print(df[["customer_id", "tenure_months", "avg_data_gb", "churn_yn"]].head(10).to_string(index=False))
    print(f"... total rows: {len(df)}")
    fig.show()
