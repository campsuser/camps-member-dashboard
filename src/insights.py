"""Generate rule-based insights from filtered member data."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class Insight:
    theme: str
    severity: str  # info | warning
    message: str


def generate_insights(df: pd.DataFrame) -> list[Insight]:
    if df.empty:
        return [Insight("Data", "warning", "No members match the current filters.")]

    insights: list[Insight] = []
    total = len(df)

    category_counts = df["category"].value_counts()
    if not category_counts.empty:
        top_cat = category_counts.index[0]
        share = category_counts.iloc[0] / total * 100
        insights.append(
            Insight(
                "Composition",
                "info",
                f"**{top_cat}** is the largest segment with {category_counts.iloc[0]} members ({share:.1f}% of filtered set).",
            )
        )

    county_counts = df[df["county"] != "Unknown"]["county"].value_counts()
    if not county_counts.empty:
        top_counties = county_counts.head(3)
        parts = [f"{name} ({count})" for name, count in top_counties.items()]
        insights.append(
            Insight(
                "Geography",
                "info",
                f"Top counties: {', '.join(parts)}.",
            )
        )

    region_counts = df["region"].value_counts()
    if not region_counts.empty:
        top_region = region_counts.index[0]
        insights.append(
            Insight(
                "Geography",
                "info",
                f"**{top_region}** leads regional representation with {region_counts.iloc[0]} members.",
            )
        )

    out_of_state = (df["region"] == "Out of State").sum()
    if out_of_state:
        examples = ", ".join(df.loc[df["region"] == "Out of State", "member_name"].head(3).tolist())
        insights.append(
            Insight(
                "Geography",
                "info",
                f"{out_of_state} member(s) are outside Washington (e.g. {examples}).",
            )
        )

    no_website = (~df["has_website"]).sum()
    if no_website:
        examples = ", ".join(df.loc[~df["has_website"], "member_name"].head(3).tolist())
        insights.append(
            Insight(
                "Data Quality",
                "warning",
                f"{no_website} members ({no_website / total * 100:.1f}%) are missing a website (e.g. {examples}).",
            )
        )

    opted_out = df["opted_out"].sum()
    if opted_out:
        insights.append(
            Insight(
                "Data Quality",
                "warning",
                f"{opted_out} member(s) are flagged as opted out of communications.",
            )
        )

    bounced = df["bounced"].sum()
    if bounced:
        insights.append(
            Insight(
                "Data Quality",
                "warning",
                f"{bounced} member(s) have bounced contact records.",
            )
        )

    health_trust = (df["membership_type"] == "Health Trust").sum()
    if health_trust:
        insights.append(
            Insight(
                "Composition",
                "info",
                f"{health_trust} members ({health_trust / total * 100:.1f}%) participate in the Health Trust program.",
            )
        )

    renewal_months = df[df["renewal_month"] != ""]["renewal_month"].value_counts()
    if not renewal_months.empty:
        peak_month = renewal_months.index[0]
        insights.append(
            Insight(
                "Renewals",
                "info",
                f"Renewals cluster most in **{peak_month}** ({renewal_months.iloc[0]} members with a known renewal month).",
            )
        )

    unknown_renewal = (df["renewal_month"] == "").sum()
    if unknown_renewal:
        insights.append(
            Insight(
                "Renewals",
                "warning",
                f"{unknown_renewal} members have renewal dates that could not be parsed to a month.",
            )
        )

    avg_contacts = df.groupby("category")["contact_count"].mean().sort_values(ascending=False)
    if not avg_contacts.empty and avg_contacts.iloc[0] > 0:
        cat = avg_contacts.index[0]
        insights.append(
            Insight(
                "Composition",
                "info",
                f"**{cat}** has the highest average additional-contact count ({avg_contacts.iloc[0]:.1f}), a proxy for organizational reach.",
            )
        )

    unknown_county = (df["county"] == "Unknown").sum()
    if unknown_county:
        insights.append(
            Insight(
                "Data Quality",
                "warning",
                f"{unknown_county} members lack a resolvable county (missing or unrecognized city/zip).",
            )
        )

    return insights