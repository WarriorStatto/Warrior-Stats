"""
pages/1_Match_Briefing.py — pre-match briefing.

Pick the upcoming fixture (opponent + alley), tick off the players in the
line-up, and see how everyone has fared against that team and at that ground.

Streamlit picks this up automatically from the `pages/` folder next to
app.py. The sidebar in app.py does not apply here, so the page carries its
own controls.
"""

import os
import pandas as pd
import numpy as np
import streamlit as st

# -------------------------------------------------------------------
# CONFIG
# -------------------------------------------------------------------

st.set_page_config(
    page_title="Match Briefing",
    page_icon="📋",
    layout="centered",
    initial_sidebar_state="collapsed",
)

GREEN  = "C5E0B4"
BLUE   = "C6D9F1"
CREAM  = "FDEADA"
SALMON = "FCD5B5"

st.markdown(f"""
<style>
  .block-container {{ padding-top: 1.2rem; padding-bottom: 2rem; max-width: 900px; }}
  h1 {{ font-size: 1.5rem !important; }}
  h3 {{ font-size: 1.1rem !important; }}
  div[data-testid="stMetricValue"] {{ font-size: 1.3rem; }}
  div[data-testid="stMetricLabel"] {{ font-size: 0.8rem; }}
  .w-card {{
      background: #{CREAM};
      border-left: 5px solid #{GREEN};
      border-radius: 8px;
      padding: 0.7rem 0.9rem;
      margin-bottom: 0.5rem;
  }}
  .w-result {{
      background: #{CREAM};
      border-left: 5px solid #{SALMON};
      border-radius: 8px;
      padding: 0.6rem 0.9rem;
      margin-bottom: 0.4rem;
  }}
  .w-big   {{ font-size: 1.4rem; font-weight: 700; }}
  .w-name  {{ font-weight: 600; font-size: 1rem; }}
  .w-sub   {{ font-size: 0.8rem; color: #555; }}
  .w-win   {{ color: #1a7f37; font-weight: 700; }}
  .w-loss  {{ color: #b42318; font-weight: 700; }}
</style>
""", unsafe_allow_html=True)


# -------------------------------------------------------------------
# DATA
# -------------------------------------------------------------------

DATA_CANDIDATES = [
    "../skittles-import.csv",
    "skittles-import.csv",
    "data/skittles-import.csv",
]


@st.cache_data
def load_data(path):
    df = pd.read_csv(path)
    df.columns = (df.columns.astype(str).str.strip().str.lower()
                    .str.replace(" ", "", regex=False)
                    .str.replace("_", "", regex=False))
    for col in ["score", "ticks", "spares", "fines", "teamtotal", "opptotal"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["result"] = np.where(df["teamtotal"] > df["opptotal"], "W",
                     np.where(df["teamtotal"] < df["opptotal"], "L", "D"))
    return df


_path = next((p for p in DATA_CANDIDATES if os.path.exists(p)), None)
if _path is None:
    st.error("### Data file not found")
    st.markdown(
        "This page needs `skittles-import.csv` in the repo, in the same "
        "folder as `app.py`."
    )
    st.stop()

df = load_data(_path)

# one row per game, for team-level records
games = df.drop_duplicates(["season", "game"]).copy()


# -------------------------------------------------------------------
# PICK THE FIXTURE
# -------------------------------------------------------------------

st.title("📋 Match Briefing")

st.markdown("#### The fixture")
colA, colB = st.columns(2)

opponents = sorted(df["opponent"].dropna().unique())
opponent = colA.selectbox("Opponent", opponents, key="brief_opp")

alleys = sorted(df["alley"].dropna().unique())
alley = colB.selectbox("Alley", alleys, key="brief_alley")

squad = sorted(df["player"].dropna().unique())
lineup = st.multiselect(
    "Players in the line-up (leave empty for the whole squad)",
    squad,
    default=[],
    key="brief_lineup",
)

# if no line-up chosen, cover everyone
focus = lineup if lineup else squad


# -------------------------------------------------------------------
# OUR RECORD AGAINST THEM
# -------------------------------------------------------------------

st.divider()
st.markdown(f"### vs {opponent}")

h2h = games[games["opponent"] == opponent]
played = len(h2h)
won = int((h2h["result"] == "W").sum())
lost = int((h2h["result"] == "L").sum())
winpct = round(100 * won / played, 1) if played else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Played", played)
c2.metric("Won", won)
c3.metric("Lost", lost)
c4.metric("Win %", winpct)

if played:
    c5, c6 = st.columns(2)
    c5.metric("Our average", round(h2h["teamtotal"].mean(), 1))
    c6.metric("Their average", round(h2h["opptotal"].mean(), 1))

    st.markdown("##### Recent meetings")
    for _, g in h2h.sort_values("date", ascending=False).head(5).iterrows():
        cls = "w-win" if g["result"] == "W" else "w-loss"
        st.markdown(
            f"""<div class="w-result">
                  <div class="w-name">{int(g['teamtotal'])}–{int(g['opptotal'])} <span class="{cls}">({g['result']})</span></div>
                  <div class="w-sub">{g['season']} · {g['venue']} · {g['alley']} · {g['date']:%d %b %Y}</div>
                </div>""",
            unsafe_allow_html=True)
else:
    st.info(f"No previous meetings with {opponent} in the data.")


# -------------------------------------------------------------------
# OUR RECORD AT THE ALLEY
# -------------------------------------------------------------------

st.divider()
st.markdown(f"### At {alley}")

at_alley = games[games["alley"] == alley]
a_played = len(at_alley)
a_won = int((at_alley["result"] == "W").sum())
a_lost = int((at_alley["result"] == "L").sum())

a1, a2, a3, a4 = st.columns(4)
a1.metric("Played", a_played)
a2.metric("Won", a_won)
a3.metric("Lost", a_lost)
a4.metric("Win %", round(100 * a_won / a_played, 1) if a_played else 0)

if a_played:
    a5, a6 = st.columns(2)
    a5.metric("Our average", round(at_alley["teamtotal"].mean(), 1))
    a6.metric("Opposition average", round(at_alley["opptotal"].mean(), 1))

    # player averages at this ground — line-up only
    st.markdown("##### Form at this alley")
    if lineup:
        st.caption("Selected players only.")
    plyr = (df[(df["alley"] == alley) & (df["player"].isin(focus))]
              .groupby("player")
              .agg(Games=("score", "count"),
                   Average=("score", "mean"),
                   Best=("score", "max"))
              .reset_index())
    plyr["Average"] = plyr["Average"].round(2)
    if plyr.empty:
        st.info("None of the selected players have played at this alley before.")
    else:
        st.dataframe(plyr.sort_values("Average", ascending=False),
                     hide_index=True, use_container_width=True)
else:
    st.info(f"No games recorded at {alley}.")


# -------------------------------------------------------------------
# THE LINE-UP
# -------------------------------------------------------------------

st.divider()
st.markdown("### The line-up")
if lineup:
    st.caption("Statistics below cover the selected players only.")
else:
    st.caption("No line-up selected — showing the whole squad.")

rows = []
for p in focus:
    vs_them = df[(df["player"] == p) & (df["opponent"] == opponent)]
    at_ground = df[(df["player"] == p) & (df["alley"] == alley)]

    def stats(frame):
        if frame.empty:
            return ("—", "—", "—", "—")
        scores = frame["score"]
        # win/loss from the team result in those games
        gs = frame.drop_duplicates(["season", "game"])
        w = int((gs["result"] == "W").sum())
        l = int((gs["result"] == "L").sum())
        return (len(gs), round(scores.mean(), 1), int(scores.max()), f"{w}–{l}")

    v_games, v_avg, v_best, v_record = stats(vs_them)
    a_games, a_avg, a_best, a_record = stats(at_ground)

    rows.append({
        "Player": p,
        f"vs {opponent} — games": v_games,
        f"vs {opponent} — avg": v_avg,
        f"vs {opponent} — best": v_best,
        f"vs {opponent} — W–L": v_record,
        f"at {alley} — games": a_games,
        f"at {alley} — avg": a_avg,
        f"at {alley} — best": a_best,
        f"at {alley} — W–L": a_record,
    })

lineup_df = pd.DataFrame(rows)
st.dataframe(lineup_df, hide_index=True, use_container_width=True)

# a quick read on who travels well
st.markdown("##### Worth noting")
notes = []
for r in rows:
    vkey = f"vs {opponent} — avg"
    akey = f"at {alley} — avg"
    if r[vkey] != "—" and isinstance(r[vkey], (int, float)) and r[vkey] >= 60:
        notes.append(f"- **{r['Player']}** averages **{r[vkey]}** against {opponent}")
    if r[akey] != "—" and isinstance(r[akey], (int, float)) and r[akey] >= 60:
        notes.append(f"- **{r['Player']}** averages **{r[akey]}** at {alley}")
if notes:
    st.markdown("\n".join(notes[:8]))
else:
    st.markdown("_No standout averages (60+) in these records yet._")

st.divider()
_last = df["date"].max()
if pd.notna(_last):
    st.caption(f"Based on {len(df):,} player-games up to **{_last:%d %B %Y}**")
