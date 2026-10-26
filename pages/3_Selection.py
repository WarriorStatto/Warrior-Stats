"""
pages/3_Selection.py — who plays, and in what order.

Applies the club's selection policy, in the order the rules take effect:

  1. SEASON START — the top 8 by career average (available).
     Only applies until everyone has had a game.

  2. WEEKLY — of the available players, the 4 who scored highest in the
     PREVIOUS game go straight in. This always runs, all season.

  3. UNTIL EVERYONE HAS PLAYED — the remaining slots go to the next best
     by previous seasons' average.

  4. ONCE EVERYONE HAS PLAYED — the remaining slots go to whoever has
     waited longest. Ties broken by the previous game's score, then by
     last season's average.

The top 4 (rule 2) always take their slots first, so a player in form can be
picked every week while someone else waits.

AVAILABILITY
------------
Nobody is picked unless they are ticked. Tick the players who replied yes
to the Saturday message and only they are considered — the season-start
rule included.

BOWLING ORDER
-------------
Once the eight are chosen, their order comes from the Positions page: the
same player x position blend, so the running order matches what that page
suggests.

MANUAL OVERRIDE
---------------
Every pick can be replaced by hand from a dropdown. An overridden slot is
marked, and the reason the app would have chosen someone else stays on
screen so nothing is lost.
"""

import os

import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(
    page_title="Selection",
    page_icon="🗳️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

GREEN = "C5E0B4"
CREAM = "FDEADA"
SALMON = "FCD5B5"

st.markdown(f"""
<style>
  .block-container {{ padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1000px; }}
  h1 {{ font-size: 1.5rem !important; }}
  h3 {{ font-size: 1.15rem !important; }}
  div[data-testid="stMetricValue"] {{ font-size: 1.3rem; }}
  .sel-card {{
      background: #{CREAM};
      border-left: 5px solid #{GREEN};
      border-radius: 8px;
      padding: 0.55rem 0.85rem;
      margin-bottom: 0.4rem;
  }}
  .sel-card.over {{ border-left-color: #b42318; }}
  .sel-pos {{ font-size: 1.15rem; font-weight: 700; }}
  .sel-name {{ font-weight: 600; }}
  .sel-why {{ font-size: 0.82rem; color: #555; }}
</style>
""", unsafe_allow_html=True)


# -------------------------------------------------------------------
# DATA
# -------------------------------------------------------------------

DATA_CANDIDATES = ["../skittles-import.csv", "skittles-import.csv",
                   "data/skittles-import.csv"]
POSITION_CANDIDATES = ["../skittles-positions.csv", "skittles-positions.csv",
                       "data/skittles-positions.csv"]


@st.cache_data
def load_data(path):
    df = pd.read_csv(path)
    df.columns = (df.columns.astype(str).str.strip().str.lower()
                    .str.replace(" ", "", regex=False)
                    .str.replace("_", "", regex=False))
    for col in ["score", "ticks"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["gamekey"] = df["season"].astype(str) + "-" + df["game"].astype(str)
    return df


@st.cache_data
def load_positions(path):
    p = pd.read_csv(path)
    p.columns = (p.columns.astype(str).str.strip().str.lower()
                   .str.replace(" ", "", regex=False))
    for c in ["score", "position"]:
        if c in p.columns:
            p[c] = pd.to_numeric(p[c], errors="coerce")
    return p[p["position"].between(1, 8)]


_path = next((p for p in DATA_CANDIDATES if os.path.exists(p)), None)
if _path is None:
    st.error("### Data file not found")
    st.markdown("This page needs `skittles-import.csv` in the repo, in the "
                "same folder as `app.py`.")
    st.stop()
df = load_data(_path)

_pos_path = next((p for p in POSITION_CANDIDATES if os.path.exists(p)), None)
pos_df = load_positions(_pos_path) if _pos_path else None


# -------------------------------------------------------------------
# THE SEASON WE ARE PICKING FOR
# -------------------------------------------------------------------

SEASONS = sorted(df["season"].dropna().astype(str).unique())
CURRENT = SEASONS[-1]
PREVIOUS = SEASONS[-2] if len(SEASONS) > 1 else SEASONS[-1]

st.title("🗳️ Team selection")
st.caption(f"Picking for **{CURRENT}** · previous season is **{PREVIOUS}**")


# -------------------------------------------------------------------
# THE FACTS THE RULES NEED
# -------------------------------------------------------------------

squad = sorted(df["player"].dropna().unique())

# career average, all seasons
_career = df.groupby("player")["score"].mean().round(2)

# previous season's average
_prev = (df[df["season"] == PREVIOUS].groupby("player")["score"].mean().round(2))

# games played this season, and most recent appearance
_cur = df[df["season"] == CURRENT]
played_this = set(_cur["player"].dropna().unique())
last_seen = {}
for player in squad:
    p_rows = df[df["player"] == player]
    if p_rows.empty:
        continue
    idx = p_rows["date"].idxmax()
    last_seen[player] = p_rows.loc[idx, "gamekey"]

# the previous game: scores, and who played in it
_cur_games = sorted(_cur["game"].dropna().unique())
if _cur_games:
    last_game = _cur_games[-1]
    _lg = _cur[_cur["game"] == last_game]
    last_scores = dict(zip(_lg["player"], _lg["score"]))
    played_last = set(_lg["player"])
else:
    last_game, last_scores, played_last = None, {}, set()

everyone_played = set(squad) - played_this


# -------------------------------------------------------------------
# AVAILABILITY — the Saturday WhatsApp replies
# -------------------------------------------------------------------

st.markdown("### 1. Who's available?")
st.caption(
    "Tick everyone who replied yes. Nobody outside this list is picked, "
    "whatever their record."
)

with st.expander("Tick the available players", expanded=True):
    c1, c2 = st.columns(2)
    if c1.button("Select all", key="av_all"):
        for p in squad:
            st.session_state[f"av_{p}"] = True
    if c2.button("Clear all", key="av_none"):
        for p in squad:
            st.session_state[f"av_{p}"] = False

    cols = st.columns(3)
    for i, p in enumerate(squad):
        cols[i % 3].checkbox(p, key=f"av_{p}", value=True)

available = [p for p in squad if st.session_state.get(f"av_{p}", True)]

if not available:
    st.warning("Nobody ticked — tick at least one player to see a selection.")
    st.stop()


# -------------------------------------------------------------------
# APPLY THE RULES
# -------------------------------------------------------------------
#
# Rule 1  season start      top 8 by career average, available
# Rule 2  every week        the 4 highest scorers from the PREVIOUS game,
#                           if available. If fewer than four reply, the
#                           unfilled slots pass straight to the pool below —
#                           they are NOT given to the 5th, 6th ... scorer.
# Rule 3  priority pool     players who have NOT played this season go in
#                           first, best previous-season average first.
# Rule 4  the rest          once the unplayed are used up, remaining slots
#                           go to whoever has waited longest. Ties broken by
#                           the last game's score, then previous season's
#                           average.

played_this_season = set(_cur["player"].dropna().unique())


def joint_positions(values, take, best_first=True):
    """Indices of the joint winners of `take` places.

    A tie is never split: if the 4th and 5th best values are equal, both are
    returned. So this can return more than `take` entries.
    """
    ordered = sorted(enumerate(values),
                     key=lambda t: (-t[1] if best_first else t[1]))
    if len(ordered) <= take:
        return [i for i, _ in ordered]
    cut = ordered[take - 1][1]                      # the value on the boundary
    return [i for i, v in ordered if (v >= cut if best_first else v <= cut)]


def wait_key(p):
    """Longest wait first: earliest last appearance, then best last score,
    then best previous-season average."""
    seen = last_seen.get(p, "")
    score = last_scores.get(p)
    prev_avg = _prev.get(p, 0)
    return (
        seen,                                     # earlier = waited longer
        -(score if pd.notna(score) else -1),      # then highest last score
        -prev_avg,                                # then best last-season avg
    )


picks = []
taken = set()

# --- rule 2: the previous game's top four, if available ------------
# The top four belong to the MATCH, not to whoever replied. Work them out
# from everyone who played that night, then keep only those who are available.
# If one of the four is unavailable his slot stays EMPTY and passes to the
# pool below — the 5th-highest scorer does not move up into it.
match_pool = sorted(
    [(p, sc) for p, sc in last_scores.items() if pd.notna(sc)],
    key=lambda t: -t[1],
)

top4_names = []
if match_pool:
    scores = [sc for _, sc in match_pool]
    keep = joint_positions(scores, 4, best_first=True)
    top4_names = [match_pool[i][0] for i in keep]

top4_in = [p for p in top4_names if p in available]
missing = [p for p in top4_names if p not in available]

for p in top4_in:
    picks.append({
        "player": p,
        "rule": "Last game — top 4",
        "why": (f"scored {int(last_scores[p])} in the last game"
                + (f" · top 4 of the match, {len(top4_names)} joint"
                   if len(top4_names) > 4 else "")),
    })
    taken.add(p)
if missing:
    st.caption(
        "Not available from last game's top four: "
        + ", ".join(f"**{m}**" for m in missing)
        + " — those slots pass to the pool below."
    )

# --- rule 1: the season's opening selection ------------------------
if not _cur_games:
    rest = [p for p in available if p not in taken]
    rest.sort(key=lambda p: -_career.get(p, 0))
    for p in rest[:8 - len(picks)]:
        picks.append({
            "player": p,
            "rule": "Season start — top 8",
            "why": f"career average {_career.get(p, 0):.1f}",
        })
        taken.add(p)
else:
    # --- rule 3: the unplayed go in first, best previous average first
    unplayed = [p for p in available
                if p not in played_this_season and p not in taken]
    unplayed.sort(key=lambda p: -_prev.get(p, 0))
    for p in unplayed[:8 - len(picks)]:
        avg = _prev.get(p)
        why = (f"not yet played this season · {PREVIOUS} average {avg:.1f}"
               if avg is not None
               else f"not yet played this season · no games in {PREVIOUS}")
        picks.append({"player": p, "rule": "Not yet played this season",
                      "why": why})
        taken.add(p)

    # --- rule 4: the rest, by longest wait --------------------------
    # The four lowest scorers from the last game drop to the back of the
    # queue, however long they have waited. Ties on that boundary are not
    # split, so possibly more than four go back.
    bottom = set()
    if last_game_pool:
        _sc = [sc for _, sc in last_game_pool]
        for i in joint_positions(_sc, 4, best_first=False):
            bottom.add(last_game_pool[i][0])

    rest = [p for p in available if p not in taken]
    rest.sort(key=lambda p: (p in bottom, ) + wait_key(p))
    for p in rest[:8 - len(picks)]:
        seen = last_seen.get(p)
        s_last = last_scores.get(p)
        bits = [f"last played {seen}" if seen else "no previous games"]
        if p in bottom:
            bits.append("bottom 4 last game — pushed back")
        if pd.notna(s_last):
            bits.append(f"scored {int(s_last)}")
        prev_avg = _prev.get(p)
        if prev_avg is not None:
            bits.append(f"{PREVIOUS} average {prev_avg:.1f}")
        picks.append({"player": p, "rule": "Longest since played",
                      "why": " · ".join(bits)})
        taken.add(p)


# -------------------------------------------------------------------
# BOWLING ORDER from the chosen eight
# -------------------------------------------------------------------

def bowling_order(players, frame, min_games=3):
    """The same blend the Positions page uses, for these players only."""
    if frame is None or frame.empty:
        return {p: i + 1 for i, p in enumerate(players)}
    scores = []
    for p in players:
        sub = frame[frame["player"] == p]
        if sub.empty:
            continue
        for pos in range(1, 9):
            rs = sub[sub["position"] == pos]
            if len(rs) < min_games:
                continue
            n = len(rs)
            avg = rs["score"].mean()
            scores.append({"player": p, "position": pos, "avg": avg,
                           "blend": avg * (1 - 1 / (n + 1))})
    if not scores:
        return {p: i + 1 for i, p in enumerate(players)}
    sdf = pd.DataFrame(scores)
    taken_p, taken_pos, order = set(), set(), {}
    for _ in range(8):
        avail = sdf[~sdf["player"].isin(taken_p) & ~sdf["position"].isin(taken_pos)]
        if avail.empty:
            break
        top = avail.sort_values(["blend", "avg"], ascending=False).iloc[0]
        order[top["player"]] = int(top["position"])
        taken_p.add(top["player"])
        taken_pos.add(int(top["position"]))
    gaps = [i for i in range(1, 9) if i not in taken_pos]
    for p, pos in zip([x for x in players if x not in order], gaps):
        order[p] = pos
    return order


order = bowling_order([p["player"] for p in picks], pos_df)

# `picks` stays in SELECTION order — the order the rules produced it. The
# bowling position is recorded on each pick and used only to order the slots
# below. Never re-sort the list itself: the reason belongs to the player, and
# re-sorting a list whose labels are read by position is what put the wrong
# rule against the wrong name.
for i, pick in enumerate(picks, start=1):
    pick["pick_no"] = i
    pick["bowl_pos"] = order.get(pick["player"], i)


# -------------------------------------------------------------------
# THE SELECTION, with a manual override on every slot
# -------------------------------------------------------------------

st.divider()
st.markdown("### 2. The selection")

if not _cur_games:
    st.info("No games played yet this season — the opening eight are picked "
            "on career average.")
elif everyone_played:
    st.info("Everyone on the list has played this season, so the remaining "
            "slots go to whoever has waited longest.")
else:
    waiting = sorted(everyone_played)
    st.info(
        f"Still to play this season: **{', '.join(waiting)}**. Until they "
        f"have, the remaining slots are filled on {PREVIOUS} average."
    )

st.caption("Change any slot below — an override is marked, and what the app "
           "would have chosen stays visible.")

# the selection itself, in the order the rules produced it
st.markdown("##### Who the rules picked")
for pick in picks:
    st.markdown(
        f'<div class="sel-why">• <b>{pick["player"]}</b> — {pick["rule"]} '
        f'({pick["why"]})</div>',
        unsafe_allow_html=True,
    )

chosen = []
# slots are laid out in bowling order, but every reason comes from the pick
# itself — never from the row it happens to sit on.
slot_picks = sorted(picks, key=lambda r: r.get("bowl_pos", 99))
for i, pick in enumerate(slot_picks):
    auto = pick["player"]
    pos_no = pick.get("bowl_pos", i + 1)

    col_pos, col_pick, col_why = st.columns([1, 3, 4])
    with col_pos:
        st.markdown(f"**{pos_no}**")
    with col_pick:
        options = [auto] + [p for p in available if p != auto]
        sel = st.selectbox(
            f"Position {pos_no}", options,
            index=0, key=f"pick_{pos_no}", label_visibility="collapsed",
        )
    with col_why:
        # the reason travels with the player, never with the row
        if sel != auto:
            st.markdown(
                f'<div class="sel-why"><b>{sel}</b> — manual override. '
                f'The app picked <b>{auto}</b> '
                f'({pick["rule"]}: {pick["why"]}).</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="sel-why">picked by <b>{pick["rule"]}</b> — '
                f'{pick["why"]}</div>',
                unsafe_allow_html=True,
            )
    chosen.append(sel)


# -------------------------------------------------------------------
# THE TEAM SHEET
# -------------------------------------------------------------------

st.divider()
st.markdown("### 3. The team sheet")

rows = []
for i, name in enumerate(chosen):
    pos_no = order.get(name, i + 1)
    p_rows = df[df["player"] == name]
    career = _career.get(name)
    prev = _prev.get(name)
    seen = last_seen.get(name, "never")
    s_last = last_scores.get(name)
    rows.append({
        "Position": i + 1,
        "Player": name,
        "Career avg": round(career, 1) if career is not None else "—",
        f"{PREVIOUS} avg": round(prev, 1) if prev is not None else "—",
        "Last game": int(s_last) if pd.notna(s_last) else "—",
        "Last played": seen,
    })

sheet = pd.DataFrame(rows)
st.dataframe(sheet, hide_index=True, use_container_width=True)

if len(chosen) != len(set(chosen)):
    st.error("The same player is picked twice — check the overrides above.")
elif len(chosen) < 8:
    st.warning(f"Only {len(chosen)} in the side — tick more available players.")
else:
    st.success("Eight players, no duplicates. Ready to bowl.")

# -------------------------------------------------------------------
# CARRY THE SELECTION TO THE MATCH BRIEFING
# -------------------------------------------------------------------
#
# Streamlit shares st.session_state across pages in the same app, so the
# chosen eight and their bowling order are written there for the briefing
# page to read. The PDF then prints this exact line-up and order.

st.divider()
st.markdown("### 4. Send to the match briefing")

if len(chosen) == 8 and len(set(chosen)) == 8:
    st.session_state["lineup"] = list(dict.fromkeys(chosen))
    st.session_state["bowl_order"] = {name: i + 1 for i, name in enumerate(chosen)}
    st.success(
        "The eight, in this bowling order, are now on the **Match Briefing** "
        "page — open it and the PDF will use them."
    )
    st.markdown(
        " · ".join(f"**{i+1}** {n}" for i, n in enumerate(chosen))
    )
else:
    st.warning(
        "A selection of exactly eight, with no duplicates, is needed before "
        "it can be sent to the briefing page."
    )

st.caption(
    f"Based on {len(df):,} player-games. Availability is not stored — "
    f"re-tick each week."
)
