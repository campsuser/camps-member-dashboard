# CAMPS Member Dashboard - Project Handoff

**Date:** June 24, 2026  
**Status:** Fresh start – clean master data foundation established. Moving from legacy messy source to reliable, maintainable structure.

---

## Project Goal

Build and maintain a reliable, interactive **CAMPS Membership Intelligence Dashboard** using:
- Streamlit (deployed on Streamlit Community Cloud or self-hosted)
- Python transformation / cleaning scripts
- GitHub for version control and live updates

The dashboard helps CAMPS leadership analyze membership by category, renewal timing, geographic distribution, health trust participation, data quality, and other strategic intelligence.

---

## Current Architecture (as of June 24, 2026)

### Data Flow (Simplified & Clean)
```
CAMPS_Company_Master_List_Cleaned_2026_June.csv   ← Single source of truth (cleaned)
          ↓
scripts/transform_or_validate.py (optional lightweight step)
          ↓
data/members_master.csv   ← Dashboard reads this (or directly from cleaned master)
          ↓
Streamlit App (app.py / pages/)
```

### Key Files

| File                                              | Purpose                                              | Notes |
|---------------------------------------------------|------------------------------------------------------|-------|
| `CAMPS_Company_Master_List_Cleaned_2026_June.csv` | Clean, documented master list (281 companies)       | Created June 24, 2026 – new foundation |
| `scripts/clean_master_list.py`                    | Reusable cleaning script for future updates         | Recommended to create/maintain |
| `data/members_master.csv`                         | Working copy consumed by dashboard                  | Can be symlink or direct copy of cleaned master |
| `app.py` + `pages/`                               | Main Streamlit dashboard                             | To be rebuilt cleanly |
| `PROJECT_HANDOFF.md`                              | This document – single source of project knowledge  | Update monthly or on major changes |

---

## Target Clean Master List Structure (Achieved + Enhanced)

The cleaned master now follows (and slightly extends) the desired 10-column structure:

**Core Columns (aligned to target):**
1. `Company Name`
2. `Category` (original)
3. `Category_Group` (new – top-level grouping: MANUFACTURERS, JOINT ACCESS, ASSOCIATES, AFFILIATES, SUPPLY CHAIN)
4. `Subcategory` (new – e.g., Cannabis, Wine Association, Brewing, PNAA, NIMA)
5. `Health Trust` (standardized: Yes / No / Corporate Sponsor)
6. `Sponsorship_Type` (new – captures IN-KIND and future sponsorship types)
7. `Renewal` (standardized month or blank)
8. `Website` (normalized where possible)
9. `Address`
10. `City`
11. `Zip`
12. `Main Phone`
13. `Status` (Active / Opted Out / Bounced)

**Data Quality & Intelligence Columns (added for maintainability):**
- `Missing_Address`
- `Missing_City_Zip`
- `Missing_Phone`
- `Data_Quality_Notes` (documents all corrections and flags needing manual review)

This structure supports much richer filtering, data quality dashboards, and renewal forecasting than the legacy version.

---

## Data Quality Improvements Made (June 24, 2026 Cleaning Pass)

A systematic cleaning pass was performed on the original `CAMPS_Company_Master_Data_Source_2026_June.csv`. Key fixes:

- **Critical corruption fixed**: Removed junk values in Website column (e.g., "er", polluted address text, copy-paste errors from adjacent rows).
- **Embedded metadata cleaned**: Stripped "** Renews..." notes from 3 company names (actual renewal data preserved in Renewal column).
- **IN-KIND sponsorship** moved from Renewal column → new `Sponsorship_Type` column (9 AFFILIATE records).
- **Zip code issues** corrected or flagged (trailing dashes removed; short/incomplete zips like "9807" flagged for manual review).
- **Name hygiene**: Trimmed trailing punctuation and spaces from many company names.
- **Standardization**:
  - Health Trust values normalized
  - Websites normalized to https:// where they looked like valid domains
  - Renewal months upper-cased and validated
  - Added hierarchical `Category_Group` + `Subcategory` for better dashboard UX
- **Data quality flags** added so the team can easily see and prioritize incomplete records.
- **Full audit trail** captured in `Data_Quality_Notes` column (84 records / 29.9% carry documentation of changes).

**Result**: The cleaned file is now the reliable single source of truth. Future updates should be made to a clean master list and then validated through the cleaning script rather than editing the legacy messy format.

---

## Current Monthly Workflow (Recommended – June 2026 onward)

1. Maintain the **clean master list** (add new members, update renewals, correct data in the cleaned CSV structure).
2. Run the cleaning/validation script (if any new source data arrives in legacy format):
   ```bash
   python scripts/clean_master_list.py --input new_export.csv --output data/members_master.csv
   ```
3. Commit + push the updated `data/members_master.csv`.
4. Dashboard automatically reflects changes (or trigger redeploy).

This is dramatically simpler than the previous legacy parser + transformation pipeline.

---

## What’s Working Well

- Clean master list with documented data quality and hierarchical categories is now in place.
- `Data_Quality_Notes` + missing-data flags give immediate visibility into record completeness.
- Category grouping (`Category_Group` / `Subcategory`) enables much better filtering and roll-up reporting in the dashboard.
- No duplicate company names.
- Status values are clean and actionable.

---

## Open Items / Priorities

| Priority | Item | Notes / Owner |
|---------|------|---------------|
| High | Create reusable `scripts/clean_master_list.py` | Should handle both clean-to-clean and legacy-to-clean paths |
| High | Rebuild Streamlit dashboard from clean data | Simpler architecture, leverage new columns (Category_Group, Sponsorship_Type, data quality flags) |
| Medium | Decide on contact/email strategy | Current master is company-level only. Plan join with HubSpot / membership system export? |
| Medium | Add data quality dashboard page | Show % complete, records needing review, trends over time |
| Low | Geographic visualization (map) | City/Zip data is now clean enough to support this |
| Low | Renewal forecasting / alerts | Use Renewal month + historical patterns |

---

## Key Decisions Made (June 2026 Reset)

- We are **moving away** from heavy reliance on complex legacy parsing logic.
- We are standardizing on a **clean, documented master list** with explicit data quality tracking.
- Short-term: Use the June 24, 2026 cleaned file as the foundation.
- Long-term: The cleaning script + clean master list becomes the maintained source. The dashboard reads from the clean structure directly.
- `Data_Quality_Notes` and missing-data flags are first-class citizens — they help the team maintain data hygiene instead of hiding problems.

---

## Useful Commands

```bash
# Validate / clean new data against current standards
python scripts/clean_master_list.py --input incoming.csv --output data/members_master.csv

# Run dashboard locally
python -m streamlit run app.py

# Quick data quality check (example)
python -c "
import pandas as pd
df = pd.read_csv('data/members_master.csv')
print(df['Data_Quality_Notes'].value_counts().head(10))
print('Records with missing address:', df['Missing_Address'].sum())
"
```

---

## Next Suggested Actions

1. **Copy** `CAMPS_Company_Master_List_Cleaned_2026_June.csv` into your project as `data/members_master.csv`.
2. **Create** `scripts/clean_master_list.py` (I can generate a starter version).
3. **Update / expand** this `PROJECT_HANDOFF.md` as decisions are made.
4. **Rebuild the dashboard** — start with a clean `app.py` that leverages the new columns (Category_Group filtering, data quality overview, renewal calendar, etc.).
5. Decide on contact enrichment approach (separate contacts file + join, or add columns to master).

---

**Last Updated:** June 24, 2026  
**Cleaned Master:** `CAMPS_Company_Master_List_Cleaned_2026_June.csv` (281 companies, documented fixes)

---

*This handoff is designed so anyone (including future Grok sessions or new team members) can understand exactly where the project stands and how to maintain momentum.*