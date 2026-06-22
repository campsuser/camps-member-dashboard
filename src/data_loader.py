"""Load, clean, and standardize CAMPS member data from CSV or Excel sources."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.constants import (
    CITY_TO_COUNTY,
    DATA_DIR,
    INDUSTRY_MAP,
    MEMBER_FILE_CANDIDATES,
    MEMBERSHIP_TYPES,
    MONTH_NAMES,
    REGION_MAP,
    SECTION_MARKERS,
    STANDARD_COLUMNS,
    ZIP3_TO_COUNTY,
)

NOTE_PREFIXES = (
    "waiting for",
    "add ",
    "dropped trust",
    "note:",
)


def _clean(val: Any) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    return str(val).strip()


def _normalize_zip(zip_code: Any) -> str:
    zip_code = _clean(zip_code)
    if not zip_code:
        return ""
    digits = re.sub(r"\D", "", zip_code)
    if len(digits) >= 5:
        return digits[:5]
    if len(digits) == 4:
        return digits.zfill(5)
    return digits


def _normalize_website(url: str) -> str:
    url = _clean(url)
    if not url or url.lower() in {"website", "er", "n/a", "na"}:
        return ""
    if url.startswith("www."):
        url = f"https://{url}"
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url


def _parse_flags(name: str) -> tuple[str, bool, bool]:
    opted_out = "(opted out)" in name.lower()
    bounced = "(bounced)" in name.lower()
    cleaned = re.sub(r"\*\*.*?\*\*", "", name, flags=re.IGNORECASE)
    cleaned = re.sub(r"\(opted out\)", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\(bounced\)", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,")
    return cleaned, opted_out, bounced


def _parse_renewal_month(renewal: str) -> str:
    renewal = _clean(renewal)
    if not renewal:
        return ""

    lower = renewal.lower()
    for month_name, _ in sorted(MONTH_NAMES.items(), key=len, reverse=True):
        if month_name in lower:
            return month_name.title() if len(month_name) > 3 else month_name.capitalize()

    match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", renewal)
    if match:
        month = int(match.group(1))
        if 1 <= month <= 12:
            return datetime(2000, month, 1).strftime("%B")

    return ""


def _derive_county(city: str, zip_code: str) -> str:
    city_key = _clean(city).lower()
    if city_key in CITY_TO_COUNTY:
        return CITY_TO_COUNTY[city_key]

    zip_norm = _normalize_zip(zip_code)
    if not zip_norm:
        return "Unknown"

    if zip_norm.startswith(("98", "99")):
        prefix = zip_norm[:3]
        return ZIP3_TO_COUNTY.get(prefix, "Unknown")

    return "Out of State"


def _derive_region(county: str) -> str:
    return REGION_MAP.get(county, "Unknown")


def _derive_size_band(contact_count: int, has_primary_contact: bool) -> str:
    total = contact_count + (1 if has_primary_contact else 0)
    if total == 0:
        return "Unknown"
    if total == 1:
        return "Solo"
    if total <= 3:
        return "Small"
    if total <= 6:
        return "Mid"
    return "Large"


def _make_member_id(name: str, category: str) -> str:
    raw = f"{category}|{name}".lower().encode("utf-8")
    return hashlib.md5(raw).hexdigest()[:12]


def is_section_header(name: str) -> bool:
    return _clean(name).upper() in SECTION_MARKERS


def is_additional_contact(name: str) -> bool:
    return _clean(name).lower().startswith("additional")


def is_total_row(name: str) -> bool:
    return _clean(name).upper().startswith("TOTAL ")


def is_note_only(name: str) -> bool:
    lower = _clean(name).lower()
    return any(lower.startswith(prefix) for prefix in NOTE_PREFIXES)


def is_dba_continuation(name: str, website: str, contact: str) -> bool:
    name = _clean(name)
    if not name:
        return False
    if is_additional_contact(name) or is_section_header(name) or is_total_row(name):
        return False
    if contact:
        return False
    if "(dba)" in name.lower() or name.startswith(" ") or (website and len(name) < 80):
        return bool(website or "(dba)" in name.lower())
    return False


def _align_row(row: list[str]) -> dict[str, str] | None:
    while len(row) < 12:
        row.append("")

    c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11 = (
        row[1],
        row[2],
        row[3],
        row[4],
        row[5],
        row[6],
        row[7],
        row[8],
        row[9],
        row[10],
        row[11],
    )

    if is_section_header(c1):
        return {"kind": "section", "category": _clean(c1).upper()}

    if is_section_header(c2):
        return {"kind": "section", "category": _clean(c2).upper()}

    if _clean(c2) in {"Website", "Renewal"} or _clean(c3) == "Website":
        return None

    name = c1
    mem_type = c2
    website = c3
    renewal = c4
    contact = c5
    job_title = c6
    email = c7
    phone = c8
    address = c9
    city = c10
    zip_code = c11

    if c3 in MEMBERSHIP_TYPES:
        name = c2
        mem_type = c3
        website = c4
        renewal = c5
        contact = c6
        job_title = c7
        email = c8
        phone = c9
        address = c10
        city = c11
        zip_code = row[12] if len(row) > 12 else ""

    if is_note_only(name) and not c2:
        return None

    if is_note_only(name) and c2 and not is_additional_contact(c2):
        name = c2
        mem_type = c3
        website = c4
        renewal = c5
        contact = c6
        job_title = c7
        email = c8
        phone = c9
        address = c10
        city = c11
        zip_code = row[12] if len(row) > 12 else ""

    name = _clean(name)
    if not name:
        return None

    if is_total_row(name):
        return None

    if is_additional_contact(name):
        return {
            "kind": "additional",
            "contact": contact,
            "job_title": job_title,
            "email": email,
            "phone": phone,
            "city": city,
            "zip": zip_code,
            "opted_out": "(opted out)" in name.lower(),
            "bounced": "(bounced)" in name.lower(),
        }

    if is_dba_continuation(name, website, contact):
        return {"kind": "dba", "dba_name": name, "website": website}

    member_name, opted_out, bounced = _parse_flags(name)
    if not member_name:
        return None

    return {
        "kind": "member",
        "member_name": member_name,
        "membership_type": _clean(mem_type) or "Unknown",
        "website": _normalize_website(website),
        "renewal": _clean(renewal),
        "primary_contact": _clean(contact),
        "job_title": _clean(job_title),
        "email": _clean(email),
        "phone": _clean(phone),
        "address": _clean(address),
        "city": _clean(city),
        "zip": _normalize_zip(zip_code),
        "opted_out": opted_out,
        "bounced": bounced,
    }


def parse_master_list(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Parse the sectioned CAMPS master member CSV into one row per organization."""
    stats = {
        "rows_read": len(df),
        "sections_found": 0,
        "primary_members": 0,
        "additional_contacts": 0,
        "dba_rows": 0,
        "skipped_rows": 0,
    }

    current_category = "Unknown"
    members: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for _, raw_row in df.iterrows():
        row = [_clean(v) for v in raw_row.tolist()]
        parsed = _align_row(row)
        if parsed is None:
            stats["skipped_rows"] += 1
            continue

        kind = parsed.get("kind")
        if kind == "section":
            current_category = parsed["category"]
            stats["sections_found"] += 1
            continue

        if kind == "additional" and current is not None:
            current["contact_count"] += 1
            if parsed.get("opted_out"):
                current["opted_out"] = True
            if parsed.get("bounced"):
                current["bounced"] = True
            stats["additional_contacts"] += 1
            continue

        if kind == "dba" and current is not None:
            dba = _clean(parsed.get("dba_name", ""))
            if dba:
                current["dba_names"].append(dba)
            website = _normalize_website(parsed.get("website", ""))
            if website and not current.get("website"):
                current["website"] = website
            stats["dba_rows"] += 1
            continue

        if kind == "member":
            if current is not None:
                members.append(current)

            member_name = parsed["member_name"]
            county = _derive_county(parsed["city"], parsed["zip"])
            website = parsed["website"]
            current = {
                "member_id": _make_member_id(member_name, current_category),
                "member_name": member_name,
                "category": current_category,
                "industry": INDUSTRY_MAP.get(current_category, current_category.title()),
                "membership_type": parsed["membership_type"]
                if parsed["membership_type"] in MEMBERSHIP_TYPES
                else ("Unknown" if not parsed["membership_type"] else parsed["membership_type"]),
                "website": website,
                "renewal": parsed["renewal"],
                "renewal_month": _parse_renewal_month(parsed["renewal"]),
                "primary_contact": parsed["primary_contact"],
                "job_title": parsed["job_title"],
                "email": parsed["email"],
                "phone": parsed["phone"],
                "address": parsed["address"],
                "city": parsed["city"],
                "zip": parsed["zip"],
                "county": county,
                "region": _derive_region(county),
                "contact_count": 0,
                "dba_names": [],
                "opted_out": parsed["opted_out"],
                "bounced": parsed["bounced"],
                "has_website": bool(website),
            }
            stats["primary_members"] += 1
            continue

        stats["skipped_rows"] += 1

    if current is not None:
        members.append(current)

    result = pd.DataFrame(members)
    if result.empty:
        return result, stats

    result["dba_names"] = result["dba_names"].apply(
        lambda names: "; ".join(names) if isinstance(names, list) else _clean(names)
    )
    result["size_band"] = result.apply(
        lambda r: _derive_size_band(
            int(r["contact_count"]),
            bool(_clean(r["primary_contact"])),
        ),
        axis=1,
    )
    result["opted_out"] = result["opted_out"].astype(bool)
    result["bounced"] = result["bounced"].astype(bool)
    result["has_website"] = result["has_website"].astype(bool)
    result["contact_count"] = result["contact_count"].astype(int)

    for col in STANDARD_COLUMNS:
        if col not in result.columns:
            result[col] = ""

    return result[STANDARD_COLUMNS], stats


def _is_preprocessed(df: pd.DataFrame) -> bool:
    required = {"member_name", "category", "industry"}
    return required.issubset(set(df.columns))


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Apply normalization to an already-standardized members table."""
    df = df.copy()
    if "member_name" not in df.columns:
        return df

    for col in STANDARD_COLUMNS:
        if col not in df.columns:
            if col in {"opted_out", "bounced", "has_website"}:
                df[col] = False
            elif col == "contact_count":
                df[col] = 0
            else:
                df[col] = ""

    for col in STANDARD_COLUMNS:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).replace({"nan": "", "None": ""})

    if "website" in df.columns:
        df["website"] = df["website"].apply(_normalize_website)
        df["has_website"] = df["website"].str.len() > 0

    if "zip" in df.columns:
        df["zip"] = df["zip"].apply(_normalize_zip)

    if "renewal" in df.columns and "renewal_month" in df.columns:
        df["renewal_month"] = df["renewal"].apply(_parse_renewal_month)

    if "county" not in df.columns or df["county"].eq("").all():
        df["county"] = df.apply(lambda r: _derive_county(r.get("city", ""), r.get("zip", "")), axis=1)

    if "region" not in df.columns or df["region"].eq("").all():
        df["region"] = df["county"].apply(_derive_region)

    if "size_band" not in df.columns or df["size_band"].eq("").all():
        df["size_band"] = df.apply(
            lambda r: _derive_size_band(
                int(r.get("contact_count", 0) or 0),
                bool(_clean(r.get("primary_contact", ""))),
            ),
            axis=1,
        )

    def _to_bool(val: Any) -> bool:
        if isinstance(val, bool):
            return val
        return str(val).lower().strip() in {"true", "1", "yes"}

    for bool_col in ("opted_out", "bounced", "has_website"):
        if bool_col in df.columns:
            df[bool_col] = df[bool_col].map(_to_bool)

    if "contact_count" in df.columns:
        df["contact_count"] = pd.to_numeric(df["contact_count"], errors="coerce").fillna(0).astype(int)

    if "member_id" not in df.columns or df["member_id"].eq("").all():
        df["member_id"] = df.apply(
            lambda r: _make_member_id(str(r["member_name"]), str(r.get("category", ""))),
            axis=1,
        )

    if "industry" not in df.columns or df["industry"].eq("").all():
        df["industry"] = df["category"].map(INDUSTRY_MAP).fillna(df["category"])

    return df[STANDARD_COLUMNS]


def _read_raw_file(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".xlsx":
        return pd.read_excel(path, sheet_name=0, header=None, dtype=str)
    return pd.read_csv(path, header=None, dtype=str, keep_default_na=False)


def find_member_file() -> Path | None:
    for candidate in MEMBER_FILE_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def load_members(source: Path | None = None) -> tuple[pd.DataFrame, Path | None, dict[str, int]]:
    """Load members from the best available file and return cleaned data with stats."""
    path = source or find_member_file()
    if path is None:
        return pd.DataFrame(columns=STANDARD_COLUMNS), None, {"error": 1}

    raw = _read_raw_file(path)

    if path.name.lower() in {"members.csv", "members.xlsx"}:
        probe = pd.read_csv(path, nrows=1) if path.suffix.lower() == ".csv" else pd.read_excel(path, nrows=1)
        if _is_preprocessed(probe):
            df = pd.read_csv(path, dtype=str) if path.suffix.lower() == ".csv" else pd.read_excel(path, dtype=str)
            return normalize_dataframe(df), path, {"rows_read": len(df), "primary_members": len(df)}

    df, stats = parse_master_list(raw)
    return df, path, stats


def save_members_csv(df: pd.DataFrame, output: Path | None = None) -> Path:
    output = output or DATA_DIR / "members.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    return output