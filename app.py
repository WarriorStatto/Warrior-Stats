import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Warriors Stats",
    page_icon="🏆",
    layout="wide"
)

@st.cache_data
def load_data():
    df = pd.read_excel("skittles-import.xlsx")
    df.columns = df.columns.str.lower()

    df["gamekey"] = (
        df["season"].astype(str)
        + "-"
        + df["game"].astype(str)
    )

    return df

df = load_data()

st.title("🏆 Warriors Statistics Dashboard")

# KPI CARDS

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Games",
    df["gamekey"].nunique()
)

c2.metric(
    "Players",
    df["player"].nunique()
)

c3.metric(
    "Average Score",
    round(df["score"].mean(), 2)
)

c4.metric(
    "Highest Score",
    int(df["score"].max())
)

st.divider()

# LEADERBOARD

st.subheader("🏅 Leaderboard")

leaderboard = (
    df.groupby("player")
    .agg(
        Games=("gamekey", "nunique"),
        Average=("score", "mean"),
        Best=("score", "max")
    )
    .reset_index()
)

leaderboard["Average"] = leaderboard["Average"].round(2)

leaderboard = leaderboard.sort_values(
    "Average",
    ascending=False
)

st.dataframe(
    leaderboard,
    use_container_width=True
)

st.divider()

# HALL OF FAME

st.subheader("🏆 Hall of Fame")

hall_of_fame = df.sort_values(
    "score",
    ascending=False
)

st.dataframe(
    hall_of_fame[
        [
            "score",
            "player",
            "date",
            "opponent",
            "venue",
            "alley"
        ]
    ],
    use_container_width=True
)
