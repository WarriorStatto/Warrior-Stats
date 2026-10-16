# Warriors Skittles — Stats App

A Streamlit app showing 7 seasons of Warriors skittles data — player stats,
alley and opponent breakdowns, records, ticks and fines.

## Files in this repo

| File | Purpose |
|---|---|
| `app.py` | the Streamlit app |
| `requirements.txt` | Python dependencies |
| `skittles-import.csv` | **required** — one row per player per game |
| `skittles-legs.csv` | optional — one row per individual leg |

All four must sit in the **same folder**. Streamlit Cloud is case-sensitive.

## Deploying

1. Push these files to a GitHub repo.
2. On [share.streamlit.io](https://share.streamlit.io), point a new app at
   `app.py`.
3. Streamlit installs `requirements.txt` and starts the app.

## The data

`skittles-import.csv` — 1,123 rows, 17 columns:

```
season,game,date,venue,alley,opponent,player,score,ticks,spares,fines,
sunshine,missed_single,flopper,spare9,team_total,opp_total
```

| Column | Meaning |
|---|---|
| `season` | e.g. `2025-2026` |
| `game` | 1–26 within that season |
| `date` | ISO format, `YYYY-MM-DD` |
| `venue` | `Home`, `Away` or `Cup` |
| `alley` | ground played at |
| `opponent` | opposition team |
| `player` | Warriors player |
| `score` | that player's total for the game |
| `ticks` | ticks scored |
| `spares` | spares (including spare 9s) |
| `fines` | fines in £ |
| `sunshine` | sunshines |
| `missed_single` | missed singles |
| `flopper` | floppers |
| `spare9` | spare 9s |
| `team_total` | Warriors' total that game |
| `opp_total` | opposition total that game |

`skittles-legs.csv` — 8,984 rows, 10 columns: one row per leg.

```
season,game,date,venue,alley,opponent,player,leg,leg_score,tick
```

## Notes on the data

**Venue storage changed between seasons.** From 2022-23 onward the venue sits
in column `AN` of each game block on the Games tab; in 2021-22 it is in `AO`.
The export script handles this per season.

**One fixture had no venue recorded** — 2023-24 game 19, Unsocialbles at
Feniton Social Club. It is an away game and has been set as such.

**Names were reconciled.** `Chris` and `Chris P` are the same player and have
been merged. Seven stand-in names (Chris H, Chris W, David V, Murray, Pete,
Callum, A. N. Other) were excluded from the player statistics.

**Opponent spellings were reconciled.** `Olive 8s` and `Olive's 8` are the
same club; both now read `Olive's 8`.

**Older seasons packed two venues into one cell** — e.g. `Feathers, Budleigh`.
The first named venue is kept, since each row is one game at one ground.

## Updating with a new game

The CSV is generated from the season Excel files. To add a game:

1. Enter it into the season workbook's `Games` tab in the usual block.
2. Regenerate `skittles-import.csv` and `skittles-legs.csv`.
3. Commit and push — Streamlit redeploys automatically.

## App structure

Seven tabs: Overview · Players · Head to Head · Alleys · Opponents · Records ·
Extras. Colours match the Excel Averages tab (green `C5E0B4`, blue `C6D9F1`,
cream `FDEADA`, salmon `FCD5B5`).
