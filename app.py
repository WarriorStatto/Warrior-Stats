import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Warriors Stats",
    page_icon="🏆",
    layout="wide"
)

st.title("🏆 Warriors Statistics Dashboard")

@st.cache_data
def load_data():
    df = pd.read_excel("skittles-import.xlsx")
    df.columns = df.columns.str.lower()

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    return df

df = load_data()

st.success(f"{len(df)} records loaded")

# KPI CARDS

c1, c2, c3, c4 = st.columns(4)

c1.metric("Games", df["gamekey"].nunique())

c2.metric("Players", df["player"].nunique())

c3.metric("Average Score", round(df["score"].mean(), 2))

c4.metric("Highest Score", int(df["score"].max()))

st.divider()

# LEADERBOARD

st.subheader("🏅 Player Leaderboard")

leaderboard = (
    df.groupby("player")
      .agg(
          games=("gamekey", "nunique"),
          average=("score", "mean"),
          best=("score", "max")
      )
      .reset_index()
)

leaderboard["average"] = leaderboard["average"].round(2)

leaderboard = leaderboard.sort_values(
    "average",
    ascending=False
)

leaderboard.index = leaderboard.index + 1

st.dataframe(
    leaderboard,
    use_container_width=True
)

st.divider()

# HALL OF FAME

st.subheader("🏆 Hall of Fame")

hall_of_fame = (
    df.sort_values(
        "score",
        ascending=False
    )
)

st.dataframe(
    hall_of_fame[
        [
            "score",
            "player",
            "date",
            "opponent",
            "venue",
            "alley",
            "season"
        ]
    ],
    use_container_width=True
)
