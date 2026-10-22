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


def _txt(v):
    """Latin-1-safe text for the core fonts (fpdf2's built-in Helvetica)."""
    return str(v).encode("latin-1", "replace").decode("latin-1")


def build_briefing_pdf(opponent, alley, focus, h2h, at_alley, rows, generated):
    """One-page A4 briefing. Everything is measured in mm from the top-left."""
    pdf = FPDF(orientation="P", unit="mm", format="A4")
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
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*INK_RGB)
    pdf.cell(W - 6, 7, _txt("Warriors — Match Briefing"), ln=0)
    pdf.set_xy(L + 3, y + 9.4)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*GREY_RGB)
    pdf.cell(W - 6, 4, _txt(generated), ln=0)
    y += 20

    # ---- the fixture -------------------------------------------------
    pdf.set_xy(L, y)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*INK_RGB)
    pdf.cell(W, 6, _txt(f"vs {opponent}   ·   at {alley}"), ln=1)
    y += 9

    # ---- two record panels, side by side -----------------------------
    def panel(x, w, title, frame, our_avg, their_avg):
        pdf.set_xy(x, y)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(*INK_RGB)
        pdf.cell(w, 5, _txt(title), ln=0)

        pdf.set_xy(x, y + 5)
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(*GREY_RGB)
        if frame.empty:
            pdf.cell(w, 5, _txt("No games recorded."), ln=0)
            return
        played_n = len(frame)
        w_n = int((frame["result"] == "W").sum())
        l_n = int((frame["result"] == "L").sum())
        pct = round(100 * w_n / played_n) if played_n else 0
        pdf.cell(w, 5, _txt(f"Played {played_n}   Won {w_n}   Lost {l_n}   ({pct}%)"), ln=0)
        pdf.set_xy(x, y + 10)
        pdf.set_text_color(*INK_RGB)
        pdf.set_font("Helvetica", "", 8.5)
        pdf.cell(w, 5, _txt(f"Our average {our_avg}   ·   Theirs {their_avg}"), ln=0)

    panel(L, W / 2 - 4, f"Record vs {opponent}", h2h,
          round(h2h["teamtotal"].mean(), 1) if len(h2h) else "—",
          round(h2h["opptotal"].mean(), 1) if len(h2h) else "—")
    panel(L + W / 2 + 4, W / 2 - 4, f"Record at {alley}", at_alley,
          round(at_alley["teamtotal"].mean(), 1) if len(at_alley) else "—",
          round(at_alley["opptotal"].mean(), 1) if len(at_alley) else "—")
    y += 19

    # ---- recent meetings --------------------------------------------
    recent = h2h.sort_values("date", ascending=False).head(3) if len(h2h) else pd.DataFrame()
    if len(recent):
        pdf.set_xy(L, y)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(*INK_RGB)
        pdf.cell(W, 5, _txt("Recent meetings"), ln=1)
        y += 6
        for _, g in recent.iterrows():
            res = g["result"]
            pdf.set_xy(L, y)
            pdf.set_font("Helvetica", "B", 8.5)
            pdf.set_text_color(*(WIN_RGB if res == "W" else LOSS_RGB))
            pdf.cell(28, 5, _txt(f"{int(g['teamtotal'])}-{int(g['opptotal'])} ({res})"), ln=0)
            pdf.set_font("Helvetica", "", 8.5)
            pdf.set_text_color(*GREY_RGB)
            pdf.cell(W - 28, 5,
                     _txt(f"{g['season']}  ·  {g['venue']}  ·  {g['alley']}  ·  {g['date']:%d %b %Y}"),
                     ln=0)
            y += 5.4
        y += 3

    # ---- the line-up table -------------------------------------------
    pdf.set_xy(L, y)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(*INK_RGB)
    pdf.cell(W, 5, _txt("The line-up"), ln=1)
    y += 6

    head = ["Player", f"vs {opponent}: G", "Avg", "Best", "W-L",
            f"at {alley}: G", "Avg", "Best", "W-L"]
    widths = [30, 17, 14, 13, 14, 17, 14, 13, 14]
    scale = W / sum(widths)
    widths = [w * scale for w in widths]

    pdf.set_fill_color(*GREEN_RGB)
    pdf.set_text_color(*INK_RGB)
    pdf.set_font("Helvetica", "B", 7.6)
    pdf.set_xy(L, y)
    for w, htxt in zip(widths, head):
        pdf.cell(w, 6, _txt(htxt), border=0, align="C", fill=True, ln=0)
    y += 6.4

    pdf.set_font("Helvetica", "", 7.8)
    for i, r in enumerate(rows):
        if i % 2 == 0:
            pdf.set_fill_color(*CREAM_RGB)
            pdf.set_xy(L, y)
            pdf.cell(sum(widths), 5.4, "", border=0, fill=True, ln=0)
        vals = [
            r["Player"],
            r[f"vs {opponent} — games"], r[f"vs {opponent} — avg"],
            r[f"vs {opponent} — best"], r[f"vs {opponent} — W–L"],
            r[f"at {alley} — games"], r[f"at {alley} — avg"],
            r[f"at {alley} — best"], r[f"at {alley} — W–L"],
        ]
        pdf.set_xy(L, y)
        pdf.set_text_color(*INK_RGB)
        for j, (w, v) in enumerate(zip(widths, vals)):
            al = "L" if j == 0 else "C"
            if j == 0:
                pdf.set_font("Helvetica", "B", 7.8)
            else:
                pdf.set_font("Helvetica", "", 7.8)
            pdf.cell(w, 5.4, _txt(v), border=0, align=al, ln=0)
        y += 5.4

    # ---- suggested batting order ------------------------------------
    y += 6
    order = suggested_order(rows, opponent, alley)
    if order:
        pdf.set_xy(L, y)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(*INK_RGB)
        pdf.cell(W, 5, _txt("Suggested batting order"), ln=1)
        y += 6.5

        for i in range(0, len(order), 4):
            chunk = order[i:i + 4]
            pdf.set_xy(L, y)
            for pos, name, note in chunk:
                pdf.set_fill_color(*SALMON_RGB if note == "captain's choice" else CREAM_RGB)
                pdf.set_font("Helvetica", "B", 8)
                pdf.set_text_color(*INK_RGB)
                pdf.cell(9, 6, _txt(str(pos)), border=0, align="C", fill=True, ln=0)
                pdf.set_font("Helvetica", "", 8)
                pdf.cell(W / 4 - 9, 6, _txt(f" {name}"), border=0, fill=True, ln=0)
            y += 6.8

    # ---- footer ------------------------------------------------------
    pdf.set_xy(L, pdf.h - 14)
    pdf.set_font("Helvetica", "", 7.4)
    pdf.set_text_color(*GREY_RGB)
    pdf.cell(W, 4, _txt("Warriors Skittles — Match Briefing"), align="L", ln=0)

    return bytes(pdf.output())


def suggested_order(rows, opponent, alley):
    """Order by blended record (average discounted by sample size)."""
    scored = []
    for r in rows:
        for pos_idx, key in ((0, f"vs {opponent} — avg"), (1, f"at {alley} — avg")):
            avg = r[key]
            gkey = f"vs {opponent} — games" if pos_idx == 0 else f"at {alley} — games"
            g = r[gkey]
            if isinstance(avg, (int, float)) and isinstance(g, int) and g > 0:
                scored.append((r["Player"], avg * (1 - 1 / (g + 1)), g))
                break
    scored.sort(key=lambda t: -t[1])
    order = [(i + 1, name, "record") for i, (name, _, _) in enumerate(scored[:8])]
    placed = {n for _, n, _ in order}
    remaining = [r["Player"] for r in rows if r["Player"] not in placed]
    for name in remaining:
        if len(order) >= 8:
            break
        order.append((len(order) + 1, name, "captain's choice"))
    return order


st.divider()
pdf_bytes = build_briefing_pdf(
    opponent, alley, focus, h2h, at_alley, rows,
    generated=f"Generated {_dt.date.today():%d %B %Y}",
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
