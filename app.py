"""CAMPS Member Analysis Dashboard."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from src.constants import MONTH_NAMES
from src.data_loader import load_members
from src.insights import Insight, generate_insights

st.set_page_config(
    page_title="CAMPS Member Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
    .kpi-card {
        background: linear-gradient(135deg, #f8fafc 0%, #eef2f7 100%);
        border: 1px solid #d0d7e2;
        border-left: 4px solid #1a4d7c;
        border-radius: 8px;
        padding: 1rem 1.25rem;
        min-height: 96px;
    }
    .kpi-label {
        color: #5a6b7d;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.25rem;
    }
    .kpi-value {
        color: #1a2e44;
        font-size: 1.75rem;
        font-weight: 700;
        line-height: 1.2;
    }
    .kpi-sub {
        color: #6b7c8f;
        font-size: 0.85rem;
        margin-top: 0.25rem;
    }
    .block-container { padding-top: 1.5rem; }
    div[data-testid="stSidebar"] { background-color: #f4f7fb; }
    .selection-banner {
        background: #e8f1fa;
        border: 1px solid #b8cfe6;
        border-radius: 6px;
        padding: 0.5rem 0.75rem;
        font-size: 0.9rem;
        color: #1a4d7c;
        margin-bottom: 0.75rem;
    }
    .selected-panel {
        background: #f8fafc;
        border: 1px solid #d0d7e2;
        border-radius: 10px;
        padding: 1rem;
        max-height: calc(100vh - 6rem);
        overflow-y: auto;
    }
    .member-card {
        background: #ffffff;
        border: 1px solid #d8e0ea;
        border-radius: 8px;
        padding: 0.75rem;
        margin: 0.5rem 0 0.75rem 0;
        font-size: 0.85rem;
    }
    .member-card dt {
        color: #5a6b7d;
        font-weight: 600;
        margin-top: 0.35rem;
    }
    .member-card dd {
        margin: 0.1rem 0 0 0;
        color: #1a2e44;
    }
    .login-card {
        background: #ffffff;
        border: 1px solid #d0d7e2;
        border-radius: 12px;
        padding: 2rem 2rem 1.5rem 2rem;
        box-shadow: 0 4px 18px rgba(26, 46, 68, 0.08);
        margin-top: 4rem;
    }
    .login-title {
        color: #1a2e44;
        font-size: 1.5rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
    }
    .login-subtitle {
        color: #5a6b7d;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }
</style>
"""

CHART_SPECS: dict[str, dict[str, Any]] = {
    "chart_category": {"dimension": "category", "label": "Category"},
    "chart_industry": {"dimension": "industry", "label": "Industry"},
    "chart_region": {"dimension": "region", "label": "Region"},
    "chart_county": {"dimension": "county", "label": "County"},
    "chart_size": {"dimension": "size_band", "label": "Size band"},
    "chart_renewal": {"dimension": "renewal_month", "label": "Renewal month"},
    "chart_membership": {
        "dimension": "category",
        "sub_dimension": "membership_type",
        "label": "Category + membership",
    },
}

EXPORT_COLUMNS = {
    "member_name": "Company Name",
    "primary_contact": "Contact Name",
    "website": "Website",
    "email": "Email",
    "phone": "Phone",
    "job_title": "Job Title",
    "category": "Category",
    "industry": "Industry",
    "membership_type": "Membership Type",
    "city": "City",
    "county": "County",
    "region": "Region",
    "address": "Address",
    "zip": "ZIP",
    "renewal": "Renewal",
    "contact_count": "Additional Contacts",
}


def init_session_state() -> None:
    defaults = {
        "authenticated": False,
        "selected_member_ids": [],
        "selection_label": "",
        "expanded_member_id": None,
        "login_error": "",
        "data_refresh_token": 0,
        "show_refresh_success": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_app_password() -> str | None:
    try:
        return str(st.secrets["password"])
    except (KeyError, TypeError, FileNotFoundError):
        return None


def render_login_screen() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    _, center, _ = st.columns([1, 1.1, 1])
    with center:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="login-title">CAMPS Member Dashboard</div>
            <div class="login-subtitle">Enter your password to access membership analytics.</div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("login_form", clear_on_submit=False):
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submitted = st.form_submit_button("Login", use_container_width=True, type="primary")

        if submitted:
            expected = get_app_password()
            if expected is None:
                st.session_state.login_error = (
                    "Login is not configured. Add `password` to `.streamlit/secrets.toml`."
                )
            elif password == expected:
                st.session_state.authenticated = True
                st.session_state.login_error = ""
                st.rerun()
            else:
                st.session_state.login_error = "Incorrect password. Please try again."

        if st.session_state.login_error:
            st.error(st.session_state.login_error)

        st.markdown("</div>", unsafe_allow_html=True)


def clear_selection() -> None:
    st.session_state.selected_member_ids = []
    st.session_state.selection_label = ""
    st.session_state.expanded_member_id = None


def refresh_data() -> None:
    get_members.clear()
    clear_selection()
    st.session_state.data_refresh_token += 1
    st.session_state.show_refresh_success = True
    st.rerun()


def render_kpi(label: str, value: str, sub: str = "") -> None:
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner="Loading member data...")
def get_members() -> tuple[pd.DataFrame, str, dict]:
    df, path, stats = load_members()
    source = path.name if path else "none"
    mtime = ""
    if path and path.exists():
        mtime = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    return df, f"{source} ({mtime})" if mtime else source, stats


def apply_sidebar_filters(
    df: pd.DataFrame,
    *,
    categories: list[str],
    industries: list[str],
    size_bands: list[str],
    regions: list[str],
    counties: list[str],
    membership_types: list[str],
    include_opted_out: bool,
    include_bounced: bool,
) -> pd.DataFrame:
    filtered = df.copy()
    if categories:
        filtered = filtered[filtered["category"].isin(categories)]
    if industries:
        filtered = filtered[filtered["industry"].isin(industries)]
    if size_bands:
        filtered = filtered[filtered["size_band"].isin(size_bands)]
    if regions:
        filtered = filtered[filtered["region"].isin(regions)]
    if counties:
        filtered = filtered[filtered["county"].isin(counties)]
    if membership_types:
        filtered = filtered[filtered["membership_type"].isin(membership_types)]
    if not include_opted_out:
        filtered = filtered[~filtered["opted_out"]]
    if not include_bounced:
        filtered = filtered[~filtered["bounced"]]
    return filtered


def get_selection_df(base_df: pd.DataFrame) -> pd.DataFrame:
    ids = st.session_state.selected_member_ids
    if not ids:
        return base_df.iloc[0:0]
    return base_df[base_df["member_id"].isin(ids)].copy()


def upcoming_renewals_count(df: pd.DataFrame) -> int:
    current_month = datetime.now().month
    upcoming = {(current_month + offset - 1) % 12 + 1 for offset in range(3)}
    month_to_num = {name.lower(): num for name, num in MONTH_NAMES.items() if len(name) > 3}
    nums = df["renewal_month"].str.lower().map(month_to_num)
    return int(nums.isin(upcoming).sum())


def _first_point_value(points: list[dict[str, Any]], key: str) -> Any:
    if not points:
        return None
    point = points[0]
    if key in point and point[key] is not None:
        return point[key]
    return None


def _extract_customdata(point: dict[str, Any]) -> list[Any]:
    custom = point.get("customdata")
    if custom is None:
        return []
    if isinstance(custom, list):
        if custom and isinstance(custom[0], list):
            return custom[0]
        return custom
    return [custom]


def handle_chart_selection(
    chart_key: str,
    points: list[dict[str, Any]],
    base_df: pd.DataFrame,
) -> None:
    if not points:
        return

    spec = CHART_SPECS.get(chart_key, {})
    dimension = spec.get("dimension")
    sub_dimension = spec.get("sub_dimension")
    if not dimension:
        return

    point = points[0]
    custom = _extract_customdata(point)

    value = custom[0] if custom else None
    sub_value = custom[1] if len(custom) > 1 else None

    if value is None:
        if dimension in ("category", "industry", "county", "size_band"):
            value = _first_point_value(points, "y") or _first_point_value(points, "label")
        else:
            value = _first_point_value(points, "x") or _first_point_value(points, "label")

    if sub_dimension and sub_value is None:
        sub_value = point.get("legendgroup") or _first_point_value(points, "legendgroup")

    if value is None:
        return

    subset = base_df[base_df[dimension].astype(str) == str(value)]
    if sub_dimension and sub_value is not None:
        subset = subset[subset[sub_dimension].astype(str) == str(sub_value)]

    label = f"{spec.get('label', dimension)}: {value}"
    if sub_dimension and sub_value is not None:
        label = f"{label} · {sub_value}"

    st.session_state.selected_member_ids = subset["member_id"].tolist()
    st.session_state.selection_label = label
    st.session_state.expanded_member_id = None


def _attach_customdata(fig, chart_df: pd.DataFrame, custom_cols: list[str]) -> None:
    values = chart_df[custom_cols].values
    if len(fig.data) == 1:
        fig.data[0].customdata = values
        return
    for trace in fig.data:
        group = trace.name
        col = custom_cols[-1] if len(custom_cols) > 1 else custom_cols[0]
        if col in chart_df.columns and group is not None:
            subset = chart_df[chart_df[col].astype(str) == str(group)]
            trace.customdata = subset[custom_cols].values
        else:
            trace.customdata = values


def plot_chart(fig, chart_key: str, chart_df: pd.DataFrame, custom_cols: list[str]) -> None:
    fig.update_layout(
        template="plotly_white",
        margin=dict(l=20, r=20, t=40, b=20),
        font=dict(family="Segoe UI, sans-serif", size=12),
        height=380,
        clickmode="event+select",
    )
    if custom_cols:
        _attach_customdata(fig, chart_df, custom_cols)

    event = st.plotly_chart(
        fig,
        use_container_width=True,
        key=chart_key,
        on_select="rerun",
        selection_mode="points",
    )

    if event and getattr(event, "selection", None) and event.selection.points:
        handle_chart_selection(chart_key, event.selection.points, st.session_state._chart_base_df)


def render_overview(df: pd.DataFrame) -> None:
    st.session_state._chart_base_df = df
    st.caption("Click any chart segment to select members. Selection appears in the right panel.")

    col1, col2 = st.columns(2)

    with col1:
        cat_df = df["category"].value_counts().reset_index()
        cat_df.columns = ["category", "count"]
        fig = px.bar(
            cat_df,
            x="count",
            y="category",
            orientation="h",
            title="Members by Category",
            color="count",
            color_continuous_scale="Blues",
        )
        fig.update_layout(showlegend=False, yaxis={"categoryorder": "total ascending"})
        plot_chart(fig, "chart_category", cat_df, ["category"])

    with col2:
        ind_df = df["industry"].value_counts().reset_index()
        ind_df.columns = ["industry", "count"]
        fig = px.pie(
            ind_df,
            names="industry",
            values="count",
            title="Industry Mix",
            hole=0.45,
            color_discrete_sequence=px.colors.sequential.Blues_r,
        )
        fig.update_traces(customdata=ind_df[["industry"]].values)
        plot_chart(fig, "chart_industry", ind_df, ["industry"])

    col3, col4 = st.columns(2)

    with col3:
        reg_df = df["region"].value_counts().reset_index()
        reg_df.columns = ["region", "count"]
        fig = px.bar(reg_df, x="region", y="count", title="Members by Region", color_discrete_sequence=["#1a4d7c"])
        fig.update_layout(showlegend=False)
        plot_chart(fig, "chart_region", reg_df, ["region"])

    with col4:
        county_df = (
            df[df["county"] != "Unknown"]["county"].value_counts().head(10).reset_index()
        )
        county_df.columns = ["county", "count"]
        fig = px.bar(
            county_df,
            x="count",
            y="county",
            orientation="h",
            title="Top 10 Counties",
            color="count",
            color_continuous_scale="Teal",
        )
        fig.update_layout(showlegend=False, yaxis={"categoryorder": "total ascending"})
        plot_chart(fig, "chart_county", county_df, ["county"])

    col5, col6 = st.columns(2)

    with col5:
        size_df = df["size_band"].value_counts().reset_index()
        size_df.columns = ["size_band", "count"]
        order = ["Solo", "Small", "Mid", "Large", "Unknown"]
        size_df["size_band"] = pd.Categorical(size_df["size_band"], categories=order, ordered=True)
        size_df = size_df.sort_values("size_band")
        fig = px.bar(
            size_df,
            x="size_band",
            y="count",
            title="Size Band (Contact Proxy)",
            color_discrete_sequence=["#2e6b9e"],
        )
        fig.update_layout(showlegend=False)
        plot_chart(fig, "chart_size", size_df, ["size_band"])

    with col6:
        mix_df = df.groupby(["category", "membership_type"]).size().reset_index(name="count")
        fig = px.bar(
            mix_df,
            x="category",
            y="count",
            color="membership_type",
            title="Membership Type by Category",
            barmode="stack",
        )
        fig.update_layout(xaxis_tickangle=-30)
        plot_chart(fig, "chart_membership", mix_df, ["category", "membership_type"])

    renewal_df = df[df["renewal_month"] != ""]["renewal_month"].value_counts().reset_index()
    if not renewal_df.empty:
        renewal_df.columns = ["renewal_month", "count"]
        month_order = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]
        renewal_df["renewal_month"] = pd.Categorical(
            renewal_df["renewal_month"], categories=month_order, ordered=True
        )
        renewal_df = renewal_df.sort_values("renewal_month")
        fig = px.bar(renewal_df, x="renewal_month", y="count", title="Renewals by Month")
        fig.update_layout(showlegend=False, xaxis_tickangle=-45)
        plot_chart(fig, "chart_renewal", renewal_df, ["renewal_month"])


def render_directory(df: pd.DataFrame) -> None:
    search = st.text_input(
        "Search members",
        placeholder="Name, city, contact, email, or industry...",
    )

    display_df = df.copy()
    if search:
        mask = pd.Series(False, index=display_df.index)
        for col in ["member_name", "city", "primary_contact", "email", "industry", "county"]:
            mask |= display_df[col].astype(str).str.contains(search, case=False, na=False)
        display_df = display_df[mask]

    st.caption(f"Showing {len(display_df)} of {len(df)} filtered members")

    table_cols = [
        "member_name",
        "category",
        "industry",
        "membership_type",
        "website",
        "primary_contact",
        "email",
        "phone",
        "city",
        "county",
        "region",
        "size_band",
        "renewal",
    ]
    table_cols = [c for c in table_cols if c in display_df.columns]

    st.dataframe(
        display_df[table_cols].sort_values(["member_name", "city"]),
        use_container_width=True,
        hide_index=True,
        column_config={
            "website": st.column_config.LinkColumn("Website", display_text="Visit"),
            "member_name": st.column_config.TextColumn("Organization", width="large"),
            "email": st.column_config.TextColumn("Email"),
            "renewal": st.column_config.TextColumn("Renewal"),
        },
    )

    csv_bytes = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download filtered results (CSV)",
        data=csv_bytes,
        file_name="camps_members_filtered.csv",
        mime="text/csv",
    )

    with st.expander("All columns"):
        st.dataframe(display_df.sort_values("member_name"), use_container_width=True, hide_index=True)


def render_insights(df: pd.DataFrame) -> None:
    insights = generate_insights(df)
    themes: dict[str, list[Insight]] = {}
    for item in insights:
        themes.setdefault(item.theme, []).append(item)

    for theme, items in themes.items():
        st.subheader(theme)
        for item in items:
            if item.severity == "warning":
                st.warning(item.message)
            else:
                st.info(item.message)


def _detail_row(label: str, value: str) -> str:
    if not value or str(value).strip() in {"", "nan", "None"}:
        return ""
    return f"<dt>{label}</dt><dd>{value}</dd>"


def render_member_detail_card(member: pd.Series) -> None:
    website = member.get("website", "")
    website_html = (
        f'<dd><a href="{website}" target="_blank">{website}</a></dd>'
        if website
        else ""
    )
    rows = [
        _detail_row("Category", member.get("category", "")),
        _detail_row("Industry", member.get("industry", "")),
        _detail_row("Membership", member.get("membership_type", "")),
        _detail_row("Contact", member.get("primary_contact", "")),
        _detail_row("Title", member.get("job_title", "")),
        _detail_row("Email", member.get("email", "")),
        _detail_row("Phone", member.get("phone", "")),
        _detail_row("City", member.get("city", "")),
        _detail_row("County", member.get("county", "")),
        _detail_row("Region", member.get("region", "")),
        _detail_row("Address", member.get("address", "")),
        _detail_row("ZIP", member.get("zip", "")),
        _detail_row("Renewal", member.get("renewal", "")),
        _detail_row("Size band", member.get("size_band", "")),
        _detail_row("Additional contacts", str(member.get("contact_count", 0))),
    ]
    body = "".join(rows)
    website_block = "<dt>Website</dt>" + website_html if website_html else ""
    st.markdown(
        f'<div class="member-card"><dl>{website_block}{body}</dl></div>',
        unsafe_allow_html=True,
    )


def build_selection_export(selection_df: pd.DataFrame) -> bytes:
    cols = [c for c in EXPORT_COLUMNS if c in selection_df.columns]
    export_df = selection_df[cols].rename(columns=EXPORT_COLUMNS)
    return export_df.to_csv(index=False).encode("utf-8")


def render_selected_members_panel(base_df: pd.DataFrame) -> None:
    st.markdown('<div class="selected-panel">', unsafe_allow_html=True)
    st.markdown("### Selected Members")

    selection_df = get_selection_df(base_df)
    has_selection = not selection_df.empty

    if has_selection:
        st.markdown(
            f'<div class="selection-banner">{st.session_state.selection_label} '
            f"({len(selection_df)} members)</div>",
            unsafe_allow_html=True,
        )
        if st.button("Clear selection", key="clear_selection", use_container_width=True):
            clear_selection()
            st.rerun()

        st.download_button(
            "Download these members as CSV",
            data=build_selection_export(selection_df),
            file_name="camps_selected_members.csv",
            mime="text/csv",
            use_container_width=True,
            key="download_selection",
        )
        st.divider()

        for _, member in selection_df.sort_values("member_name").iterrows():
            member_id = member["member_id"]
            is_expanded = st.session_state.expanded_member_id == member_id
            label = f"{'▾' if is_expanded else '▸'} {member['member_name']}"

            if st.button(label, key=f"member_toggle_{member_id}", use_container_width=True):
                st.session_state.expanded_member_id = (
                    None if is_expanded else member_id
                )
                st.rerun()

            if is_expanded:
                render_member_detail_card(member)
    else:
        st.caption("Click a chart segment on the Overview tab to select members.")
        if st.session_state.selection_label:
            st.caption(f"Last selection cleared ({st.session_state.selection_label}).")

    st.markdown("</div>", unsafe_allow_html=True)


init_session_state()

if not st.session_state.authenticated:
    render_login_screen()
    st.stop()

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.title("CAMPS Member Analysis Dashboard")
st.caption("Interactive membership intelligence for the Center for Advanced Manufacturing Puget Sound")

df, source_label, stats = get_members()

if df.empty:
    st.error(
        "No member data found. Place `members.csv`, `members.xlsx`, or the master list in `data/`, "
        "then run `python scripts/build_members.py`."
    )
    st.stop()

st.sidebar.header("Filters")

all_categories = sorted(df["category"].dropna().unique())
all_industries = sorted(df["industry"].dropna().unique())
all_size_bands = ["Solo", "Small", "Mid", "Large", "Unknown"]
all_regions = sorted(df["region"].dropna().unique())
all_counties = sorted(df["county"].dropna().unique())
all_membership_types = sorted(df["membership_type"].dropna().unique())

filter_key = st.session_state.data_refresh_token
selected_categories = st.sidebar.multiselect(
    "Category", all_categories, default=all_categories, key=f"filter_category_{filter_key}"
)
selected_industries = st.sidebar.multiselect(
    "Industry", all_industries, default=all_industries, key=f"filter_industry_{filter_key}"
)
selected_size_bands = st.sidebar.multiselect(
    "Size band (contact proxy)",
    all_size_bands,
    default=all_size_bands,
    help="Derived from primary + additional contacts listed in the roster. Not employee headcount.",
    key=f"filter_size_{filter_key}",
)
selected_regions = st.sidebar.multiselect(
    "Region", all_regions, default=all_regions, key=f"filter_region_{filter_key}"
)
selected_counties = st.sidebar.multiselect(
    "County", all_counties, default=all_counties, key=f"filter_county_{filter_key}"
)
selected_membership_types = st.sidebar.multiselect(
    "Membership type",
    all_membership_types,
    default=all_membership_types,
    key=f"filter_membership_{filter_key}",
)

st.sidebar.divider()
include_opted_out = st.sidebar.checkbox(
    "Include opted-out members", value=True, key=f"filter_opted_out_{filter_key}"
)
include_bounced = st.sidebar.checkbox(
    "Include bounced contacts", value=True, key=f"filter_bounced_{filter_key}"
)

if st.sidebar.button("Reset filters"):
    clear_selection()
    st.rerun()

sidebar_filtered = apply_sidebar_filters(
    df,
    categories=selected_categories,
    industries=selected_industries,
    size_bands=selected_size_bands,
    regions=selected_regions,
    counties=selected_counties,
    membership_types=selected_membership_types,
    include_opted_out=include_opted_out,
    include_bounced=include_bounced,
)

selection_df = get_selection_df(sidebar_filtered)
kpi_df = selection_df if not selection_df.empty else sidebar_filtered

main_col, panel_col = st.columns([4, 1.35], gap="medium")

with main_col:
    if st.session_state.show_refresh_success:
        st.success("Data refreshed successfully.")
        st.session_state.show_refresh_success = False

    header_col1, header_col2, header_col3 = st.columns([2.8, 1.1, 1.1])
    with header_col1:
        st.markdown(f"**Data source:** `{source_label}`")
    with header_col2:
        st.markdown(f"**Showing:** {len(sidebar_filtered)} / {len(df)} members")
    with header_col3:
        if st.button("Refresh Data", type="secondary", use_container_width=True, help="Reload the latest CSV from disk"):
            refresh_data()

    if not selection_df.empty:
        st.markdown(
            f'<div class="selection-banner">Chart selection active — KPIs reflect '
            f"<b>{len(selection_df)}</b> selected members. "
            f"{st.session_state.selection_label}</div>",
            unsafe_allow_html=True,
        )

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    with k1:
        render_kpi("Total Members", f"{len(kpi_df):,}")
    with k2:
        render_kpi("Categories", f"{kpi_df['category'].nunique()}")
    with k3:
        pct = kpi_df["has_website"].mean() * 100 if len(kpi_df) else 0
        render_kpi("With Website", f"{pct:.0f}%", f"{int(kpi_df['has_website'].sum())} members")
    with k4:
        ht = (kpi_df["membership_type"] == "Health Trust").sum()
        render_kpi("Health Trust", f"{ht:,}")
    with k5:
        render_kpi("Renewals (90d)", f"{upcoming_renewals_count(kpi_df):,}", "By renewal month")
    with k6:
        render_kpi("Regions", f"{kpi_df['region'].nunique()}", f"{kpi_df['county'].nunique()} counties")

    tab_overview, tab_directory, tab_insights = st.tabs(["Overview", "Member Directory", "Insights"])

    with tab_overview:
        if sidebar_filtered.empty:
            st.warning("No members match the current filters.")
        else:
            render_overview(sidebar_filtered)

    with tab_directory:
        if sidebar_filtered.empty:
            st.warning("No members match the current filters.")
        else:
            render_directory(sidebar_filtered)

    with tab_insights:
        render_insights(kpi_df)

with panel_col:
    render_selected_members_panel(sidebar_filtered)

with st.sidebar.expander("Data quality"):
    st.write(stats)
    st.caption(
        "Size band uses contact-count proxy. County/region derived from city and ZIP when not provided."
    )