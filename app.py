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
    return df

df = load_data()

st.success(f"{len(df)} records loaded")

st.subheader("Data Preview")

st.dataframe(df.head(20))

st.subheader("Top Players")

leaderboard = (
    df.groupby("player")
      .agg(
          games=("gamekey", "nunique"),
          average=("score", "mean"),
          best=("score", "max")
      )
      .reset_index()
      .sort_values("average", ascending=False)
)

leaderboard["average"] = leaderboard["average"].round(2)

st.dataframe(leaderboard)
