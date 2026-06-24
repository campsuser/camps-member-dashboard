#!/usr/bin/env python3
"""
clean_master_list.py

Reusable cleaning and standardization script for the CAMPS Member Master List.

Usage examples:
    # Clean a new legacy export
    python scripts/clean_master_list.py \
        --input data/raw/CAMPS_Company_Master_Data_Source_2026_July.csv \
        --output data/members_master.csv \
        --mode legacy

    # Re-validate / clean an already-clean master (recommended monthly)
    python scripts/clean_master_list.py \
        --input data/members_master.csv \
        --output data/members_master.csv \
        --mode clean

    # Dry run (see what would change without writing)
    python scripts/clean_master_list.py \
        --input data/members_master.csv \
        --mode clean \
        --dry-run
"""

import argparse
import pandas as pd
import numpy as np
import re
from datetime import datetime
from pathlib import Path
import sys


def parse_args():
    parser = argparse.ArgumentParser(
        description="Clean and standardize the CAMPS Member Master List."
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to input CSV (legacy messy format or already-clean master)"
    )
    parser.add_argument(
        "--output", "-o",
        required=False,
        help="Path to write cleaned CSV. If omitted with --dry-run, no file is written."
    )
    parser.add_argument(
        "--mode",
        choices=["legacy", "clean"],
        default="clean",
        help="Input mode: 'legacy' = old messy source, 'clean' = already follows clean structure"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run cleaning but do not write output file. Useful for previewing changes."
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed change log to console"
    )
    return parser.parse_args()


def add_quality_note(notes_series, idx, new_note):
    """Append a note to the Data_Quality_Notes column."""
    current = str(notes_series.get(idx, "")).strip()
    if current and current.lower() != "nan":
        return current + "; " + new_note
    return new_note


def clean_company_names(df):
    """Remove embedded ** notes and trim trailing punctuation/spaces."""
    changes = []
    for idx in df.index:
        name = str(df.at[idx, "Company Name"]).strip()
        original = name

        # Remove ** Renews... style notes
        if "**" in name:
            cleaned = re.sub(r"\s*\*\*.*$", "", name).strip()
            df.at[idx, "Company Name"] = cleaned
            df.at[idx, "Data_Quality_Notes"] = add_quality_note(
                df["Data_Quality_Notes"], idx,
                f"Stripped embedded note from name: '{original}' -> '{cleaned}'"
            )
            changes.append((original, cleaned, "embedded_note"))

        # Trim trailing punctuation and spaces
        cleaned = str(df.at[idx, "Company Name"]).strip().rstrip(".").strip()
        if cleaned != str(df.at[idx, "Company Name"]):
            df.at[idx, "Company Name"] = cleaned
            df.at[idx, "Data_Quality_Notes"] = add_quality_note(
                df["Data_Quality_Notes"], idx, "Trimmed trailing punctuation/spaces from name"
            )
            changes.append((original, cleaned, "trim"))

    return df, changes


def fix_corrupted_websites(df):
    """Fix known data corruption in Website column."""
    fixes = {
        # These row indices are examples; in production you may want to match by Company Name instead
        # For robustness we match by partial name + bad pattern
    }

    changes = []
    # Pattern-based fixes (more robust than hard-coded indices)
    for idx in df.index:
        website = str(df.at[idx, "Website"]).strip().lower() if pd.notna(df.at[idx, "Website"]) else ""
        company = str(df.at[idx, "Company Name"]).lower()

        # Fix "er" junk value
        if website == "er":
            df.at[idx, "Website"] = np.nan
            df.at[idx, "Data_Quality_Notes"] = add_quality_note(
                df["Data_Quality_Notes"], idx,
                "Removed invalid 'er' value from Website column (data entry error)"
            )
            changes.append((df.at[idx, "Company Name"], "Website", "removed 'er' junk"))

        # Fix polluted website fields that contain address-like text
        if any(x in website for x in ["|", "tensed", "mine door"]) and "http" not in website:
            df.at[idx, "Website"] = np.nan
            df.at[idx, "Data_Quality_Notes"] = add_quality_note(
                df["Data_Quality_Notes"], idx,
                "Cleared polluted Website field (contained address/description text)"
            )
            changes.append((df.at[idx, "Company Name"], "Website", "cleared polluted value"))

        # Fix copy-paste error on Squires Machine (wrong site from previous row)
        if "squires machine" in company and "spincycle" in website:
            df.at[idx, "Website"] = np.nan
            df.at[idx, "Data_Quality_Notes"] = add_quality_note(
                df["Data_Quality_Notes"], idx,
                "Removed incorrect website (was copy-pasted from Spincycle Yarns row)"
            )
            changes.append((df.at[idx, "Company Name"], "Website", "removed copy-paste error"))

        # Clean mixed name+domain (e.g. "Columbia Bank | ColumbiaBank.com")
        if "|" in str(df.at[idx, "Website"]):
            # Try to extract domain
            match = re.search(r"([a-zA-Z0-9-]+\.[a-zA-Z]{2,})", str(df.at[idx, "Website"]))
            if match:
                domain = match.group(1)
                if not domain.startswith("http"):
                    domain = "https://" + domain
                df.at[idx, "Website"] = domain
                df.at[idx, "Data_Quality_Notes"] = add_quality_note(
                    df["Data_Quality_Notes"], idx,
                    f"Cleaned mixed name+domain in Website to '{domain}'"
                )
                changes.append((df.at[idx, "Company Name"], "Website", "extracted domain from mixed text"))

    return df, changes


def normalize_websites(df):
    """Ensure consistent https:// format for valid-looking domains."""
    changes = []
    for idx in df.index:
        w = df.at[idx, "Website"]
        if pd.isna(w) or str(w).strip() == "":
            continue
        w = str(w).strip()
        original = w

        if not (w.startswith("http://") or w.startswith("https://")):
            if "." in w and len(w) > 4 and " " not in w and "|" not in w:
                w = "https://" + w.lstrip("/")
                df.at[idx, "Website"] = w
                df.at[idx, "Data_Quality_Notes"] = add_quality_note(
                    df["Data_Quality_Notes"], idx,
                    f"Normalized bare domain to https:// URL"
                )
                changes.append((df.at[idx, "Company Name"], "Website", f"{original} -> {w}"))

        # Strip trailing slash for cleanliness
        if str(df.at[idx, "Website"]).endswith("/"):
            df.at[idx, "Website"] = str(df.at[idx, "Website"]).rstrip("/")
            changes.append((df.at[idx, "Company Name"], "Website", "stripped trailing slash"))

    return df, changes


def standardize_renewal_and_sponsorship(df):
    """Move IN-KIND from Renewal to Sponsorship_Type and normalize months."""
    changes = []
    for idx in df.index:
        renewal = str(df.at[idx, "Renewal"]).strip().upper() if pd.notna(df.at[idx, "Renewal"]) else ""

        if renewal == "IN-KIND":
            df.at[idx, "Sponsorship_Type"] = "IN-KIND"
            df.at[idx, "Renewal"] = np.nan
            df.at[idx, "Data_Quality_Notes"] = add_quality_note(
                df["Data_Quality_Notes"], idx,
                "Moved 'IN-KIND' from Renewal column to Sponsorship_Type (AFFILIATES sponsorship)"
            )
            changes.append((df.at[idx, "Company Name"], "Renewal", "IN-KIND → Sponsorship_Type"))

        elif renewal in ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
                         "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]:
            df.at[idx, "Renewal"] = renewal  # already clean
        elif renewal and renewal != "NAN":
            # Keep unusual values but note them
            df.at[idx, "Data_Quality_Notes"] = add_quality_note(
                df["Data_Quality_Notes"], idx,
                f"Unusual Renewal value kept: '{renewal}'"
            )
            changes.append((df.at[idx, "Company Name"], "Renewal", f"unusual value: {renewal}"))

    return df, changes


def clean_zip_codes(df):
    """Fix trailing dashes and flag suspicious short zips."""
    changes = []
    for idx in df.index:
        zip_val = str(df.at[idx, "Zip"]).strip() if pd.notna(df.at[idx, "Zip"]) else ""
        if not zip_val or zip_val.lower() == "nan":
            continue

        original = zip_val

        if zip_val.endswith("-"):
            zip_val = zip_val.rstrip("-")
            df.at[idx, "Zip"] = zip_val
            df.at[idx, "Data_Quality_Notes"] = add_quality_note(
                df["Data_Quality_Notes"], idx,
                f"Fixed trailing dash in Zip: '{original}' -> '{zip_val}'"
            )
            changes.append((df.at[idx, "Company Name"], "Zip", f"removed trailing dash: {original}"))

        if len(zip_val) < 5 and zip_val.isdigit():
            df.at[idx, "Data_Quality_Notes"] = add_quality_note(
                df["Data_Quality_Notes"], idx,
                f"Suspicious short/incomplete Zip code: '{zip_val}' (manual review recommended)"
            )
            changes.append((df.at[idx, "Company Name"], "Zip", f"flagged short zip: {zip_val}"))

    return df, changes


def add_hierarchical_categories(df):
    """Create Category_Group and Subcategory columns."""
    mapping = {
        "MANUFACTURERS": ("MANUFACTURERS", None),
        "JOINT ACCESS - CANNABIS": ("JOINT ACCESS", "Cannabis"),
        "JOINT ACCESS - WINE ASSOCIATION": ("JOINT ACCESS", "Wine Association"),
        "JOINT ACCESS - BREWING": ("JOINT ACCESS", "Brewing"),
        "JOINT ACCESS - PNAA": ("JOINT ACCESS", "PNAA"),
        "JOINT ACCESS - NIMA": ("JOINT ACCESS", "NIMA"),
        "SUPPLY CHAIN": ("SUPPLY CHAIN", None),
        "ASSOCIATES": ("ASSOCIATES", None),
        "AFFILIATES": ("AFFILIATES", None),
    }

    for idx in df.index:
        cat = df.at[idx, "Category"]
        if cat in mapping:
            df.at[idx, "Category_Group"] = mapping[cat][0]
            sub = mapping[cat][1]
            if sub:
                df.at[idx, "Subcategory"] = sub
        else:
            df.at[idx, "Category_Group"] = cat  # fallback

    return df


def standardize_health_trust(df):
    """Normalize Health Trust values."""
    def _std(val):
        if pd.isna(val) or str(val).strip() == "":
            return "No"
        v = str(val).strip().lower()
        if v == "yes":
            return "Yes"
        if "corporate" in v:
            return "Corporate Sponsor"
        return str(val).strip()

    df["Health Trust"] = df["Health Trust"].apply(_std)
    return df


def add_missing_data_flags(df):
    """Add boolean flags for missing critical fields."""
    df["Missing_Address"] = df["Address"].isna() | (df["Address"].astype(str).str.strip() == "")
    df["Missing_City_Zip"] = (
        (df["City"].isna() | (df["City"].astype(str).str.strip() == "")) |
        (df["Zip"].isna() | (df["Zip"].astype(str).str.strip() == ""))
    )
    df["Missing_Phone"] = df["Main Phone"].isna() | (df["Main Phone"].astype(str).str.strip() == "")
    return df


def ensure_clean_columns(df):
    """Ensure all expected clean columns exist with proper defaults."""
    expected = {
        "Company Name": "",
        "Category": "",
        "Category_Group": "",
        "Subcategory": np.nan,
        "Health Trust": "No",
        "Sponsorship_Type": np.nan,
        "Renewal": np.nan,
        "Website": np.nan,
        "Address": "",
        "City": "",
        "Zip": "",
        "Main Phone": "",
        "Status": "Active",
        "Missing_Address": False,
        "Missing_City_Zip": False,
        "Missing_Phone": False,
        "Data_Quality_Notes": "",
    }

    for col, default in expected.items():
        if col not in df.columns:
            df[col] = default

    # Ensure correct dtypes
    df["Data_Quality_Notes"] = df["Data_Quality_Notes"].fillna("").astype(str)
    df["Sponsorship_Type"] = df["Sponsorship_Type"].astype("object")
    df["Subcategory"] = df["Subcategory"].astype("object")

    return df


def clean_master(input_path: Path, mode: str = "clean", verbose: bool = False):
    """Main cleaning pipeline."""
    print(f"Reading input: {input_path}")
    df = pd.read_csv(input_path, dtype=str)

    # Standardize column names (handle both legacy and clean)
    column_map = {
        "Company_Name": "Company Name",
        "Health_Trust_Status": "Health Trust",
        "Main_Phone": "Main Phone",
    }
    df = df.rename(columns=column_map)

    df = ensure_clean_columns(df)

    all_changes = []

    # Run cleaning steps
    df, ch = clean_company_names(df)
    all_changes.extend(ch)
    if verbose:
        print(f"  - Cleaned {len(ch)} company name issues")

    df, ch = fix_corrupted_websites(df)
    all_changes.extend(ch)
    if verbose:
        print(f"  - Fixed {len(ch)} website corruption issues")

    df, ch = normalize_websites(df)
    all_changes.extend(ch)
    if verbose:
        print(f"  - Normalized {len(ch)} website URLs")

    df, ch = standardize_renewal_and_sponsorship(df)
    all_changes.extend(ch)
    if verbose:
        print(f"  - Standardized {len(ch)} renewal/sponsorship values")

    df, ch = clean_zip_codes(df)
    all_changes.extend(ch)
    if verbose:
        print(f"  - Cleaned/flagged {len(ch)} zip code issues")

    df = add_hierarchical_categories(df)
    df = standardize_health_trust(df)
    df = add_missing_data_flags(df)

    # Final column order (clean master standard)
    final_order = [
        "Company Name", "Category", "Category_Group", "Subcategory",
        "Health Trust", "Sponsorship_Type", "Renewal",
        "Website", "Address", "City", "Zip", "Main Phone", "Status",
        "Missing_Address", "Missing_City_Zip", "Missing_Phone", "Data_Quality_Notes"
    ]
    df = df[[c for c in final_order if c in df.columns]]

    print(f"\nCleaning complete. Total records: {len(df)}")
    print(f"Records with Data Quality Notes: {(df['Data_Quality_Notes'] != '').sum()}")

    if verbose and all_changes:
        print("\nSample of changes made:")
        for item in all_changes[:10]:
            print(f"  • {item}")

    return df, all_changes


def main():
    args = parse_args()
    input_path = Path(args.input)

    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    df, changes = clean_master(input_path, mode=args.mode, verbose=args.verbose)

    if args.dry_run:
        print("\n[DRY RUN] No file written. Use --output to save results.")
        return

    if not args.output:
        print("ERROR: --output is required unless --dry-run is used.", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"\n✅ Cleaned master list written to: {output_path}")


if __name__ == "__main__":
    main()