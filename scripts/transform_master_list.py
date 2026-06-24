#!/usr/bin/env python3
"""
CAMPS Member Dashboard - Master List Transformer
Clean version with your column names - June 23, 2026
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import re
import sys

DATA_DIR = Path("data")
OUTPUT_FILE = DATA_DIR / "members.csv"
BACKUP_DIR = DATA_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

TARGET_COLUMNS = [
    "Company Name", "Category", "Health Trust", "Renewal Month",
    "Website", "Main Contact", "Email Address", "Physical Address",
    "City", "Zip Code"
]

# Updated aliases that match your file (Company_Name, Health_Trust_Status, Renewal, Address, Zip, etc.)
COLUMN_ALIASES = {
    "Company Name": [
        "company name", "company_name", "company", "name", 
        "organization", "org name", "legal_name", "legal name"
    ],
    "Category": ["category", "type", "member type", "industry", "sector"],
    "Health Trust": [
        "health trust", "health_trust", "healthtrust", "ht", "benefits", "trust",
        "health_trust_status", "health trust status"
    ],
    "Renewal Month": [
        "renewal month", "renewal_month", "renewal", "renewal date", 
        "expires", "expiration", "month"
    ],
    "Website": ["website", "web", "url", "site", "web site"],
    "Main Contact": [
        "main contact", "contact", "primary contact", "contact name", 
        "key contact", "main_phone"
    ],
    "Email Address": [
        "email address", "email", "e-mail", "contact email", "primary email"
    ],
    "Physical Address": [
        "physical address", "address", "street address", "mailing address", "addr"
    ],
    "City": ["city", "town"],
    "Zip Code": ["zip code", "zip_code", "zip", "postal code", "zipcode", "postcode"]
}

CATEGORY_MAPPING = {
    "aerospace": "Aerospace & Defense",
    "defense": "Aerospace & Defense",
    "maritime": "Maritime & Shipbuilding",
    "food": "Food & Beverage Processing",
    "clean tech": "Clean Technology & Energy",
    "manufacturing": "Advanced Manufacturing",
    "metal fab": "Metal Fabrication & Machining",
    "electronics": "Electronics & Technology",
    "medical": "Medical Devices & Life Sciences",
}

MONTH_MAP = {
    "jan": "January", "january": "January",
    "feb": "February", "february": "February",
    "mar": "March", "march": "March",
    "apr": "April", "april": "April",
    "may": "May",
    "jun": "June", "june": "June",
    "jul": "July", "july": "July",
    "aug": "August", "august": "August",
    "sep": "September", "sept": "September", "september": "September",
    "oct": "October", "october": "October",
    "nov": "November", "november": "November",
    "dec": "December", "december": "December",
}

def find_latest_master_file():
    candidates = list(DATA_DIR.glob("*[Mm]aster*.csv"))
    if not candidates:
        raise FileNotFoundError("No master file with 'Master' in the name found in data/ folder.")
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]

def normalize_column_name(col):
    col_clean = str(col).strip().lower()
    for target, aliases in COLUMN_ALIASES.items():
        if col_clean in [a.lower() for a in aliases] or col_clean == target.lower():
            return target
    return col

def standardize_category(value):
    if pd.isna(value) or str(value).strip() == "":
        return ""
    val = str(value).strip().lower()
    return CATEGORY_MAPPING.get(val, str(value).strip().title())

def normalize_renewal_month(value):
    if pd.isna(value) or str(value).strip() == "":
        return ""
    val = str(value).strip().lower().replace(".", "")
    if val in MONTH_MAP:
        return MONTH_MAP[val]
    match = re.search(r"\b(0?[1-9]|1[0-2])\b", val)
    if match:
        return MONTH_MAP.get(match.group(1), str(value).strip().title())
    return str(value).strip().title()

def clean_text(value):
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value).strip())

def clean_email(value):
    if pd.isna(value):
        return ""
    email = str(value).strip().lower()
    return email if "@" in email else email

def clean_zip(value):
    if pd.isna(value):
        return ""
    zip_str = re.sub(r"[^\d-]", "", str(value).strip())
    if len(zip_str) == 9 and "-" not in zip_str:
        zip_str = zip_str[:5] + "-" + zip_str[5:]
    return zip_str