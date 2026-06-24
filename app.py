#!/usr/bin/env python3
"""
CAMPS Membership Intelligence Dashboard
Clean rebuild - June 2026

Run locally:
    streamlit run app.py

Deploy to Streamlit Community Cloud:
    - Push to GitHub
    - Connect repo in Streamlit Cloud
    - Add password to secrets (see instructions at bottom)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(
    page_title="CAMPS Membership Intelligence",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# PASSWORD PROTECTION (for Streamlit Community Cloud)
# =============================================================================
def check_password():
    """Returns True if the user entered the correct password."""
    def password_entered():
        if st.session_state["password"] == st.secrets.get("dashboard_password", "changeme"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password in session
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input(
            "Enter dashboard password",
            type="password",
            on_change=password_entered,
            key="password"
        )
        st.caption("Contact CAMPS leadership for access.")
        return False

    if not st.session_state["password_correct"]:
        st.text_input(
            "Enter dashboard password",
            type="password",
            on_change=password_entered,
            key="password"
        )
        st.error("Password incorrect. Please try again.")
        return False

    return True


if not check_password():
    st.stop()

# =============================================================================
# DATA LOADING
# =============================================================================
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_data():
    """Load the clean master list."""
    try:
        df = pd.read_csv("data/members_master.csv")
        return df
    except FileNotFoundError:
        st.error("Could not find `data/members_master.csv`. Please ensure the clean master file is in the `data/` folder.")
        st.stop()


df = load_data()

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def get_renewal_month_order():
    """Return months in calendar order for sorting."""
    return ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
            "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]


def create_renewal_chart(df_filtered):
    """Create monthly renewal distribution chart."""
    renewal_counts = (
        df_filtered[df_filtered["Renewal"].notna()]
        .groupby("Renewal")
        .size()
        .reindex(get_renewal_month_order(), fill_value=0)
        .reset_index(name="Count")
    )
    fig = px.bar(
        renewal_counts,
        x="Renewal",
        y="Count",
        title="Members by Renewal Month",
        color="Count",
        color_continuous_scale="Blues",
        labels={"Renewal": "Month", "Count": "Number of Members"}
    )
    fig.update_layout(xaxis_tickangle=-45, height=400)
    return fig


def create_category_chart(df_filtered):
    """Create horizontal bar chart by Category_Group."""
    cat_counts = (
        df_filtered.groupby("Category_Group")
        .size()
        .sort_values(ascending=True)
        .reset_index(name="Count")
    )
    fig = px.bar(
        cat_counts,
        x="Count",
        y="Category_Group",
        orientation="h",
        title="Members by Category Group",
        color="Count",
        color_continuous_scale="Viridis",
        text="Count"
    )
    fig.update_layout(height=350, showlegend=False)
    fig.update_traces(textposition="outside")
    return fig


def get_region(city):
    """Simple region bucketing for Washington state based on city."""
    if pd.isna(city):
        return "Unknown / Missing"
    city = str(city).strip().lower()
    
    puget_sound = ["seattle", "kent", "bellevue", "tacoma", "renton", "auburn", 
                   "everett", "mukilteo", "lynnwood", "edmonds", "redmond", 
                   "woodinville", "tukwila", "fife", "sumner", "enumclaw",
                   "maple valley", "issaquah", "kirkland", "bothell", "sammamish"]
    north_sound = ["bellingham", "mount vernon", "burlington", "anacortes", 
                   "sedro woolley", "mountlake terrace", "marysville", "arlington"]
    south_sound = ["olympia", "tumwater", "gig harbor", "lacey", "puyallup",
                   "federal way", "des moines"]
    eastern_wa = ["spokane", "walla walla", "kennewick", "yakima", "pasco",
                  "richland", "pullman", "wenatchee", "moses lake"]
    
    if any(c in city for c in puget_sound):
        return "Puget Sound Metro"
    elif any(c in city for c in north_sound):
        return "North Sound"
    elif any(c in city for c in south_sound):
        return "South Sound"
    elif any(c in city for c in eastern_wa):
        return "Eastern Washington"
    elif "id" in city or ", id" in city:
        return "Out of State (ID)"
    else:
        return "Other / Smaller WA Cities"


def create_top_cities_chart(df_filtered, top_n=10):
    """Create bar chart of top cities."""
    city_counts = (
        df_filtered["City"]
        .value_counts()
        .head(top_n)
        .reset_index()
    )
    city_counts.columns = ["City", "Members"]
    
    fig = px.bar(
        city_counts,
        x="Members",
        y="City",
        orientation="h",
        title=f"Top {top_n} Cities by Membership",
        color="Members",
        color_continuous_scale="Blues",
        text="Members"
    )
    fig.update_layout(height=400, yaxis={'categoryorder':'total ascending'})
    fig.update_traces(textposition="outside")
    return fig


def create_region_chart(df_filtered):
    """Create region distribution chart."""
    df_filtered = df_filtered.copy()
    df_filtered["Region"] = df_filtered["City"].apply(get_region)
    
    region_counts = (
        df_filtered["Region"]
        .value_counts()
        .reset_index()
    )
    region_counts.columns = ["Region", "Members"]
    
    fig = px.pie(
        region_counts,
        values="Members",
        names="Region",
        title="Membership by Region",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    fig.update_layout(height=400)
    return fig, region_counts


# =============================================================================
# SIDEBAR FILTERS
# =============================================================================
st.sidebar.header("🔍 Filters")

# Search box
search_term = st.sidebar.text_input(
    "Search company name",
    placeholder="Type to filter...",
    help="Search is case-insensitive"
)

# Category Group filter
category_groups = ["All"] + sorted(df["Category_Group"].dropna().unique().tolist())
selected_group = st.sidebar.selectbox("Category Group", category_groups, index=0)

# Dynamic Subcategory filter (only shows relevant options)
if selected_group != "All":
    subcats = ["All"] + sorted(
        df[df["Category_Group"] == selected_group]["Subcategory"].dropna().unique().tolist()
    )
else:
    subcats = ["All"] + sorted(df["Subcategory"].dropna().unique().tolist())

selected_subcat = st.sidebar.selectbox("Subcategory", subcats, index=0)

# Health Trust filter
health_options = ["All", "Yes", "No", "Corporate Sponsor"]
selected_health = st.sidebar.selectbox("Health Trust", health_options, index=0)

# Status filter
status_options = ["All"] + sorted(df["Status"].dropna().unique().tolist())
selected_status = st.sidebar.selectbox("Status", status_options, index=0)

# Renewal month filter
renewal_months = ["All"] + get_renewal_month_order()
selected_renewal = st.sidebar.selectbox("Renewal Month", renewal_months, index=0)

# Data quality filter
show_incomplete_only = st.sidebar.checkbox(
    "Show only records with missing data",
    value=False,
    help="Filter to records missing Address, City/Zip, or Phone"
)

st.sidebar.divider()
st.sidebar.caption(f"Last updated: {datetime.now().strftime('%B %d, %Y')}")
st.sidebar.caption(f"Total records in master: {len(df):,}")

# =============================================================================
# APPLY FILTERS
# =============================================================================
df_filtered = df.copy()

if search_term:
    mask = df_filtered["Company Name"].str.contains(search_term, case=False, na=False)
    df_filtered = df_filtered[mask]

if selected_group != "All":
    df_filtered = df_filtered[df_filtered["Category_Group"] == selected_group]

if selected_subcat != "All":
    df_filtered = df_filtered[df_filtered["Subcategory"] == selected_subcat]

if selected_health != "All":
    df_filtered = df_filtered[df_filtered["Health Trust"] == selected_health]

if selected_status != "All":
    df_filtered = df_filtered[df_filtered["Status"] == selected_status]

if selected_renewal != "All":
    df_filtered = df_filtered[df_filtered["Renewal"] == selected_renewal]

if show_incomplete_only:
    incomplete_mask = (
        df_filtered["Missing_Address"] |
        df_filtered["Missing_City_Zip"] |
        df_filtered["Missing_Phone"]
    )
    df_filtered = df_filtered[incomplete_mask]

# =============================================================================
# MAIN DASHBOARD
# =============================================================================
st.title("CAMPS Membership Intelligence Dashboard")
st.caption("Clean data foundation • June 2026 rebuild")

# Top metrics row
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Total Members", f"{len(df_filtered):,}", 
              delta=f"{len(df_filtered) - len(df):+,}" if len(df_filtered) != len(df) else None)

with col2:
    health_yes = len(df_filtered[df_filtered["Health Trust"] == "Yes"])
    pct_health = (health_yes / len(df_filtered) * 100) if len(df_filtered) > 0 else 0
    st.metric("Health Trust", f"{health_yes:,}", f"{pct_health:.0f}% of filtered")

with col3:
    active = len(df_filtered[df_filtered["Status"] == "Active"])
    pct_active = (active / len(df_filtered) * 100) if len(df_filtered) > 0 else 0
    st.metric("Active", f"{active:,}", f"{pct_active:.0f}%")

with col4:
    with_website = df_filtered["Website"].notna().sum()
    pct_web = (with_website / len(df_filtered) * 100) if len(df_filtered) > 0 else 0
    st.metric("Have Website", f"{with_website:,}", f"{pct_web:.0f}%")

with col5:
    incomplete = (
        df_filtered["Missing_Address"] |
        df_filtered["Missing_City_Zip"] |
        df_filtered["Missing_Phone"]
    ).sum()
    pct_incomplete = (incomplete / len(df_filtered) * 100) if len(df_filtered) > 0 else 0
    st.metric("Need Data Update", f"{incomplete:,}", f"{pct_incomplete:.0f}%")

st.divider()

# =============================================================================
# TABBED VIEWS
# =============================================================================
tab_overview, tab_renewals, tab_quality, tab_category = st.tabs([
    "📊 Overview & Data",
    "📅 Renewals",
    "✅ Data Quality",
    "🏷️ Category Analysis"
])

# -----------------------------------------------------------------------------
# TAB 1: OVERVIEW + DATA TABLE (Enhanced Dashboard Feel)
# -----------------------------------------------------------------------------
with tab_overview:
    st.subheader("📊 Membership Overview Dashboard")
    st.caption(f"Showing **{len(df_filtered):,}** of **{len(df):,}** total members  |  Filters applied above")

    # --- Visual Dashboard Section ---
    st.markdown("### Key Visual Insights")

    # Row 1: Category + Top Cities
    col1, col2 = st.columns(2)
    
    with col1:
        if len(df_filtered) > 0:
            fig_cat = create_category_chart(df_filtered)
            st.plotly_chart(fig_cat, use_container_width=True, key="overview_cat")
        else:
            st.info("No data for current filters.")
    
    with col2:
        if len(df_filtered) > 0:
            fig_cities = create_top_cities_chart(df_filtered, top_n=10)
            st.plotly_chart(fig_cities, use_container_width=True, key="overview_cities")
        else:
            st.info("No data for current filters.")

    # Row 2: Region + Renewal
    col3, col4 = st.columns(2)
    
    with col3:
        if len(df_filtered) > 0:
            fig_region, region_df = create_region_chart(df_filtered)
            st.plotly_chart(fig_region, use_container_width=True, key="overview_region")
            
            # Small region table
            with st.expander("Region breakdown details"):
                st.dataframe(region_df, use_container_width=True, hide_index=True)
        else:
            st.info("No data for current filters.")
    
    with col4:
        if len(df_filtered) > 0:
            fig_renew = create_renewal_chart(df_filtered)
            st.plotly_chart(fig_renew, use_container_width=True, key="overview_renew")
        else:
            st.info("No data for current filters.")

    st.divider()

    # --- Interactive Data Table with Selection ---
    st.markdown("### Member Directory (Click rows for details)")

    # Column selection
    default_cols = [
        "Company Name", "Category_Group", "Subcategory", "Health Trust",
        "Renewal", "Status", "City", "Region", "Website"
    ]
    
    # Add Region column dynamically for display
    df_display = df_filtered.copy()
    df_display["Region"] = df_display["City"].apply(get_region)
    
    available_cols = df_display.columns.tolist()
    display_cols = st.multiselect(
        "Columns to show in table",
        options=available_cols,
        default=[c for c in default_cols if c in available_cols]
    )

    if not display_cols:
        display_cols = ["Company Name", "Category_Group", "Status", "City"]

    # Interactive dataframe with selection (Streamlit 1.35+)
    event = st.dataframe(
        df_display[display_cols],
        use_container_width=True,
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun",
        key="main_table",
        column_config={
            "Website": st.column_config.LinkColumn("Website", display_text="🔗"),
            "Company Name": st.column_config.TextColumn("Company Name", width="large"),
            "Region": st.column_config.TextColumn("Region", width="medium"),
        }
    )

    # Show selected company details
    selected_rows = event.selection.rows if event.selection else []
    
    if selected_rows:
        selected_idx = selected_rows[0]
        selected_company = df_display.iloc[selected_idx]
        
        with st.expander(f"📍 **{selected_company['Company Name']}** — Detailed View", expanded=True):
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.markdown("**Core Information**")
                st.write(f"**Category:** {selected_company.get('Category_Group', 'N/A')}")
                if pd.notna(selected_company.get('Subcategory')):
                    st.write(f"**Subcategory:** {selected_company['Subcategory']}")
                st.write(f"**Health Trust:** {selected_company.get('Health Trust', 'N/A')}")
                st.write(f"**Status:** {selected_company.get('Status', 'N/A')}")
                st.write(f"**Renewal:** {selected_company.get('Renewal', 'N/A')}")
            
            with col_b:
                st.markdown("**Location**")
                st.write(f"**City:** {selected_company.get('City', 'N/A')}")
                st.write(f"**Region:** {selected_company.get('Region', 'N/A')}")
                st.write(f"**Zip:** {selected_company.get('Zip', 'N/A')}")
                if pd.notna(selected_company.get('Address')):
                    st.write(f"**Address:** {selected_company['Address']}")
            
            if pd.notna(selected_company.get('Website')):
                st.markdown(f"**Website:** [{selected_company['Website']}]({selected_company['Website']})")
            
            if pd.notna(selected_company.get('Main Phone')):
                st.write(f"**Phone:** {selected_company['Main Phone']}")
            
            # Data quality notes
            if pd.notna(selected_company.get('Data_Quality_Notes')) and str(selected_company['Data_Quality_Notes']).strip():
                st.warning(f"**Data Notes:** {selected_company['Data_Quality_Notes']}")
            
            # Missing data flags
            missing_items = []
            if selected_company.get('Missing_Address'): missing_items.append("Address")
            if selected_company.get('Missing_City_Zip'): missing_items.append("City/Zip")
            if selected_company.get('Missing_Phone'): missing_items.append("Phone")
            if missing_items:
                st.info(f"**Missing data fields:** {', '.join(missing_items)}")

    # Download button
    csv = df_filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download filtered data as CSV",
        data=csv,
        file_name=f"camps_members_filtered_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True
    )

# -----------------------------------------------------------------------------
# TAB 2: RENEWALS (Enhanced)
# -----------------------------------------------------------------------------
with tab_renewals:
    st.subheader("📅 Renewal Intelligence")

    # Summary metrics
    total_with_renewal = df_filtered["Renewal"].notna().sum()
    col_m1, col_m2, col_m3 = st.columns(3)
    
    with col_m1:
        st.metric("Members with Renewal Data", f"{total_with_renewal:,}")
    with col_m2:
        pct_renewal = (total_with_renewal / len(df_filtered) * 100) if len(df_filtered) > 0 else 0
        st.metric("% with Known Renewal", f"{pct_renewal:.1f}%")
    with col_m3:
        # Approximate "next 3 months"
        renewal_order = get_renewal_month_order()
        current_month_idx = 5  # Approximate (June). Can be made dynamic later.
        upcoming_count = df_filtered[df_filtered["Renewal"].notna()]["Renewal"].apply(
            lambda x: renewal_order.index(x) if x in renewal_order else 99
        ).between(current_month_idx, current_month_idx + 2).sum()
        st.metric("Renewing in Next ~3 Months (est.)", f"{upcoming_count:,}")

    st.divider()

    col_left, col_right = st.columns([1.8, 1])

    with col_left:
        if len(df_filtered) > 0:
            fig_renewal = create_renewal_chart(df_filtered)
            st.plotly_chart(fig_renewal, use_container_width=True)
        else:
            st.info("No data to display with current filters.")

    with col_right:
        st.markdown("**Renewals by Category Group**")
        if len(df_filtered) > 0:
            cat_renewal = (
                df_filtered[df_filtered["Renewal"].notna()]
                .groupby(["Category_Group", "Renewal"])
                .size()
                .unstack(fill_value=0)
            )
            st.dataframe(cat_renewal, use_container_width=True)
        else:
            st.caption("No data.")

    st.markdown("**Upcoming Renewals (Next Several Months)**")
    upcoming = df_filtered[df_filtered["Renewal"].notna()].copy()
    if len(upcoming) > 0:
        renewal_order = get_renewal_month_order()
        upcoming["Renewal_Order"] = upcoming["Renewal"].apply(
            lambda x: renewal_order.index(x) if x in renewal_order else 99
        )
        upcoming = upcoming.sort_values("Renewal_Order")

        # Add Region for better context
        upcoming["Region"] = upcoming["City"].apply(get_region)

        st.dataframe(
            upcoming[["Company Name", "Renewal", "Category_Group", "Region", "City", "Health Trust"]].head(25),
            use_container_width=True,
            hide_index=True
        )
        
        # Download upcoming
        csv_upcoming = upcoming[["Company Name", "Renewal", "Category_Group", "Region", "City", "Health Trust"]].to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download upcoming renewals list",
            data=csv_upcoming,
            file_name="camps_upcoming_renewals.csv",
            mime="text/csv"
        )
    else:
        st.caption("No renewal data in current filter.")

    st.caption("Note: The 'Next 3 months' metric is approximate. We can add exact date-based forecasting later.")

# -----------------------------------------------------------------------------
# TAB 3: DATA QUALITY (Enhanced)
# -----------------------------------------------------------------------------
with tab_quality:
    st.subheader("✅ Data Quality Overview")

    # High-level completeness
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Completeness by Field**")
        completeness = {
            "Address": (~df_filtered["Missing_Address"]).mean() * 100,
            "City / Zip": (~df_filtered["Missing_City_Zip"]).mean() * 100,
            "Phone": (~df_filtered["Missing_Phone"]).mean() * 100,
            "Website": (df_filtered["Website"].notna()).mean() * 100,
            "Health Trust": (df_filtered["Health Trust"].notna()).mean() * 100,
        }
        comp_df = pd.DataFrame.from_dict(completeness, orient="index", columns=["% Complete"])
        comp_df = comp_df.round(1).sort_values("% Complete")
        st.dataframe(comp_df, use_container_width=True)

    with col2:
        st.markdown("**Overall Data Health**")
        total_records = len(df_filtered)
        missing_any = (
            df_filtered["Missing_Address"] |
            df_filtered["Missing_City_Zip"] |
            df_filtered["Missing_Phone"]
        ).sum()
        pct_complete = ((total_records - missing_any) / total_records * 100) if total_records > 0 else 0
        
        st.metric("Records with Complete Core Data", f"{total_records - missing_any:,}", 
                  f"{pct_complete:.1f}% complete")
        st.metric("Records Needing Some Update", f"{missing_any:,}")

    st.divider()

    st.markdown("**Records Needing Attention**")
    needs_work = df_filtered[
        df_filtered["Missing_Address"] |
        df_filtered["Missing_City_Zip"] |
        df_filtered["Missing_Phone"] |
        (df_filtered["Data_Quality_Notes"] != "")
    ].copy()

    if len(needs_work) > 0:
        # Add Region for context
        needs_work["Region"] = needs_work["City"].apply(get_region)
        
        # Allow filtering by missing type
        missing_filter = st.multiselect(
            "Filter by missing field type",
            ["Address", "City/Zip", "Phone", "Has Data Notes"],
            default=["Address", "City/Zip", "Phone", "Has Data Notes"]
        )
        
        filtered_needs = needs_work.copy()
        if "Address" in missing_filter:
            filtered_needs = filtered_needs[filtered_needs["Missing_Address"]]
        if "City/Zip" in missing_filter:
            filtered_needs = filtered_needs[filtered_needs["Missing_City_Zip"]]
        if "Phone" in missing_filter:
            filtered_needs = filtered_needs[filtered_needs["Missing_Phone"]]
        if "Has Data Notes" in missing_filter:
            filtered_needs = filtered_needs[filtered_needs["Data_Quality_Notes"] != ""]
        
        st.dataframe(
            filtered_needs[["Company Name", "Category_Group", "Region", "City", 
                           "Missing_Address", "Missing_City_Zip", "Missing_Phone", "Data_Quality_Notes"]],
            use_container_width=True,
            hide_index=True
        )
        st.caption(f"Showing {len(filtered_needs)} of {len(needs_work)} records that may need review.")
        
        # Download list for follow-up
        csv_needs = filtered_needs[["Company Name", "Category_Group", "Region", "City", 
                                   "Missing_Address", "Missing_City_Zip", "Missing_Phone", "Data_Quality_Notes"]].to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download cleanup list",
            data=csv_needs,
            file_name="camps_data_cleanup_list.csv",
            mime="text/csv"
        )
    else:
        st.success("All records look complete with current filters! Great data hygiene.")

    st.info("Tip: Use the sidebar checkbox 'Show only records with missing data' to focus the whole dashboard on cleanup work.")

# -----------------------------------------------------------------------------
# TAB 4: CATEGORY ANALYSIS
# -----------------------------------------------------------------------------
with tab_category:
    st.subheader("Category Breakdown")

    col_left, col_right = st.columns([1.5, 1])

    with col_left:
        if len(df_filtered) > 0:
            fig_cat = create_category_chart(df_filtered)
            st.plotly_chart(fig_cat, use_container_width=True)
        else:
            st.info("No data for current filters.")

    with col_right:
        st.markdown("**Breakdown by Category Group**")
        summary = (
            df_filtered.groupby("Category_Group")
            .agg(
                Members=("Company Name", "count"),
                Health_Trust_Yes=("Health Trust", lambda x: (x == "Yes").sum()),
                Active=("Status", lambda x: (x == "Active").sum()),
            )
            .reset_index()
            .sort_values("Members", ascending=False)
        )
        st.dataframe(summary, use_container_width=True, hide_index=True)

    # Subcategory detail when a group is selected
    if selected_group != "All" and selected_subcat == "All":
        st.markdown(f"**Subcategories within {selected_group}**")
        sub_summary = (
            df_filtered[df_filtered["Category_Group"] == selected_group]
            .groupby("Subcategory")
            .size()
            .reset_index(name="Members")
            .sort_values("Members", ascending=False)
        )
        st.dataframe(sub_summary, use_container_width=True, hide_index=True)

# =============================================================================
# FOOTER
# =============================================================================
st.divider()
st.caption(
    "CAMPS Membership Intelligence Dashboard • Built on clean master data (June 2026) • "
    "Data source: `data/members_master.csv` • "
    "Use the cleaning script regularly to maintain data quality."
)

# =============================================================================
# DEPLOYMENT INSTRUCTIONS (for reference)
# =============================================================================
"""
DEPLOYMENT TO STREAMLIT COMMUNITY CLOUD - QUICK GUIDE

1. Create a GitHub repo and push your project:
   - app.py
   - data/members_master.csv
   - requirements.txt (see below)
   - .streamlit/secrets.toml (see below)

2. Go to https://share.streamlit.io → New app → connect your repo

3. In Streamlit Cloud settings, add this secret:
   Key: dashboard_password
   Value: (choose a strong password)

4. Create `.streamlit/secrets.toml` locally (DO NOT commit real passwords):
   dashboard_password = "your-strong-password-here"

5. Create `requirements.txt` with:
   streamlit
   pandas
   plotly

The password gate will automatically use the secret when deployed.
"""

# End of app.py