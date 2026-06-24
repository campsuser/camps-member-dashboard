# CAMPS Membership Intelligence Dashboard

A clean, visual, and interactive dashboard for analyzing CAMPS membership data. Built on a cleaned master list with strong location intelligence, renewal tracking, and data quality visibility.

**Live Demo:** Deployed on Streamlit Community Cloud (link to be added after deployment)

---

## Features

- **Visual Dashboard Overview** — Multiple charts including Category breakdown, Top Cities, Region distribution, and Renewal timing
- **Location Intelligence** — Membership by Region (Puget Sound Metro, North Sound, Eastern Washington, etc.) and Top Cities
- **Interactive Data Table** — Click any row to see detailed company information including location details
- **Renewal Intelligence** — Summary metrics, monthly distribution, Category breakdown, and downloadable upcoming renewals list
- **Data Quality Tracking** — Clear visibility into incomplete records with filterable cleanup lists and download options
- **Powerful Filtering** — By Category Group, Subcategory, Health Trust, Status, Renewal Month, and search
- **Export Capabilities** — Download filtered data, upcoming renewals, or data cleanup lists

---

## Project Structure

```
camps-member-dashboard/
├── app.py                          # Main Streamlit dashboard
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── PROJECT_HANDOFF.md              # Technical handoff / architecture notes
├── data/
│   └── members_master.csv          # Clean master data (single source of truth)
├── scripts/
│   └── clean_master_list.py        # Reusable data cleaning script
└── .streamlit/
    └── secrets.toml                # Local secrets only (never commit real passwords)
```

---

## Local Setup

### 1. Clone or Download the Project

```bash
git clone <your-repo-url>
cd camps-member-dashboard
```

### 2. Create a Virtual Environment (Recommended)

```powershell
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Add Your Clean Data

Place your cleaned master file here:

```
data/members_master.csv
```

> **Note:** The dashboard expects the clean 17-column structure produced by `scripts/clean_master_list.py`.

### 5. Run the Dashboard Locally

```bash
python -m streamlit run app.py
```

The dashboard will open in your browser at `http://localhost:8501`.

---

## Password Protection

The dashboard is protected by a password.

### For Local Development

Create the folder and file:

```
.streamlit/secrets.toml
```

Add the following:

```toml
dashboard_password = "your-strong-password-here"
```

### For Streamlit Community Cloud Deployment

1. Go to your app settings in Streamlit Cloud
2. Navigate to **Secrets**
3. Add the following:

```toml
dashboard_password = "your-strong-password-here"
```

> **Important:** Never commit real passwords to GitHub. The `.streamlit/secrets.toml` file should be in your `.gitignore`.

---

## Data Maintenance Workflow

### Monthly Update Process (Recommended)

1. Update your source data as needed.
2. Run the cleaning script:

```bash
python scripts/clean_master_list.py \
    --input data/raw/your-new-export.csv \
    --output data/members_master.csv \
    --mode legacy
```

Or re-validate the existing clean file:

```bash
python scripts/clean_master_list.py \
    --input data/members_master.csv \
    --output data/members_master.csv \
    --mode clean
```

3. Commit and push the updated `data/members_master.csv`.
4. The live dashboard will automatically reflect the new data (or redeploy if needed).

---

## Deployment to Streamlit Community Cloud

### Step-by-Step

1. **Push your project to GitHub**
   - Make sure the following are committed:
     - `app.py`
     - `requirements.txt`
     - `data/members_master.csv`
     - `README.md`
     - `PROJECT_HANDOFF.md`
   - **Do NOT commit** real passwords or `.streamlit/secrets.toml`

2. **Deploy on Streamlit Cloud**
   - Go to [https://share.streamlit.io](https://share.streamlit.io)
   - Click **New app**
   - Connect your GitHub repository
   - Select the main branch and `app.py` as the entrypoint
   - Click **Deploy**

3. **Add the Password Secret**
   - After deployment, go to your app → **Settings** → **Secrets**
   - Add:

   ```toml
   dashboard_password = "your-strong-password-here"
   ```

4. **(Optional) Set a Custom Subdomain**
   - In Settings → you can choose a nicer URL like `camps-membership.streamlit.app`

---

## Requirements

```
streamlit>=1.35
pandas>=2.2
plotly>=5.22
numpy>=1.26
```

---

## Future Enhancements (Ideas)

- Exact date-based renewal forecasting
- Email alerts for upcoming renewals
- Ability to compare multiple selected companies
- Deeper geographic analysis (by ZIP or county)
- Role-based views (different access levels)
- Automated monthly data quality reports

---

## Support & Maintenance

- **Data Cleaning Script**: See `scripts/clean_master_list.py` and `PROJECT_HANDOFF.md`
- **Dashboard Code**: All logic is in `app.py` (well-commented)
- **Questions?** Contact the CAMPS team or the dashboard maintainer.

---

**Built with ❤️ for CAMPS** — Center for Advanced Manufacturing Puget Sound

*Last updated: June 2026*