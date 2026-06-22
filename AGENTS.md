# CAMPS Member Dashboard — Agent Guide

## Purpose

Local Streamlit dashboard for analyzing CAMPS (Center for Advanced Manufacturing Puget Sound) membership data: KPIs, distribution charts, searchable member directory, and auto-generated insights.

## Quick start

```bash
cd camps-member-dashboard
pip install -r requirements.txt
python scripts/build_members.py
```

Set the dashboard password in `.streamlit/secrets.toml` (key: `password`), then:

```bash
streamlit run app.py
```

Login state persists for the browser session via `st.session_state.authenticated`.

Use the **Refresh Data** button in the header to clear `get_members()` cache and reload from disk without restarting the app. Filter widgets reset on refresh via `data_refresh_token`.

Open the URL shown in the terminal (default `http://localhost:8501`).

## Data files

Load priority in `src/data_loader.py`:

1. `data/members.csv` — cleaned, one row per organization (preferred)
2. `data/members.xlsx` — same schema, first sheet
3. `data/Master Member List - 2026 Master List.csv` — raw roster fallback

Refresh cleaned CSV after master list updates:

```bash
python scripts/build_members.py
```

## Raw data quirks

The master CSV is **not** a flat table:

- **Section headers** repeat per category (`MANUFACTURERS`, `JOINT ACCESS - CANNABIS`, etc.)
- **Primary rows** are organizations; **`Additional`** rows are secondary contacts
- **DBA continuation rows** may appear under a parent org with shifted columns
- **Admin notes** occasionally prefix a row (`Waiting for App.`, `add Laura to database`)
- Flags embedded in names: `(OPTED OUT)`, `(BOUNCED)`, `** Renews June **`
- Renewal formats vary: month names, `MM/DD/YYYY`, or blank

The parser in `src/data_loader.py` handles these patterns. Do not assume fixed column positions without testing.

## Standard schema

| Column | Notes |
|--------|-------|
| `member_id` | MD5 hash of category + name |
| `member_name` | Cleaned organization name |
| `category` | Section from master list |
| `industry` | Normalized label (e.g. Cannabis, Wine) |
| `membership_type` | Health Trust, Corporate Sponsor, IN-KIND, Unknown |
| `website` | Normalized with `https://` |
| `renewal` / `renewal_month` | Raw + parsed month where possible |
| `county` / `region` | Derived from city + WA ZIP prefix |
| `size_band` | **Contact-count proxy** (Solo/Small/Mid/Large) — not headcount |
| `contact_count` | Number of `Additional` rows |
| `opted_out` / `bounced` | Parsed from name/contact markers |

## Project layout

```
camps-member-dashboard/
  app.py                 # Streamlit UI
  requirements.txt
  AGENTS.md
  .streamlit/config.toml
  data/
    members.csv          # generated
    Master Member List - 2026 Master List.csv
  scripts/
    build_members.py     # ETL to members.csv
  src/
    constants.py         # sections, ZIP/county maps
    data_loader.py       # load + clean + derive
    insights.py          # rule-based insight text
```

## Chart selection (session state)

Interactive chart clicks drive the right-side **Selected Members** panel:

| Key | Purpose |
|-----|---------|
| `selected_member_ids` | Member IDs from the latest chart segment click |
| `selection_label` | Human-readable label (e.g. `Category: MANUFACTURERS`) |
| `expanded_member_id` | Which member detail card is open in the right panel |

- Charts use `st.plotly_chart(..., on_select="rerun", selection_mode="points")` with `customdata` for reliable segment parsing.
- Sidebar filters define the base dataset; chart clicks select a subset within that base.
- KPIs switch to the selected subset when a chart selection is active.
- Register new charts in `CHART_SPECS` and pass `customdata` columns in `plot_chart()`.

## Extension points

- **New charts**: add functions in `app.py` → `render_overview()` and register in `CHART_SPECS`
- **New filters**: sidebar in `app.py` + `apply_filters()`
- **Better geography**: expand `CITY_TO_COUNTY` / `ZIP3_TO_COUNTY` in `src/constants.py`
- **Real size data**: add an `employee_count` column to `members.csv`; update `_derive_size_band()`
- **New insights**: add rules in `src/insights.py`

## Do not break

- `@st.cache_data` on `get_members()` — clear cache when schema changes
- `STANDARD_COLUMNS` order — downstream CSV export depends on it
- `load_members()` return signature: `(DataFrame, path, stats)`
- Preprocessed detection: files with `member_name` + `category` skip heavy parsing

## Verification

```bash
python scripts/build_members.py   # expect ~280+ members
python -c "from src.data_loader import load_members; df,_,s=load_members(); print(len(df), s)"
```

Search the directory tab for `Microsoft`, `Steeler`, or `Boeing` to sanity-check parsing.