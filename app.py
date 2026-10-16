import streamlit as st
import os
import pandas as pd
import numpy as np

# -------------------------------------------------------------------
# CONFIG
# -------------------------------------------------------------------

st.set_page_config(
    page_title="Warriors Stats",
    page_icon="🏆",
    layout="centered",          # narrower = better on phones
    initial_sidebar_state="collapsed",
)

# -------------------------------------------------------------------
# COLOURS  (matched to the Excel Averages tab)
# -------------------------------------------------------------------

GREEN  = "C5E0B4"   # headings
BLUE   = "C6D9F1"   # player names
CREAM  = "FDEADA"   # data cells
SALMON = "FCD5B5"   # highlights
KHAKI  = "DDD9C3"   # home block
ROSE   = "F2DCDB"   # away block
LAV    = "E4DFEC"   # cup block

CSS = f"""
<style>
  .block-container {{ padding-top: 1.2rem; padding-bottom: 2rem; max-width: 900px; }}
  h1 {{ font-size: 1.5rem !important; color: #2b2b2b; }}
  h2 {{ font-size: 1.2rem !important; }}
  h3 {{ font-size: 1.05rem !important; }}
  div[data-testid="stMetricValue"] {{ font-size: 1.35rem; }}
  div[data-testid="stMetricLabel"] {{ font-size: 0.8rem; }}
  .w-card {{
      background: #{CREAM};
      border-left: 5px solid #{GREEN};
      border-radius: 8px;
      padding: 0.7rem 0.9rem;
      margin-bottom: 0.6rem;
  }}
  .w-name {{ font-weight: 600; font-size: 1.05rem; }}
  .w-sub  {{ font-size: 0.82rem; color: #555; }}
  .w-big  {{ font-size: 1.5rem; font-weight: 700; }}
  .w-h2h {{
      background: #{CREAM};
      border-radius: 8px;
      padding: 0.8rem 1rem;
      margin-bottom: 0.7rem;
      border-left: 5px solid #{SALMON};
  }}
  .w-vs {{ font-size: 0.95rem; font-weight: 600; }}
  .w-score {{ font-size: 1.6rem; font-weight: 700; letter-spacing: 1px; }}
  div[data-testid="stDataFrame"] {{ font-size: 0.82rem; }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# -------------------------------------------------------------------
# DATA
# -------------------------------------------------------------------

# Files the app looks for, in order of preference.
DATA_CANDIDATES = [
    "skittles-import.csv",
    "skittles-import.xlsx",
    "data/skittles-import.csv",
    "data/skittles-import.xlsx",
]


def _find_data_file():
    """Return the first existing data file, or None."""
    for name in DATA_CANDIDATES:
        if os.path.exists(name):
            return name
    return None


@st.cache_data
def load_data(path):
    if path.lower().endswith(".xlsx"):
        df = pd.read_excel(path, sheet_name="All Games")
    else:
        df = pd.read_csv(path)

    # normalise headers: lower-case, no spaces / underscores
    df.columns = (
        df.columns.str.strip().str.lower()
                  .str.replace(" ", "_", regex=False)
    )
    # accept a few likely spellings so column names never break the app
    aliases = {
        "missed_single": "missedsingle",
        "missed_singles": "missedsingle",
        "spare_9": "spare9",
        "spare_9s": "spare9",
        "team_total": "team_total",
        "opp_total": "opp_total",
    }
    df = df.rename(columns={k: v for k, v in aliases.items() if k in df.columns})

    for col in ["score", "ticks", "spares", "fines", "sunshine",
                "missedsingle", "flopper", "spare9", "team_total", "opp_total"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["gamekey"] = df["season"].astype(str) + "-" + df["game"].astype(str)
    df["result"] = np.where(df["team_total"] > df["opp_total"], "W",
                    np.where(df["team_total"] < df["opp_total"], "L", "D"))
    return df


_path = _find_data_file()
if _path is None:
    st.error("### Data file not found")
    st.markdown(
        "The app is looking for the games data but can't find it. "
        "Add **one** of these files to the repo, in the same folder as `app.py`:"
    )
    for name in DATA_CANDIDATES:
        st.markdown(f"- `{name}`")
    st.markdown(
        "Check the filename is spelled and capitalised exactly (Streamlit Cloud "
        "is case-sensitive), and that it sits next to `app.py` rather than in a "
        "subfolder it doesn't expect."
    )
    st.stop()

try:
    df = load_data(_path)
except KeyError as e:
    st.error(f"### Column missing: {e}")
    st.markdown(
        "The data file was found but a required column is missing. "
        "Expected columns: season, game, date, venue, alley, opponent, player, "
        "score, ticks, spares, fines, sunshine, missedsingle, flopper, spare9, "
        "team_total, opp_total."
    )
    st.stop()

st.caption(f"Loaded {len(df):,} rows from `{_path}`")

# -------------------------------------------------------------------
# SIDEBAR — filters only (navigation is via tabs)
# -------------------------------------------------------------------

st.sidebar.title("🏆 Warriors")

season_filter = st.sidebar.multiselect(
    "Season", sorted(df["season"].unique()), default=sorted(df["season"].unique())
)
venue_filter = st.sidebar.multiselect(
    "Venue", sorted(df["venue"].unique()), default=sorted(df["venue"].unique())
)

with st.sidebar.expander("More filters"):
    alley_filter = st.multiselect("Alley", sorted(df["alley"].unique()), default=sorted(df["alley"].unique()))
    player_filter = st.multiselect("Player", sorted(df["player"].unique()), default=sorted(df["player"].unique()))

f = df[
    df["season"].isin(season_filter)
    & df["venue"].isin(venue_filter)
    & df["alley"].isin(alley_filter)
    & df["player"].isin(player_filter)
]

if f.empty:
    st.warning("No games match those filters. Try widening them in the sidebar.")
    st.stop()


# ===================================================================
# TABS
# ===================================================================

tab_home, tab_players, tab_h2h, tab_alleys, tab_opps, tab_records, tab_extra = st.tabs(
    ["📊 Overview", "👤 Players", "🆚 Head to Head", "🎳 Alleys",
     "⚔️ Opponents", "🏆 Records", "➕ Extras"]
)

# -------------------------------------------------------------------
# OVERVIEW
# -------------------------------------------------------------------
with tab_home:
    st.markdown("### Overview")

    c1, c2 = st.columns(2)
    c1.metric("Games", f["gamekey"].nunique())
    c2.metric("Players", f["player"].nunique())

    c3, c4 = st.columns(2)
    c3.metric("Team average", round(f["score"].mean(), 2))
    c4.metric("Best score", int(f["score"].max()))

    tg = (
        f.drop_duplicates(["season", "game"])
        .groupby("season")
        .agg(Played=("game", "count"),
             Won=("result", lambda x: (x == "W").sum()),
             Lost=("result", lambda x: (x == "L").sum()))
        .reset_index()
    )
    tg["Win %"] = (100 * tg["Won"] / tg["Played"]).round(1)
    st.markdown("#### Season by season")
    st.dataframe(tg, hide_index=True, use_container_width=True)

# -------------------------------------------------------------------
# PLAYERS
# -------------------------------------------------------------------
with tab_players:
    st.markdown("### Player leaderboard")

    lb = (
        f.groupby("player")
        .agg(Games=("gamekey", "nunique"),
             Average=("score", "mean"),
             Best=("score", "max"))
        .reset_index()
        .sort_values("Average", ascending=False)
    )
    lb["Average"] = lb["Average"].round(2)
    st.dataframe(lb, hide_index=True, use_container_width=True)

    st.markdown("#### Player profile")
    player = st.selectbox("Choose a player", sorted(f["player"].unique()))
    pdf = f[f["player"] == player].sort_values("date", ascending=False)

    m1, m2, m3 = st.columns(3)
    m1.metric("Games", pdf["gamekey"].nunique())
    m2.metric("Average", round(pdf["score"].mean(), 2))
    m3.metric("Best", int(pdf["score"].max()))

    # ---- form chart: score by match, oldest to newest ----
    st.markdown("#### Form")
    form = pdf.sort_values("date")
    if len(form) >= 2:
        st.line_chart(form.set_index("date")["score"], height=200)
    else:
        st.info("Not enough games for a form line yet.")

    st.markdown("#### Recent games")
    for _, r in pdf.head(10).iterrows():
        st.markdown(
            f"""<div class="w-card">
                  <div class="w-big">{int(r['score'])}</div>
                  <div class="w-name">{r['opponent']}</div>
                  <div class="w-sub">{r['venue']} · {r['alley']} · {r['season']}</div>
                </div>""",
            unsafe_allow_html=True,
        )

# -------------------------------------------------------------------
# HEAD TO HEAD
# -------------------------------------------------------------------
with tab_h2h:
    st.markdown("### Head to head")
    st.caption("Compare one player against one opponent.")

    colA, colB = st.columns(2)
    h2h_player = colA.selectbox("Player", sorted(f["player"].unique()), key="h2hp")
    opp_options = sorted(f[f["player"] == h2h_player]["opponent"].unique())

    if not opp_options:
        st.info("That player has no games with the current filters.")
    else:
        h2h_opp = colB.selectbox("Opponent", opp_options, key="h2ho")
        h2h = f[(f["player"] == h2h_player) & (f["opponent"] == h2h_opp)].sort_values("date")

        played = h2h["gamekey"].nunique()
        won = int(h2h.drop_duplicates("gamekey")["result"].eq("W").sum())
        lost = int(h2h.drop_duplicates("gamekey")["result"].eq("L").sum())

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Games", played)
        m2.metric("Won", won)
        m3.metric("Lost", lost)
        m4.metric("Average", round(h2h["score"].mean(), 2))

        st.markdown("#### Head-to-head record")
        for _, g in h2h.drop_duplicates("gamekey").sort_values("date", ascending=False).iterrows():
            res = "W" if g["team_total"] > g["opp_total"] else ("L" if g["team_total"] < g["opp_total"] else "D")
            st.markdown(
                f"""<div class="w-h2h">
                      <div class="w-vs">{h2h_player} vs {h2h_opp} — {g['season']} game {int(g['game'])}</div>
                      <div class="w-score">{int(g['team_total'])}–{int(g['opp_total'])} ({res})</div>
                      <div class="w-sub">{g['venue']} · {g['alley']}</div>
                    </div>""",
                unsafe_allow_html=True,
            )

        st.markdown(f"#### {h2h_player}'s scores in those games")
        st.dataframe(
            h2h[["date", "score", "venue", "alley", "season", "ticks", "spares", "fines"]],
            hide_index=True, use_container_width=True,
        )

# -------------------------------------------------------------------
# ALLEYS
# -------------------------------------------------------------------
with tab_alleys:
    st.markdown("### Alley form")

    al = (
        f.groupby("alley")
        .agg(Games=("gamekey", "nunique"),
             Average=("score", "mean"),
             Best=("score", "max"))
        .reset_index()
        .sort_values("Average", ascending=False)
    )
    al["Average"] = al["Average"].round(2)
    st.dataframe(al, hide_index=True, use_container_width=True)

    st.markdown("#### Player × Alley")
    mode = st.radio("Show", ["Overall", "Home", "Away", "Cup"], horizontal=True)
    src = f if mode == "Overall" else f[f["venue"] == mode]
    if src.empty:
        st.info("No games for that venue with the current filters.")
    else:
        piv = src.pivot_table(index="player", columns="alley",
                              values="score", aggfunc="mean").round(2)
        st.dataframe(piv, use_container_width=True)

# -------------------------------------------------------------------
# OPPONENTS
# -------------------------------------------------------------------
with tab_opps:
    st.markdown("### Head to head — all opponents")

    tgames = f.drop_duplicates(["season", "game"])
    opp = (
        tgames.groupby("opponent")
        .agg(Played=("game", "count"),
             Won=("result", lambda x: (x == "W").sum()),
             Lost=("result", lambda x: (x == "L").sum()))
        .reset_index()
    )
    opp["Win %"] = (100 * opp["Won"] / opp["Played"]).round(1)
    opp = opp.sort_values("Win %", ascending=False)
    st.dataframe(opp, hide_index=True, use_container_width=True)

    st.markdown("#### Player × Opponent")
    mode2 = st.radio("Show", ["Overall", "Home", "Away", "Cup"], horizontal=True, key="oppmode")
    src2 = f if mode2 == "Overall" else f[f["venue"] == mode2]
    if src2.empty:
        st.info("No games for that venue with the current filters.")
    else:
        piv2 = src2.pivot_table(index="player", columns="opponent",
                                values="score", aggfunc="mean").round(2)
        st.dataframe(piv2, use_container_width=True)

# -------------------------------------------------------------------
# RECORDS
# -------------------------------------------------------------------
with tab_records:
    st.markdown("### Records")

    st.markdown("#### 70+ club")
    big = f[f["score"] >= 70].sort_values("score", ascending=False)
    if big.empty:
        st.info("No scores of 70 or more with the current filters.")
    else:
        st.dataframe(
            big[["score", "player", "opponent", "venue", "alley", "season"]],
            hide_index=True, use_container_width=True,
        )

    st.markdown("#### Best team totals")
    tt = f.drop_duplicates(["season", "game"]).sort_values("team_total", ascending=False)
    st.dataframe(
        tt[["team_total", "opp_total", "opponent", "venue", "alley", "season"]].head(15),
        hide_index=True, use_container_width=True,
    )

    st.markdown("#### Best individual legs")
    try:
        legs = pd.read_csv("skittles-legs.csv")
        legs.columns = legs.columns.str.strip().str.lower()
        legs = legs[legs["season"].isin(season_filter)]
        st.dataframe(
            legs.sort_values("leg_score", ascending=False)
                [["leg_score", "player", "opponent", "alley", "season", "tick"]].head(15),
            hide_index=True, use_container_width=True,
        )
    except FileNotFoundError:
        st.info("Add skittles-legs.csv to the repo to show leg records.")

# -------------------------------------------------------------------
# EXTRAS — ticks, spares, fines
# -------------------------------------------------------------------
with tab_extra:
    st.markdown("### Ticks, spares & fines")

    x = (
        f.groupby("player")
        .agg(Games=("gamekey", "nunique"),
             Ticks=("ticks", "sum"),
             Spares=("spares", "sum"),
             Fines=("fines", "sum"),
             Sunshine=("sunshine", "sum"),
             MissedSingle=("missedsingle", "sum"),
             Flopper=("flopper", "sum"),
             Spare9=("spare9", "sum"))
        .reset_index()
        .sort_values("Fines", ascending=False)
    )
    x["Fines"] = x["Fines"].round(2)
    st.dataframe(x, hide_index=True, use_container_width=True)

    st.markdown("#### Totals")
    t1, t2, t3 = st.columns(3)
    t1.metric("Ticks", int(f["ticks"].sum()))
    t2.metric("Spares", int(f["spares"].sum()))
    t3.metric("Fines", f"£{f['fines'].sum():.2f}")
