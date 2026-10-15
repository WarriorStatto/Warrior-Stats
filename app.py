import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Warriors Stats",
    page_icon="🏆",
    layout="wide"
)

# ------------------------
# LOAD DATA
# ------------------------

@st.cache_data
def load_data():
    df = pd.read_excel("skittles-import.xlsx")

    df.columns = df.columns.str.lower()

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )

    df["gamekey"] = (
        df["season"].astype(str)
        + "-"
        + df["game"].astype(str)
    )

    return df

df = load_data()

# ------------------------
# SIDEBAR
# ------------------------

st.sidebar.title("🏆 Warriors Stats")

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Leaderboard",
        "Hall of Fame",
        "Player Profiles",
        "Opponent Analysis"
    ]
)

season_filter = st.sidebar.multiselect(
    "Season",
    sorted(df["season"].unique()),
    default=sorted(df["season"].unique())
)

venue_filter = st.sidebar.multiselect(
    "Venue",
    sorted(df["venue"].unique()),
    default=sorted(df["venue"].unique())
)

alley_filter = st.sidebar.multiselect(
    "Alley",
    sorted(df["alley"].unique()),
    default=sorted(df["alley"].unique())
)

filtered = df[
    (df["season"].isin(season_filter))
    & (df["venue"].isin(venue_filter))
    & (df["alley"].isin(alley_filter))
]

# ------------------------
# DASHBOARD
# ------------------------

if page == "Dashboard":

    st.title("🏆 Warriors Statistics Dashboard")

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
        round(filtered["score"].mean(), 2)
    )

    c4.metric(
        "Highest Score",
        int(filtered["score"].max())
    )

    st.subheader("Recent Results")

    st.dataframe(
        filtered.sort_values(
            "date",
            ascending=False
        ).head(20),
        use_container_width=True
    )

# ------------------------
# LEADERBOARD
# ------------------------

elif page == "Leaderboard":

    st.title("🏅 Leaderboard")

    leaderboard = (
        filtered.groupby("player")
        .agg(
            Games=("gamekey", "nunique"),
            Average=("score", "mean"),
            Best=("score", "max"),
            SixtyPlus=("score",
                       lambda x: (x >= 60).sum()),
            SeventyPlus=("score",
                         lambda x: (x >= 70).sum())
        )
        .reset_index()
    )

    leaderboard["Average"] = (
        leaderboard["Average"]
        .round(2)
    )

    leaderboard = leaderboard.sort_values(
        "Average",
        ascending=False
    )

    leaderboard.index = (
        leaderboard.index + 1
    )

    st.dataframe(
        leaderboard,
        use_container_width=True
    )

# ------------------------
# HALL OF FAME
# ------------------------

elif page == "Hall of Fame":

    st.title("🏆 Hall of Fame")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Highest Score",
        int(filtered["score"].max())
    )

    c2.metric(
        "70+ Scores",
        len(
            filtered[
                filtered["score"] >= 70
            ]
        )
    )

    c3.metric(
        "60+ Scores",
        len(
            filtered[
                filtered["score"] >= 60
            ]
        )
    )

    hall = filtered.sort_values(
        "score",
        ascending=False
    )

    st.dataframe(
        hall[
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

# ------------------------
# PLAYER PROFILE
# ------------------------

elif page == "Player Profiles":

    st.title("👤 Player Profile")

    player = st.selectbox(
        "Select Player",
        sorted(filtered["player"].unique())
    )

    player_df = filtered[
        filtered["player"] == player
    ]

    c1, c2, c3 = st.columns(3)

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
        "Best Score",
        int(
            player_df["score"].max()
        )
    )

    st.subheader("Match History")

    st.dataframe(
        player_df.sort_values(
            "date",
            ascending=False
        ),
        use_container_width=True
    )

# ------------------------
# OPPONENT ANALYSIS
# ------------------------

elif page == "Opponent Analysis":

    st.title("⚔️ Opponent Analysis")

    opponents = (
        filtered
        .groupby("opponent")
        .agg(
            Games=("gamekey", "nunique"),
 
