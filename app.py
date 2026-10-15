import streamlit as st
import pandas as pd
import plotly.express as px

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

st.set_page_config(
    page_title="Warriors Stats",
    page_icon="🏆",
    layout="wide"
)

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

@st.cache_data
def load_data():

    df = pd.read_excel("skittles-import.xlsx")

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
    )

    df["date"] = pd.to_datetime(
        df["date"],
        dayfirst=True,
        errors="coerce"
    )

    df["score"] = pd.to_numeric(
        df["score"],
        errors="coerce"
    ).fillna(0)

    df["gamekey"] = (
        df["season"].astype(str)
        + "-"
        + df["game"].astype(str)
    )

    df["win_flag"] = (
        df["team_total"]
        > df["opp_total"]
    ).astype(int)

    return df

df = load_data()

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Leaderboard",
        "Hall of Fame",
        "Player Profiles",
        "Opponent Analysis",
        "Awards"
    ]
)

season_filter = st.sidebar.multiselect(
    "Season",
    sorted(df["season"].unique()),
    default=sorted(df["season"].unique())
)

filtered = df[
    df["season"].isin(season_filter)
]

if filtered.empty:
    st.warning(
        "No records match the selected filters."
    )
    st.stop()

# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

if page == "Dashboard":

    st.title("🏆 Warriors Dashboard")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Games",
        filtered["gamekey"].nunique()
    )

    c2.metric(
        "Players",
        filtered["player"].nunique()
    )

    c3.metric(
        "Average Score",
        round(
            filtered["score"].mean(),
            2
        )
    )

    c4.metric(
        "Highest Score",
        int(
            filtered["score"].max()
        )
    )

    st.subheader("📈 Team Performance")

    team_scores = (
        filtered
        .groupby(
            ["gamekey", "date", "opponent"]
        )
        .agg(
            TeamScore=("team_total", "max"),
            OpponentScore=("opp_total", "max")
        )
        .reset_index()
        .sort_values("date")
    )

    team_scores["Rolling"] = (
        team_scores["TeamScore"]
        .rolling(5, min_periods=1)
        .mean()
    )

    chart = px.line(
        team_scores,
        x="date",
        y=[
            "TeamScore",
            "OpponentScore",
            "Rolling"
        ],
        markers=True
    )

    st.plotly_chart(
        chart,
        use_container_width=True
    )

# --------------------------------------------------
# LEADERBOARD
# --------------------------------------------------

elif page == "Leaderboard":

    st.title("🏅 Leaderboard")

    leaders = (
        filtered.groupby("player")
        .agg(
            Games=("gamekey", "nunique"),
            Average=("score", "mean"),
            Best=("score", "max"),
            Wins=("win_flag", "sum")
        )
        .reset_index()
    )

    leaders["Win %"] = (
        leaders["Wins"]
        / leaders["Games"]
        * 100
    ).round(1)

    leaders["Average"] = (
        leaders["Average"]
        .round(2)
    )

    leaders = leaders.sort_values(
        "Average",
        ascending=False
    )

    leaders["Rank"] = range(
        1,
        len(leaders) + 1
    )

    st.dataframe(
        leaders,
        use_container_width=True
    )

# --------------------------------------------------
# HALL OF FAME
# --------------------------------------------------

elif page == "Hall of Fame":

    st.title("🏆 Hall of Fame")

    hall = (
        filtered
        .sort_values(
            "score",
            ascending=False
        )
        .copy()
    )

    hall["Rank"] = range(
        1,
        len(hall) + 1
    )

    st.dataframe(
        hall[
            [
                "Rank",
                "score",
                "player",
                "date",
                "opponent",
                "venue"
            ]
        ],
        use_container_width=True
    )

# --------------------------------------------------
# PLAYER PROFILE
# --------------------------------------------------

elif page == "Player Profiles":

    st.title("👤 Player Profiles")

    player = st.selectbox(
        "Player",
        sorted(
            filtered["player"]
            .unique()
        )
    )

    player_df = filtered[
        filtered["player"] == player
    ]

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Games",
        player_df["gamekey"].nunique()
    )

    c2.metric(
        "Average",
        round(
            player_df["score"].mean(),
            2
        )
    )

    c3.metric(
        "Best",
        int(
            player_df["score"].max()
        )
    )

    recent = (
        player_df
        .sort_values("date")
        .tail(10)
    )

    c4.metric(
        "Last 10 Avg",
        round(
            recent["score"].mean(),
            2
        )
    )

    st.subheader("Score Trend")

    trend = px.line(
        player_df.sort_values("date"),
        x="date",
        y="score",
        markers=True
    )

    st.plotly_chart(
        trend,
        use_container_width=True
    )

# --------------------------------------------------
# OPPONENT ANALYSIS
# --------------------------------------------------

elif page == "Opponent Analysis":

    st.title("⚔️ Opponent Analysis")

    opponents = (
        filtered.groupby("opponent")
        .agg(
            Games=("gamekey", "nunique"),
            Average=("score", "mean"),
            Best=("score", "max")
        )
        .reset_index()
    )

    opponents["Average"] = (
        opponents["Average"]
        .round(2)
    )

    st.dataframe(
        opponents.sort_values(
            "Average",
            ascending=False
        ),
        use_container_width=True
    )

# --------------------------------------------------
# AWARDS
# --------------------------------------------------

elif page == "Awards":

    st.title("🥇 Awards")

    leaders = (
        filtered.groupby("player")
        .agg(
            Games=("gamekey", "nunique"),
            Average=("score", "mean"),
            Wins=("win_flag", "sum")
        )
        .reset_index()
    )

    leaders = leaders[
        leaders["Games"] >= 10
    ]

    if not leaders.empty:

        best_avg = leaders.loc[
            leaders["Average"].idxmax()
        ]

        most_wins = leaders.loc[
            leaders["Wins"].idxmax()
        ]

        best_score = filtered.loc[
            filtered["score"].idxmax()
        ]

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Highest Average",
            f"{best_avg['Average']:.2f}",
            best_avg["player"]
        )

        c2.metric(
            "Highest Score",
            int(best_score["score"]),
            best_score["player"]
        )

        c3.metric(
            "Most Wins",
            int(most_wins["Wins"]),
            most_wins["player"]
        )