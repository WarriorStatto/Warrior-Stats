"""
Warriors Skittles — statistics app.

Data files expected alongside this script:
  skittles-import.csv   (required)  one row per player per game
  skittles-legs.csv     (optional)  one row per individual leg
"""

import os
import pandas as pd
import numpy as np
import streamlit as st

# -------------------------------------------------------------------
# CONFIG
# -------------------------------------------------------------------

st.set_page_config(
    page_title="Warriors Stats",
    page_icon="🏆",
    layout="centered",              # narrower reads better on a phone
    initial_sidebar_state="collapsed",
)

# -------------------------------------------------------------------
# COLOURS — matched to the Excel "Averages" tab
# -------------------------------------------------------------------

GREEN  = "C5E0B4"   # headings
BLUE   = "C6D9F1"   # player names
CREAM  = "FDEADA"   # data cells
SALMON = "FCD5B5"   # highlights

st.markdown(f"""
<style>
  .block-container {{ padding-top: 1.2rem; padding-bottom: 2rem; max-width: 900px; }}
  h1 {{ font-size: 1.5rem !important; }}
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
  .w-h2h {{
      background: #{CREAM};
      border-left: 5px solid #{SALMON};
      border-radius: 8px;
      padding: 0.8rem 1rem;
      margin-bottom: 0.7rem;
  }}
  .w-name  {{ font-weight: 600; font-size: 1.05rem; }}
  .w-sub   {{ font-size: 0.82rem; color: #555; }}
  .w-big   {{ font-size: 1.5rem; font-weight: 700; }}
  .w-vs    {{ font-size: 0.95rem; font-weight: 600; }}
  .w-score {{ font-size: 1.6rem; font-weight: 700; letter-spacing: 1px; }}

  /* ---- tables: keep the scrollbar clear of the digits ---- */
  div[data-testid="stDataFrame"] {{ font-size: 0.82rem; }}
  div[data-testid="stDataFrame"] > div {{ padding-bottom: 10px; }}
  /* breathing room inside the table so the last column isn't clipped */
  div[data-testid="stDataFrame"] [role="gridcell"],
  div[data-testid="stDataFrame"] [role="columnheader"] {{
      padding-left: 10px !important;
      padding-right: 12px !important;
  }}
  /* push the horizontal scrollbar away from the data */
  div[data-testid="stDataFrame"] [data-testid="stElementToolbar"] {{ margin-bottom: 8px; }}
  .w-table-wrap {{ padding-right: 6px; }}
</style>
""", unsafe_allow_html=True)


# -------------------------------------------------------------------
# DATA LOADING
# -------------------------------------------------------------------

DATA_CANDIDATES = [
    "skittles-import.csv",
    "skittles-import.xlsx",
    "data/skittles-import.csv",
    "data/skittles-import.xlsx",
]

# -------------------------------------------------------------------
# THE GERALD TROPHY — committee overrides
# -------------------------------------------------------------------
# The award is for the most ticks in a single match. Occasionally the
# committee applies judgement the data can't show, and the award passes
# to the next eligible player. Add a season here to record that.
#
#   "2025-2026": {"awarded_to": "Chris P", "ticks": 9},

TROPHY_OVERRIDES = {
    "2025-2026": {"awarded_to": "Chris P", "ticks": 9},
    "2024-2025": {"awarded_to": "Matt", "ticks": 10},
}

# Players left out of the Gerald Trophy's all-time line, for the same
# reason they were discounted from individual seasons.
TROPHY_EXCLUDE = {"Sally"}

# columns the app needs, and the spellings it will accept for each
COLUMN_ALIASES = {
    "missed_single": "missedsingle",
    "missed_singles": "missedsingle",
    "missedsingle": "missedsingle",
    "spare_9": "spare9",
    "spare_9s": "spare9",
    "spare9": "spare9",
    "teamtotal": "team_total",
    "opptotal": "opp_total",
}

NUMERIC_COLS = ["score", "ticks", "spares", "fines", "sunshine",
                "missedsingle", "flopper", "spare9", "team_total", "opp_total"]


def _find_data_file():
    for name in DATA_CANDIDATES:
        if os.path.exists(name):
            return name
    return None


def _normalise_columns(df):
    """Lower-case headers, drop spaces and underscores, then map aliases."""
    df.columns = (df.columns.astype(str).str.strip().str.lower()
                    .str.replace(" ", "", regex=False)
                    .str.replace("_", "", regex=False))
    return df.rename(columns={k: v for k, v in COLUMN_ALIASES.items() if k in df.columns})


@st.cache_data
def load_data(path):
    if path.lower().endswith(".xlsx"):
        df = pd.read_excel(path, sheet_name="All Games")
    else:
        df = pd.read_csv(path)

    df = _normalise_columns(df)

    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = 0            # keep the app running if a stat is absent

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["gamekey"] = df["season"].astype(str) + "-" + df["game"].astype(str)
    df["result"] = np.where(df["team_total"] > df["opp_total"], "W",
                     np.where(df["team_total"] < df["opp_total"], "L", "D"))
    return df


def _fines_with_pound(df):
    """Format a fines column as £0.00 for display."""
    return df.assign(Fines=df["Fines"].map(lambda v: f"£{v:,.2f}"))


_req_cols = {"season", "game", "date", "venue", "alley", "opponent", "player", "score"}

_path = _find_data_file()
if _path is None:
    st.error("### Data file not found")
    st.markdown("Add **one** of these to the repo, in the same folder as `app.py`:")
    for name in DATA_CANDIDATES:
        st.markdown(f"- `{name}`")
    st.markdown("Filenames are case-sensitive on Streamlit Cloud.")
    st.stop()

try:
    df = load_data(_path)
except Exception as e:
    st.error(f"### Could not read `{_path}`")
    st.code(str(e))
    st.stop()

missing = sorted(_req_cols - set(df.columns))
if missing:
    st.error(f"### Missing column(s): {', '.join(missing)}")
    st.markdown("Found columns: " + ", ".join(sorted(df.columns)))
    st.stop()

st.caption(f"Loaded {len(df):,} rows from `{_path}`")


# -------------------------------------------------------------------
# SIDEBAR — filters only (navigation is via tabs)
# -------------------------------------------------------------------

st.sidebar.title("🏆 Warriors")

season_filter = st.sidebar.multiselect(
    "Season", sorted(df["season"].unique()), default=sorted(df["season"].unique()))
venue_filter = st.sidebar.multiselect(
    "Venue", sorted(df["venue"].dropna().unique()), default=sorted(df["venue"].dropna().unique()))

with st.sidebar.expander("More filters"):
    alley_filter = st.sidebar.multiselect(
        "Alley", sorted(df["alley"].dropna().unique()), default=sorted(df["alley"].dropna().unique()))
    player_filter = st.sidebar.multiselect(
        "Player", sorted(df["player"].dropna().unique()), default=sorted(df["player"].dropna().unique()))

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

tab_home, tab_players, tab_h2h, tab_alleys, tab_opps, tab_records, tab_clutch, tab_gerald, tab_extra = st.tabs(
    ["📊 Overview", "👤 Players", "🆚 Head to Head", "🎳 Alleys",
     "⚔️ Opponents", "🏆 Records", "🎯 Hold Your Nerve", "🏅 Gerald Trophy", "➕ Extras"]
)

# ------------------------------------------------------- OVERVIEW
with tab_home:
    st.markdown("### Overview")

    c1, c2 = st.columns(2)
    c1.metric("Games", f["gamekey"].nunique())
    c2.metric("Players", f["player"].nunique())
    c3, c4 = st.columns(2)
    c3.metric("Team average", round(f["score"].mean(), 2))
    c4.metric("Best score", int(f["score"].max()))

    tg = (f.drop_duplicates(["season", "game"]).groupby("season")
            .agg(Played=("game", "count"),
                 Won=("result", lambda x: (x == "W").sum()),
                 Lost=("result", lambda x: (x == "L").sum()))
            .reset_index())
    tg["Win %"] = (100 * tg["Won"] / tg["Played"]).round(1)
    st.markdown("#### Season by season")
    st.dataframe(tg, hide_index=True, use_container_width=True)

# ------------------------------------------------------- PLAYERS
with tab_players:
    st.markdown("### Player leaderboard")

    lb = (f.groupby("player")
            .agg(Games=("gamekey", "nunique"),
                 Average=("score", "mean"),
                 Best=("score", "max"))
            .reset_index()
            .sort_values("Average", ascending=False))
    lb["Average"] = lb["Average"].round(2)
    st.dataframe(lb, hide_index=True, use_container_width=True)

    st.markdown("#### Player profile")
    player = st.selectbox("Choose a player", sorted(f["player"].unique()))
    pdf = f[f["player"] == player].sort_values("date", ascending=False)

    m1, m2, m3 = st.columns(3)
    m1.metric("Games", pdf["gamekey"].nunique())
    m2.metric("Average", round(pdf["score"].mean(), 2))
    m3.metric("Best", int(pdf["score"].max()))

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
            unsafe_allow_html=True)

# ------------------------------------------------------- HEAD TO HEAD
with tab_h2h:
    st.markdown("### Head to head")
    st.caption("Compare one player against one opponent.")

    colA, colB = st.columns(2)
    h2h_player = colA.selectbox("Player", sorted(f["player"].unique()), key="h2hp")
    opp_options = sorted(f[f["player"] == h2h_player]["opponent"].dropna().unique())

    if not opp_options:
        st.info("That player has no games with the current filters.")
    else:
        h2h_opp = colB.selectbox("Opponent", opp_options, key="h2ho")
        h2h = f[(f["player"] == h2h_player) & (f["opponent"] == h2h_opp)].sort_values("date")

        games = h2h.drop_duplicates("gamekey")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Games", len(games))
        m2.metric("Won", int(games["result"].eq("W").sum()))
        m3.metric("Lost", int(games["result"].eq("L").sum()))
        m4.metric("Average", round(h2h["score"].mean(), 2))

        st.markdown("#### Head-to-head record")
        for _, g in games.sort_values("date", ascending=False).iterrows():
            res = "W" if g["team_total"] > g["opp_total"] else ("L" if g["team_total"] < g["opp_total"] else "D")
            st.markdown(
                f"""<div class="w-h2h">
                      <div class="w-vs">{h2h_player} vs {h2h_opp} — {g['season']} game {int(g['game'])}</div>
                      <div class="w-score">{int(g['team_total'])}–{int(g['opp_total'])} ({res})</div>
                      <div class="w-sub">{g['venue']} · {g['alley']}</div>
                    </div>""",
                unsafe_allow_html=True)

        st.markdown(f"#### {h2h_player}'s scores in those games")
        st.dataframe(
            h2h[["date", "score", "venue", "alley", "season", "ticks", "spares", "fines"]],
            hide_index=True, use_container_width=True)

# ------------------------------------------------------- ALLEYS
with tab_alleys:
    st.markdown("### Alley form")

    al = (f.groupby("alley")
            .agg(Games=("gamekey", "nunique"),
                 Average=("score", "mean"),
                 Best=("score", "max"))
            .reset_index()
            .sort_values("Average", ascending=False))
    al["Average"] = al["Average"].round(2)
    st.dataframe(al, hide_index=True, use_container_width=True)

    st.markdown("#### Player × Alley")
    mode = st.radio("Show", ["Overall", "Home", "Away", "Cup"], horizontal=True)
    src = f if mode == "Overall" else f[f["venue"] == mode]
    if src.empty:
        st.info("No games for that venue with the current filters.")
    else:
        st.dataframe(src.pivot_table(index="player", columns="alley",
                                     values="score", aggfunc="mean").round(2),
                     use_container_width=True)

# ------------------------------------------------------- OPPONENTS
with tab_opps:
    st.markdown("### Opponents")

    tgames = f.drop_duplicates(["season", "game"])
    opp = (tgames.groupby("opponent")
             .agg(Played=("game", "count"),
                  Won=("result", lambda x: (x == "W").sum()),
                  Lost=("result", lambda x: (x == "L").sum()))
             .reset_index())
    opp["Win %"] = (100 * opp["Won"] / opp["Played"]).round(1)
    st.dataframe(opp.sort_values("Win %", ascending=False), hide_index=True, use_container_width=True)

    st.markdown("#### Player × Opponent")
    mode2 = st.radio("Show", ["Overall", "Home", "Away", "Cup"], horizontal=True, key="oppmode")
    src2 = f if mode2 == "Overall" else f[f["venue"] == mode2]
    if src2.empty:
        st.info("No games for that venue with the current filters.")
    else:
        st.dataframe(src2.pivot_table(index="player", columns="opponent",
                                      values="score", aggfunc="mean").round(2),
                     use_container_width=True)

# ------------------------------------------------------- RECORDS
with tab_records:
    st.markdown("### Records")

    st.markdown("#### 70+ club")
    big = f[f["score"] >= 70].sort_values("score", ascending=False)
    if big.empty:
        st.info("No scores of 70 or more with the current filters.")
    else:
        st.dataframe(big[["score", "player", "opponent", "venue", "alley", "season"]],
                     hide_index=True, use_container_width=True)

    st.markdown("#### Best team totals")
    tt = f.drop_duplicates(["season", "game"]).sort_values("team_total", ascending=False)
    st.dataframe(tt[["team_total", "opp_total", "opponent", "venue", "alley", "season"]].head(15),
                 hide_index=True, use_container_width=True)

    st.markdown("#### Best individual legs")
    if os.path.exists("skittles-legs.csv"):
        legs = pd.read_csv("skittles-legs.csv")
        legs.columns = legs.columns.astype(str).str.strip().str.lower()
        legs = legs[legs["season"].isin(season_filter)]
        st.dataframe(
            legs.sort_values("leg_score", ascending=False)
                [["leg_score", "player", "opponent", "alley", "season", "tick"]].head(15),
            hide_index=True, use_container_width=True)
    else:
        st.info("Add `skittles-legs.csv` to the repo to show leg records.")

# ------------------------------------------------------- NERVE
with tab_clutch:
    st.markdown("### 🎯 Hold Your Nerve")
    st.caption(
        "Tight wins — decided by 10 pins or fewer — and the best scores "
        "in the final leg of the match."
    )

    _legs = None
    if os.path.exists("skittles-legs.csv"):
        _legs = pd.read_csv("skittles-legs.csv")
        _legs.columns = _legs.columns.astype(str).str.strip().str.lower()

    if _legs is None or "result" not in _legs.columns or "margin" not in _legs.columns:
        st.info(
            "Add the updated `skittles-legs.csv` to the repo to show this tab — "
            "it needs the `margin`, `result` and `leg` columns."
        )
    else:
        _legs = _legs[_legs["season"].isin(season_filter)]

        # tight wins, then the final leg only (leg 8)
        tight_wins = _legs[(_legs["result"] == "W") & (_legs["margin"].between(1, 10))]
        final = tight_wins[tight_wins["leg"] == 8].copy()

        if final.empty:
            st.info("No tight wins with the current filters.")
        else:
            matches = final[["season", "game"]].drop_duplicates().shape[0]

            c1, c2, c3 = st.columns(3)
            c1.metric("Tight wins", matches)
            c2.metric("Final legs", len(final))
            c3.metric("Best final leg", int(final["leg_score"].max()))

            st.markdown("#### Held their nerve")
            for _, r in final.sort_values("leg_score", ascending=False).iterrows():
                st.markdown(
                    f"""<div class="w-card">
                          <div class="w-big">{int(r['leg_score'])}</div>
                          <div class="w-name">{r['player']}</div>
                          <div class="w-sub">{r['season']} · vs {r['opponent']} · {r['venue']} · won by {int(r['margin'])}</div>
                        </div>""",
                    unsafe_allow_html=True)

# ------------------------------------------------------- EXTRAS
with tab_extra:
    st.markdown("### Ticks, spares & fines")

    x = (f.groupby("player")
           .agg(Games=("gamekey", "nunique"),
                Ticks=("ticks", "sum"),
                Spares=("spares", "sum"),
                Fines=("fines", "sum"),
                Sunshine=("sunshine", "sum"),
                MissedSingle=("missedsingle", "sum"),
                Flopper=("flopper", "sum"),
                Spare9=("spare9", "sum"))
           .reset_index()
           .sort_values("Fines", ascending=False))

    # tick average per game
    x["Tick Avg"] = (x["Ticks"] / x["Games"]).round(2)

    x = _fines_with_pound(x)          # show fines as £0.00

    st.dataframe(
        x[["player", "Games", "Ticks", "Tick Avg", "Spares",
           "Fines", "Sunshine", "MissedSingle", "Flopper", "Spare9"]],
        hide_index=True, use_container_width=True)

    st.markdown("#### Totals")
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("Ticks", int(f["ticks"].sum()))
    t2.metric("Tick average", round(f["ticks"].sum() / max(f["gamekey"].nunique(), 1), 2))
    t3.metric("Spares", int(f["spares"].sum()))
    t4.metric("Fines", f"£{f['fines'].sum():,.2f}")


# -------------------------------------------------------------------
# THE GERALD TROPHY — most ticks in a single match, per season
# -------------------------------------------------------------------
with tab_gerald:
    st.markdown("### 🏅 The Gerald Trophy")
    st.caption("Most ticks in a single match, each season.")

    seasons_for_trophy = sorted(f["season"].unique(), reverse=True)

    for season in seasons_for_trophy:
        season_rows = f[f["season"] == season]
        if season_rows.empty or season_rows["ticks"].max() == 0:
            st.markdown(f"**{season}** — no ticks recorded")
            continue

        # the raw best in the data
        best = season_rows["ticks"].max()
        winners = sorted(season_rows[season_rows["ticks"] == best]["player"].unique())

        # committee overrides — judgement calls the data can't show
        override = TROPHY_OVERRIDES.get(season)
        if override:
            winners = [override["awarded_to"]]
            best = override["ticks"]
        detail = (season_rows[(season_rows["ticks"] == best)
                              & (season_rows["player"].isin(winners))]
                    .drop_duplicates(["game"])
                    .sort_values("date"))

        st.markdown(f"#### {season}")
        w1, w2 = st.columns([2, 1])
        w1.markdown(
            f"""<div class="w-h2h">
                  <div class="w-vs">{' & '.join(winners)}</div>
                  <div class="w-score">{int(best)} ticks</div>
                  <div class="w-sub">{'in a single match' if len(detail) <= 1 else 'in ' + str(len(detail)) + ' matches'}</div>
                </div>""",
            unsafe_allow_html=True)
        w2.dataframe(
            detail[["opponent", "venue", "alley"]].rename(
                columns={"opponent": "Opponent", "venue": "Venue", "alley": "Alley"}),
            hide_index=True, use_container_width=True)

    st.markdown("#### All-time best")
    eligible = f[~f["player"].isin(TROPHY_EXCLUDE)]
    if not eligible.empty and eligible["ticks"].max() > 0:
        allbest = eligible["ticks"].max()
        allholders = sorted(eligible[eligible["ticks"] == allbest]["player"].unique())
        st.markdown(f"**{int(allbest)} ticks** — {' & '.join(allholders)}")

    st.caption("Awarded for the most ticks in a single match.")


# -------------------------------------------------------------------
# FOOTER — last updated
# -------------------------------------------------------------------

_last_game = f["date"].max()
_last_season = f.loc[f["date"] == _last_game, "season"].iloc[0] if pd.notna(_last_game) else ""

st.divider()
if pd.notna(_last_game):
    st.caption(
        f"Last updated: **{_last_game:%d %B %Y}** "
        f"({_last_season}) · {len(df):,} player-games across "
        f"{df['season'].nunique()} seasons"
    )
else:
    st.caption(f"Last updated: date unavailable · {len(df):,} player-games")
