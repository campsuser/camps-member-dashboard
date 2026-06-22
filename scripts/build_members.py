"""Build a clean members.csv from the CAMPS master member list."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.constants import DATA_DIR
from src.data_loader import find_member_file, load_members, save_members_csv


def main() -> int:
    master = DATA_DIR / "Master Member List - 2026 Master List.csv"
    source = master if master.exists() else find_member_file()
    if source is None:
        print("No member source file found in data/.")
        return 1

    df, _, stats = load_members(source)
    if df.empty:
        print(f"Parsing produced 0 members from {source.name}.")
        return 1

    output = save_members_csv(df)
    print(f"Wrote {len(df)} members to {output}")
    print(f"Stats: {stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())