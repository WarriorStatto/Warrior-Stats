"""
pages/2_Positions.py — batting position analysis.

Two views:
  1. Best position per player, by raw average.
  2. Where each player beats their OWN career average — the more useful
     signal, since it strips out the fact that strong players already bat
     in certain slots.

Built from skittles-positions.csv, which carries one row per player per
game with the position they batted in.
"""

import os
import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(
    page_title="Positions",
    page_icon="🎯",
    layout="centered",
    initial_sidebar_state="collapsed",
)

GREEN = "C5E0B4"
CREAM = "FDEADA"
SALMON = "FCD5B5"

st.markdown(f"""
<style>
  .block-container {{ padding-top: 1.2rem; padding-bottom: 2rem; max-width: 900px; }}
  h1 {{ font-size: 1.5rem !important; }}
  h3 {{ font-size: 1.1rem !important; }}
  div[data-testid="stMetricValue"] {{ font-size: 1.3rem; }}
  .w-card {{
      background: #{CREAM};
      border-left: 5px solid #{GREEN};
      border-radius: 8px;
      padding: 0.7rem 0.9rem;
      margin-bottom: 0.5rem;
  }}
  .w-best {{ border-left-color: #{SALMON}; }}
  .w-big  {{ font-size: 1.3rem; font-weight: 700; }}
  .w-name {{ font-weight: 600; font-size: 1rem; }}
  .w-sub  {{ font-size: 0.8rem; color: #555; }}
</style>
""", unsafe_allow_html=True)


# -------------------------------------------------------------------
# DATA
# -------------------------------------------------------------------

CANDIDATES = ["../skittles-positions.csv", "skittles-positions.csv",
              "data/skittles-positions.csv"]


@st.cache_data
def load(path):
    df = pd.read_csv(path)
    df.columns = (df.columns.astype(str).str.strip().str.lower()
                    .str.replace(" ", "", regex=False))
    for c in ["score", "ticks", "margin", "position", "team_total", "opp_total"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


path = next((p for p in CANDIDATES if os.path.exists(p)), None)
if path is None:
    st.error("### Data file not found")
    st.markdown(
        "This page needs `skittles-positions.csv` in the repo, in the same "
        "folder as `app.py`."
    )
    st.stop()

df = load(path)
df = df[df["position"].between(1, 8)]

st.title("🎯 Batting positions")

MIN_GAMES = st.slider(
    "Minimum games at a position (for the recommendations)",
    min_value=1, max_value=10, value=3,
    help="A player needs at least this many games in a slot to be considered.",
)

SQUAD = sorted(df["player"].dropna().unique())
lineup = st.multiselect(
    "Players to consider (leave empty for the whole squad)",
    SQUAD, default=[],
)
focus = lineup if lineup else SQUAD


# -------------------------------------------------------------------
# 1. HOW EACH POSITION SCORES, EVERYONE COMBINED
# -------------------------------------------------------------------

st.divider()
st.markdown("### Position by position")
st.caption("Every player-game across all seasons, grouped by batting slot.")

overall = (df.groupby("position")
             .agg(Games=("score", "count"),
                  Average=("score", "mean"),
                  Best=("score", "max"),
                  Sixties=("score", lambda s: int((s >= 60).sum())))
             .reset_index())
overall["Average"] = overall["Average"].round(1)
overall["SixtyPlus %"] = (100 * overall["Sixties"] / overall["Games"]).round(1)
st.dataframe(overall, hide_index=True, use_container_width=True)

st.caption(
    "Positions 7 and 8 score noticeably higher — but that reflects who "
    "bats there, not the slot itself."
)


# -------------------------------------------------------------------
# 2. THE PLAYER x POSITION MATRIX
# -------------------------------------------------------------------

st.divider()
st.markdown("### Player × position")
st.caption(
    "Average score for each player in each slot. Blank means they have "
    "never batted there."
)

matrix_rows = []
for p in focus:
    sub = df[df["player"] == p]
    row = {"Player": p}
    for pos in range(1, 9):
        rs = sub[sub["position"] == pos]
        if rs.empty:
            row[f"Pos {pos}"] = ""
        else:
            avg = rs["score"].mean()
            row[f"Pos {pos}"] = round(avg, 1) if len(rs) >= MIN_GAMES else f"({avg:.0f})"
    row["Games"] = len(sub)
    row["Career"] = round(sub["score"].mean(), 1) if len(sub) else ""
    matrix_rows.append(row)

matrix_df = pd.DataFrame(matrix_rows)
st.dataframe(matrix_df, hide_index=True, use_container_width=True)

st.caption(
    f"Figures in brackets are from fewer than {MIN_GAMES} games — a hint, "
    "not a record. Raise the minimum slider to hide them."
)

# games played at each slot, so the sample size is visible
st.markdown("##### Games played at each slot")
count_rows = []
for p in focus:
    sub = df[df["player"] == p]
    row = {"Player": p}
    for pos in range(1, 9):
        row[f"Pos {pos}"] = int((sub["position"] == pos).sum()) or ""
    count_rows.append(row)
st.dataframe(pd.DataFrame(count_rows), hide_index=True, use_container_width=True)


# -------------------------------------------------------------------
# 3. BEST POSITION PER PLAYER (RAW AVERAGE)
# -------------------------------------------------------------------

st.divider()
st.markdown("### Best position by average")
st.caption(f"Players with at least {MIN_GAMES} game(s) in the slot.")

rows = []
for p in focus:
    sub = df[df["player"] == p]
    career = sub["score"].mean()
    best = None
    for pos in range(1, 9):
        rs = sub[sub["position"] == pos]
        if len(rs) < MIN_GAMES:
            continue
        avg = rs["score"].mean()
        if best is None or avg > best[1]:
            best = (pos, avg, len(rs), rs["score"].max())
    if best:
        rows.append({
            "Player": p,
            "Best position": int(best[0]),
            "Average there": round(best[1], 1),
            "Games": best[2],
            "Best score": int(best[3]),
            "Career average": round(career, 1),
        })

best_df = pd.DataFrame(rows).sort_values("Average there", ascending=False)
st.dataframe(best_df, hide_index=True, use_container_width=True)


# -------------------------------------------------------------------
# 3. WHERE THEY BEAT THEIR OWN AVERAGE  (the useful one)
# -------------------------------------------------------------------

st.divider()
st.markdown("### Above their own average")
st.caption(
    "How much better each player scores in a slot than their career "
    "average. This strips out the fact that the strongest players already "
    "bat at 7 and 8."
)

gain_rows = []
for p in focus:
    sub = df[df["player"] == p]
    if sub.empty:
        continue
    career = sub["score"].mean()
    for pos in range(1, 9):
        rs = sub[sub["position"] == pos]
        if len(rs) < MIN_GAMES:
            continue
        avg = rs["score"].mean()
        gain_rows.append({
            "Player": p,
            "Position": pos,
            "Average": round(avg, 1),
            "Career avg": round(career, 1),
            "Gain": round(avg - career, 1),
            "Games": len(rs),
        })

gain_df = pd.DataFrame(gain_rows)
if gain_df.empty:
    st.info("Not enough games at any position with the current minimum.")
else:
    gain_df = gain_df.sort_values("Gain", ascending=False)
    st.dataframe(gain_df.head(15), hide_index=True, use_container_width=True)

    # headline gains, as cards
    st.markdown("##### Standout gains")
    for _, r in gain_df[gain_df["Gain"] >= 3].head(6).iterrows():
        st.markdown(
            f"""<div class="w-card w-best">
                  <div class="w-big">+{r['Gain']:.1f}</div>
                  <div class="w-name">{r['Player']} at position {int(r['Position'])}</div>
                  <div class="w-sub">{r['Average']} there vs {r['Career avg']} career · {int(r['Games'])} games</div>
                </div>""",
            unsafe_allow_html=True)


# -------------------------------------------------------------------
# 4. SUGGESTED ORDER
# -------------------------------------------------------------------

st.divider()
st.markdown("### Suggested order")
st.caption(
    "Greedy pick: the strongest above-average slot first, one player per "
    "position. A prompt for the captain, not a settled line-up."
)

# score each player-position on gain, fall back to raw average
scores = []
for p in focus:
    sub = df[df["player"] == p]
    if sub.empty:
        continue
    career = sub["score"].mean()
    for pos in range(1, 9):
        rs = sub[sub["position"] == pos]
        if len(rs) < MIN_GAMES:
            continue
        avg = rs["score"].mean()
        scores.append({
            "player": p, "position": pos,
            "gain": avg - career, "avg": avg, "n": len(rs),
        })

scores_df = pd.DataFrame(scores)
if scores_df.empty:
    st.info("Not enough data to suggest an order with this minimum.")
else:
    # greedy: each round take the highest gain still available
    taken_players, taken_positions, order = set(), set(), []
    for _ in range(8):
        avail = scores_df[~scores_df["player"].isin(taken_players)
                          & ~scores_df["position"].isin(taken_positions)]
        if avail.empty:
            break
        top = avail.sort_values(["gain", "avg"], ascending=False).iloc[0]
        order.append(top)
        taken_players.add(top["player"])
        taken_positions.add(int(top["position"]))

    # players left over once the recommendations have taken their pick
    leftovers = [p for p in focus if p not in taken_players]
    filled_positions = {int(r["position"]) for r in order}
    empty_positions = [p for p in range(1, 9) if p not in filled_positions]

    # build the full order: recommendations first, then leftovers in the gaps
    full_order = []
    for r in order:
        full_order.append({
            "position": int(r["position"]),
            "player": r["player"],
            "detail": f"{r['avg']:.1f} avg there · {r['gain']:+.1f} vs career · {int(r['n'])} games",
            "captains": False,
        })

    leftover_iter = iter(leftovers)
    for pos in empty_positions:
        try:
            p = next(leftover_iter)
        except StopIteration:
            break
        sub = df[df["player"] == p]
        full_order.append({
            "position": pos,
            "player": p,
            "detail": "captain's choice",
            "captains": True,
        })

    for r in sorted(full_order, key=lambda x: x["position"]):
        cls = "w-card w-best" if r["captains"] else "w-card"
        st.markdown(
            f"""<div class="{cls}">
                  <div class="w-big">{r['position']}</div>
                  <div class="w-name">{r['player']}</div>
                  <div class="w-sub">{r['detail']}</div>
                </div>""",
            unsafe_allow_html=True)

    if any(r["captains"] for r in full_order):
        st.caption(
            "Positions marked *captain's choice* have no qualifying record — "
            "they are filled from the remaining players so the order is "
            "complete."
        )

st.divider()
st.caption(f"Based on {len(df):,} player-games across {df['season'].nunique()} seasons.")
