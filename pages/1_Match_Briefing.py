"""
pages/1_Match_Briefing.py — pre-match briefing.

Pick the upcoming fixture (opponent + alley), tick off the players in the
line-up, and see how everyone has fared against that team and at that ground.

Streamlit picks this up automatically from the `pages/` folder next to
app.py. The sidebar in app.py does not apply here, so the page carries its
own controls.

There is also a printable A4 PDF of the briefing — one page, ready to hand
round or pin up. It needs `fpdf2` in requirements.txt.
"""

import os
import io
import datetime as _dt

import pandas as pd
import numpy as np
import streamlit as st

from fpdf import FPDF

# A TrueType face with a real pound sign. fpdf2's built-in Helvetica is
# ASCII-only, so "£" comes out as "?". If neither file is present the code
# falls back to Helvetica and money prints as "GBP".
# The reliable source is a font committed alongside the page: `fonts/` next to
# `pages/`, or at the repo root. System fonts are tried after that, since
# Streamlit's image does not always carry them.
FONT_DIRS = [
    "fonts",                     # pages/fonts/  (this file lives in pages/)
    "../fonts",                  # fonts/ at the repo root
    "data/fonts",
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype/liberation",
    "/usr/share/fonts/truetype/noto",
]
FONT_FAMILY = "Helvetica"
MONEY_FONT = "Helvetica"


def _register_font(pdf):
    """Try to register a font with a pound sign; return (family, is_custom)."""
    import os as _os
    candidates = [
        ("DejaVuSans", "DejaVuSans.ttf", "DejaVuSans-Bold.ttf"),
        ("DejaVu", "DejaVuSans.ttf", "DejaVuSans-Bold.ttf"),
        ("Liberation", "LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf"),
        ("NotoSans", "NotoSans-Regular.ttf", "NotoSans-Bold.ttf"),
    ]
    for family, regular, bold in candidates:
        for d in FONT_DIRS:
            rp = _os.path.join(d, regular)
            bp = _os.path.join(d, bold)
            if _os.path.exists(rp):
                try:
                    pdf.add_font(family, "", rp)
                    pdf.add_font(family, "B", bp if _os.path.exists(bp) else rp)
                    return family, True
                except Exception:
                    continue
    return "Helvetica", False

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


# ---- positions, for the bowling order --------------------------------
# This is the same file the Positions page reads, so the order printed on
# the briefing matches the suggested order shown there exactly.

POSITION_CANDIDATES = [
    "../skittles-positions.csv",
    "skittles-positions.csv",
    "data/skittles-positions.csv",
]


@st.cache_data
def load_positions(path):
    p = pd.read_csv(path)
    p.columns = (p.columns.astype(str).str.strip().str.lower()
                  .str.replace(" ", "", regex=False))
    for c in ["score", "position"]:
        if c in p.columns:
            p[c] = pd.to_numeric(p[c], errors="coerce")
    p = p[p["position"].between(1, 8)]
    return p


_pos_path = next((p for p in POSITION_CANDIDATES if os.path.exists(p)), None)
pos_df = load_positions(_pos_path) if _pos_path else None





# ---- the jackpot -------------------------------------------------------
# One row per game, carrying the pot recorded on the scoresheet. The figure
# on a briefing is THIS match's jackpot: the last recorded value plus the
# pound this game adds.

POT_CANDIDATES = [
    "../skittles-pot.csv",
    "skittles-pot.csv",
    "data/skittles-pot.csv",
]


@st.cache_data
def load_pot(path):
    pt = pd.read_csv(path)
    pt.columns = (pt.columns.astype(str).str.strip().str.lower()
                    .str.replace(" ", "", regex=False))
    if "pot" in pt.columns:
        pt["pot"] = pd.to_numeric(pt["pot"], errors="coerce")
    return pt


_pot_path = next((p for p in POT_CANDIDATES if os.path.exists(p)), None)
pot_df = load_pot(_pot_path) if _pot_path else None


def next_jackpot(pot_frame):
    """The jackpot on offer at this game: last recorded pot + £1, rounded."""
    if pot_frame is None or pot_frame.empty or "pot" not in pot_frame.columns:
        return None
    last = pot_frame["pot"].dropna()
    if last.empty:
        return None
    return int(round(float(last.iloc[-1]) + 1))


JACKPOT = next_jackpot(pot_df)

df = load_data(_path)

# the latest season in the data — that's the one whose average the briefing shows
CURRENT_SEASON = sorted(
    df.dropna(subset=["season"])["season"].astype(str).unique()
)[-1]

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

# A team we have never played won't be in the dropdown — type the name here.
new_team = st.text_input(
    "Playing a team not in the list? Type their name",
    value="",
    key="brief_newteam",
    placeholder="e.g. Sleepers",
)
if new_team.strip():
    opponent = new_team.strip()
    st.caption(
        f"Briefing for **{opponent}** — a first meeting, so no head-to-head "
        f"history. The alley and line-up records below still apply."
    )

if JACKPOT is not None:
    st.metric("Jackpot", f"£{JACKPOT}")

squad = sorted(df["player"].dropna().unique())

# A selection made on the Selection page arrives here, so the briefing — and
# the printable PDF — use the same eight, in the same bowling order.
FROM_SELECTION = st.session_state.get("lineup") or []
BOWL_ORDER = st.session_state.get("bowl_order") or {}

if FROM_SELECTION:
    st.markdown("##### The selected side")
    st.caption("Arrived from the Selection page. Change it below if you need to.")
    _order_bits = " · ".join(
        f"**{BOWL_ORDER.get(n, i + 1)}** {n}"
        for i, n in enumerate(FROM_SELECTION)
    )
    st.markdown(_order_bits)

lineup = st.multiselect(
    "Players in the line-up (leave empty for the whole squad)",
    squad,
    default=FROM_SELECTION,
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
    st.info(
        f"No previous meetings with {opponent} in the data — this is a "
        f"first meeting. The alley and line-up records below still apply."
    )


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

    # current-season average for this player (blank if they haven't played yet)
    _cs = df[(df["player"] == p) & (df["season"] == CURRENT_SEASON)]
    season_avg = round(_cs["score"].mean(), 1) if len(_cs) else "-"

    rows.append({
        "Player": p,
        "_season_avg": season_avg,
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

# -------------------------------------------------------------------
# PRINTABLE A4 PDF
# -------------------------------------------------------------------

GREEN_RGB  = (197, 224, 180)
CREAM_RGB  = (253, 234, 218)
SALMON_RGB = (252, 213, 181)
INK_RGB    = (34, 34, 34)
GREY_RGB   = (110, 110, 110)
WIN_RGB    = (26, 127, 55)
LOSS_RGB   = (180, 35, 24)


# When a TrueType face is registered these characters can be drawn as they
# are; with the built-in core fonts they have to be folded to ASCII or they
# arrive on the page as "?".
RICH_TEXT = False


def _txt(v):
    """Text safe for the font in use.

    With a TrueType font the characters are kept as written. With the built-in
    core fonts (ASCII only) en-dashes, curly quotes, ellipses and the pound
    sign are folded to plain equivalents, because fpdf2 renders anything else
    as a question mark.
    """
    s = str(v)
    for bad, good in (
        ("\u2013", "-"), ("\u2014", "-"), ("\u2012", "-"),   # dashes
        ("\u2018", "'"), ("\u2019", "'"), ("\u201c", '"'), ("\u201d", '"'),
        ("\u2026", "..."), ("\u00b7", "-"), ("\u00a0", " "),
    ):
        s = s.replace(bad, good)
    if RICH_TEXT:
        return s
    s = s.replace("\u00a3", "GBP")
    return s.encode("ascii", "replace").decode("ascii")


def _bowling_order(focus, pos_df, min_games=3):
    """Return {player: (position, captains_choice)} — the SAME order the
    Positions page produces, from the same data and the same rule.

    Score every player-position pair on a blend of average and sample size
    (blend = average x (1 - 1/(games+1))), then pick greedily: each round take
    the highest blend whose player and position are both still free. Positions
    left over are filled from the remaining players and flagged as the
    captain's choice.

    Nothing here looks at the opposition or the alley — the order is a
    property of the players, not of the fixture.
    """
    if pos_df is None or pos_df.empty:
        return {p: (i + 1, True) for i, p in enumerate(focus[:8])}

    # every player-position blend, exactly as the Positions page builds it
    scores = []
    for p in focus:
        sub = pos_df[pos_df["player"] == p]
        if sub.empty:
            continue
        for pos in range(1, 9):
            rs = sub[sub["position"] == pos]
            if len(rs) < min_games:
                continue
            n = len(rs)
            avg = rs["score"].mean()
            scores.append({"player": p, "position": pos, "avg": avg, "n": n,
                           "blend": avg * (1 - 1 / (n + 1))})

    if not scores:
        return {p: (i + 1, True) for i, p in enumerate(focus[:8])}

    scores_df = pd.DataFrame(scores)

    # greedy: each round take the best blend still available
    taken_players, taken_positions, order = set(), set(), []
    for _ in range(8):
        avail = scores_df[~scores_df["player"].isin(taken_players)
                          & ~scores_df["position"].isin(taken_positions)]
        if avail.empty:
            break
        top = avail.sort_values(["blend", "avg"], ascending=False).iloc[0]
        order.append(top)
        taken_players.add(top["player"])
        taken_positions.add(int(top["position"]))

    out = {r["player"]: (int(r["position"]), False) for r in order}

    # leftovers fill the empty slots
    leftovers = [p for p in focus if p not in taken_players]
    gaps = [i for i in range(1, 9) if i not in taken_positions]
    for pos, p in zip(gaps, leftovers):
        out[p] = (pos, True)

    return out


def build_briefing_pdf(opponent, alley, focus, h2h, at_alley, rows, generated,
                       pos_df=None, jackpot=None):
    """One-page A4 briefing. Everything is measured in mm from the top-left."""
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    global RICH_TEXT
    family, custom = _register_font(pdf)
    RICH_TEXT = custom
    base = family if custom else "Helvetica"
    money = family if custom else "Helvetica"
    pdf.set_auto_page_break(auto=False)
    pdf.set_margins(16, 14, 16)
    pdf.add_page()
    W = pdf.w - 32          # usable width
    L = 16                  # left edge
    y = 14

    # ---- header band -------------------------------------------------
    pdf.set_fill_color(*GREEN_RGB)
    pdf.rect(L, y, W, 15, style="F")
    pdf.set_xy(L + 3, y + 2.2)
    pdf.set_font(base, "B", 15)
    pdf.set_text_color(*INK_RGB)
    pdf.cell(W - 6, 7, _txt("Warriors — Match Briefing"), ln=0)
    pdf.set_xy(L + 3, y + 9.4)
    pdf.set_font(base, "", 9)
    pdf.set_text_color(*GREY_RGB)
    pdf.cell(W - 6, 4, _txt(generated), ln=0)
    y += 20

    # ---- the fixture -------------------------------------------------
    pdf.set_xy(L, y)
    pdf.set_font(base, "B", 15)
    pdf.set_text_color(*INK_RGB)
    if jackpot is None:
        pdf.cell(W, 8, _txt(f"vs {opponent}   -   at {alley}"), ln=1)
    else:
        # fixture on the left, jackpot on the right of the same band
        pdf.cell(W * 0.62, 8, _txt(f"vs {opponent}   -   at {alley}"), ln=0)
        pdf.set_font(money, "B", 13)
        pot_text = f"Jackpot  £{jackpot}"
        pdf.cell(W * 0.38, 8, _txt(pot_text), align="R", ln=1)
    y += 12

    # ---- two record panels, side by side -----------------------------
    def panel(x, w, title, frame, our_avg, their_avg):
        pdf.set_xy(x, y)
        pdf.set_font(base, "B", 12)
        pdf.set_text_color(*INK_RGB)
        pdf.cell(w, 6.4, _txt(title), ln=0)

        pdf.set_xy(x, y + 5)
        pdf.set_font(base, "", 11)
        pdf.set_text_color(*GREY_RGB)
        if frame.empty:
            pdf.cell(w, 6.4, _txt("No games recorded."), ln=0)
            return
        played_n = len(frame)
        w_n = int((frame["result"] == "W").sum())
        l_n = int((frame["result"] == "L").sum())
        pct = round(100 * w_n / played_n) if played_n else 0
        pdf.cell(w, 6.4, _txt(f"Played {played_n}   Won {w_n}   Lost {l_n}   ({pct}%)"), ln=0)
        pdf.set_xy(x, y + 10)
        pdf.set_text_color(*INK_RGB)
        pdf.set_font(base, "", 11)
        pdf.cell(w, 6.4, _txt(f"Our average {our_avg}   -   Theirs {their_avg}"), ln=0)

    panel(L, W / 2 - 4, f"Record vs {opponent}", h2h,
          round(h2h["teamtotal"].mean(), 1) if len(h2h) else "—",
          round(h2h["opptotal"].mean(), 1) if len(h2h) else "—")
    panel(L + W / 2 + 4, W / 2 - 4, f"Record at {alley}", at_alley,
          round(at_alley["teamtotal"].mean(), 1) if len(at_alley) else "—",
          round(at_alley["opptotal"].mean(), 1) if len(at_alley) else "—")
    y += 23

    # ---- recent meetings --------------------------------------------
    recent = h2h.sort_values("date", ascending=False).head(3) if len(h2h) else pd.DataFrame()
    if len(recent):
        pdf.set_xy(L, y)
        pdf.set_font(base, "B", 12)
        pdf.set_text_color(*INK_RGB)
        pdf.cell(W, 6.4, _txt("Recent meetings"), ln=1)
        y += 8
        for _, g in recent.iterrows():
            res = g["result"]
            pdf.set_xy(L, y)
            pdf.set_font(base, "B", 11)
            pdf.set_text_color(*(WIN_RGB if res == "W" else LOSS_RGB))
            pdf.cell(30, 6.4, _txt(f"{int(g['teamtotal'])}-{int(g['opptotal'])} ({res})"), ln=0)
            pdf.set_font(base, "", 10)
            pdf.set_text_color(*GREY_RGB)
            pdf.cell(W - 30, 6.4,
                     _txt(f"{g['season']}  ·  {g['venue']}  ·  {g['alley']}  ·  {g['date']:%d %b %Y}"),
                     ln=0)
            y += 7
        y += 3

    # ---- the line-up, in bowling order -------------------------------
    pdf.set_xy(L, y)
    pdf.set_font(base, "B", 14)
    pdf.set_text_color(*INK_RGB)
    pdf.cell(W, 7, _txt("The line-up (bowling order)"), ln=1)
    y += 10

    # Columns: #  |  Player  |  Current Season Av  |  vs <team> G/Avg/Best  |  at <alley> G/Avg/Best
    widths = [9, 34, 21, 15, 17, 17, 15, 17, 17]
    scale = W / sum(widths)
    widths = [w * scale for w in widths]

    GREEN_FILL = (197, 224, 180)
    SUB_GREY   = (110, 110, 110)

    # --- row 1: group labels spanning their columns -------------------
    pdf.set_fill_color(*GREEN_FILL)
    pdf.set_text_color(*INK_RGB)
    pdf.set_font(base, "B", 12)
    pdf.set_xy(L, y)
    pdf.cell(widths[0] + widths[1] + widths[2], 8.6, "", border=0, fill=True, ln=0)
    pdf.cell(sum(widths[3:6]), 8.6, _txt(f"vs {opponent}"), border=0, align="C", fill=True, ln=0)
    pdf.cell(sum(widths[6:9]), 8.6, _txt(f"at {alley}"), border=0, align="C", fill=True, ln=0)
    y += 8.6

    # --- row 2: the column headings -----------------------------------
    pdf.set_xy(L, y)
    pdf.set_font(base, "B", 12)
    heads = ["#", "Player", "Season Avg", "G", "Avg", "Best", "G", "Avg", "Best"]
    for j, (w, htxt) in enumerate(zip(widths, heads)):
        al = "L" if j == 1 else "C"
        pdf.cell(w, 8.6, _txt(htxt), border=0, align=al, fill=True, ln=0)
    y += 9.4

    order = _bowling_order([r["Player"] for r in rows], pos_df)
    ordered = sorted(rows, key=lambda r: order.get(r["Player"], (99, True))[0])

    for i, r in enumerate(ordered):
        pos_no, captains = order.get(r["Player"], (i + 1, True))
        if i % 2 == 0:
            pdf.set_fill_color(*CREAM_RGB)
            pdf.set_xy(L, y)
            pdf.cell(sum(widths), 13.2, "", border=0, fill=True, ln=0)
        vals = [
            f"{pos_no}*" if captains else str(pos_no),
            r["Player"],
            r.get("_season_avg", "-"),
            r[f"vs {opponent} — games"], r[f"vs {opponent} — avg"], r[f"vs {opponent} — best"],
            r[f"at {alley} — games"], r[f"at {alley} — avg"], r[f"at {alley} — best"],
        ]
        pdf.set_xy(L, y)
        pdf.set_text_color(*INK_RGB)
        for j, (w, v) in enumerate(zip(widths, vals)):
            if j == 1:
                pdf.set_font(base, "B", 13)
                al = "L"
            else:
                pdf.set_font(base, "", 13)
                al = "C"
            pdf.cell(w, 13.2, _txt(v), border=0, align=al, ln=0)
        y += 13.2

    # ---- footer ------------------------------------------------------
    pdf.set_xy(L, pdf.h - 12)
    pdf.set_font(base, "", 8.5)
    pdf.set_text_color(*GREY_RGB)
    pdf.cell(W, 4, _txt("Warriors Skittles - Match Briefing"), align="L", ln=0)
    if any(r.get("_captains") for r in rows):
        pdf.set_xy(L, pdf.h - 8)
        pdf.set_font(base, "", 8)
        pdf.cell(W, 4, _txt("Positions marked * are captain's choice (no qualifying record)."),
                 align="L", ln=0)

    return bytes(pdf.output())


st.divider()
pdf_bytes = build_briefing_pdf(
    opponent, alley, focus, h2h, at_alley, rows,
    generated=f"Generated {_dt.date.today():%d %B %Y}",
    pos_df=pos_df,
    jackpot=JACKPOT,
)
st.download_button(
    "🖨️ Download printable briefing (A4 PDF)",
    data=pdf_bytes,
    file_name=f"briefing-{opponent.replace(' ', '-').lower()}.pdf",
    mime="application/pdf",
)

_last = df["date"].max()
if pd.notna(_last):
    st.caption(f"Based on {len(df):,} player-games up to **{_last:%d %B %Y}**")
