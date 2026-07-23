from google.cloud import bigquery
import plotly.graph_objects as go

PROJECT_ID = "hudson-bq-practice-2026"
TABLE = f"`{PROJECT_ID}.practice_dataset.data_agents`"

client = bigquery.Client(project=PROJECT_ID)


def classify(score):
    if score >= 9:
        return "promoter"
    elif score >= 7:
        return "passive"
    return "detractor"


def enps_from_rows(rows):
    n = len(rows)
    if n == 0:
        return None
    promoters = sum(1 for r in rows if classify(r) == "promoter")
    detractors = sum(1 for r in rows if classify(r) == "detractor")
    return round(100 * promoters / n - 100 * detractors / n, 1)


query = f"SELECT team, agent_satisfaction FROM {TABLE}"
rows = list(client.query(query).result())

overall_enps = enps_from_rows([r["agent_satisfaction"] for r in rows])

teams = sorted({r["team"] for r in rows})
team_enps = {
    team: enps_from_rows([r["agent_satisfaction"] for r in rows if r["team"] == team])
    for team in teams
}

BLUE = "#3987e5"
RED = "#d03b3b"
DARK_SURFACE = "#1a1a19"
TEXT = "#ffffff"

fig = go.Figure()

# Big gauge: overall eNPS
fig.add_trace(
    go.Indicator(
        mode="gauge+number",
        value=overall_enps,
        title={"text": "전체 직원 eNPS", "font": {"color": TEXT, "size": 20}},
        number={"font": {"color": RED if overall_enps < 0 else BLUE, "size": 40}},
        gauge={
            "axis": {"range": [-100, 100], "tickcolor": TEXT},
            "bar": {"color": RED if overall_enps < 0 else BLUE},
            "steps": [
                {"range": [-100, 0], "color": "rgba(208, 59, 59, 0.25)"},
                {"range": [0, 100], "color": "rgba(57, 135, 229, 0.15)"},
            ],
            "threshold": {
                "line": {"color": TEXT, "width": 2},
                "thickness": 0.8,
                "value": overall_enps,
            },
        },
        domain={"x": [0, 0.55], "y": [0, 1]},
    )
)

# Small number cards: per-team eNPS, side by side on the right
team_x_slots = [[0.62, 0.78], [0.80, 0.96], [0.62, 0.96]]
n_teams = len(teams)
slot_width = 0.34 / n_teams if n_teams else 0.34
for i, team in enumerate(teams):
    value = team_enps[team]
    x0 = 0.62 + i * slot_width
    x1 = x0 + slot_width - 0.02
    fig.add_trace(
        go.Indicator(
            mode="number",
            value=value,
            title={"text": team, "font": {"color": TEXT, "size": 16}},
            number={"font": {"color": RED if value < 0 else BLUE, "size": 30}},
            domain={"x": [x0, x1], "y": [0.55, 0.95]},
        )
    )

fig.update_layout(
    title="직원만족도 eNPS 스코어카드",
    paper_bgcolor=DARK_SURFACE,
    plot_bgcolor=DARK_SURFACE,
    font_color=TEXT,
    height=420,
)

if __name__ == "__main__":
    print(f"overall eNPS: {overall_enps}")
    for team in teams:
        print(f"{team} eNPS: {team_enps[team]}")
    fig.show()
