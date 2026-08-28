"""
import_data.py

Reads a postal CSV file and populates the SQLite database (postal.db).

Usage:
    python scripts/import_data.py
    python scripts/import_data.py --csv data/my-custom-data.csv --db postal.db

The CSV must have at minimum these columns:
    office_name, pincode, district, state, locality

Optional columns (stored if present):
    office_type, delivery, division, region, circle

This script is safe to re-run — it drops and recreates the postal_offices table
each time, so you always get a clean import.

DATA NOTE:
    The default CSV (data/pincode-data.csv) is a PROTOTYPE/DEMO dataset.
    It is NOT the official India Post All India Pincode Directory.
    To use official data, download the CSV from:
    https://data.gov.in/resource/all-india-pincode-directory
    and pass it via --csv flag.
"""

import sqlite3
import csv
import argparse
import os
import sys

# Resolve paths relative to the backend/ directory,
# regardless of where this script is called from.
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CSV = os.path.join(BACKEND_DIR, "data", "pincode-data.csv")
DEFAULT_DB  = os.path.join(BACKEND_DIR, "postal.db")

# Columns we always expect in the CSV
REQUIRED_COLUMNS = {"office_name", "pincode", "district", "state", "locality"}

# Extra columns we store if present
OPTIONAL_COLUMNS = ["office_type", "delivery", "division", "region", "circle"]


def create_table(cursor: sqlite3.Cursor) -> None:
    """Create (or recreate) the postal_offices table."""
    cursor.execute("DROP TABLE IF EXISTS postal_offices")
    cursor.execute("""
        CREATE TABLE postal_offices (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            office_name TEXT    NOT NULL,
            pincode     TEXT    NOT NULL,
            district    TEXT    NOT NULL,
            state       TEXT    NOT NULL,
            locality    TEXT    NOT NULL,
            office_type TEXT,
            delivery    TEXT,
            division    TEXT,
            region      TEXT,
            circle      TEXT
        )
    """)
    # Index the columns we query/search against most frequently
    cursor.execute("CREATE INDEX idx_pincode  ON postal_offices(pincode)")
    cursor.execute("CREATE INDEX idx_district ON postal_offices(district)")
    cursor.execute("CREATE INDEX idx_state    ON postal_offices(state)")
    cursor.execute("CREATE INDEX idx_locality ON postal_offices(locality)")
    print("  Table 'postal_offices' created with indexes.")


def import_csv(csv_path: str, db_path: str) -> int:
    """
    Import records from csv_path into the SQLite database at db_path.
    Returns the number of rows imported.
    """
    if not os.path.exists(csv_path):
        print(f"ERROR: CSV file not found: {csv_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    create_table(cursor)

    rows_imported = 0
    rows_skipped  = 0

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        # Validate that required columns are present
        if reader.fieldnames is None:
            print("ERROR: CSV file is empty or unreadable.")
            sys.exit(1)

        actual_columns = set(c.strip().lower() for c in reader.fieldnames)
        missing = REQUIRED_COLUMNS - actual_columns
        if missing:
            print(f"ERROR: CSV is missing required columns: {missing}")
            sys.exit(1)

        for row in reader:
            # Normalize: strip whitespace, title-case name fields
            office_name = row.get("office_name", "").strip()
            pincode     = row.get("pincode", "").strip()
            district    = row.get("district", "").strip()
            state       = row.get("state", "").strip()
            locality    = row.get("locality", "").strip()

            # Skip obviously bad rows
            if not office_name or not pincode or not district or not state:
                rows_skipped += 1
                continue

            # Validate pincode is numeric and 6 digits
            if not pincode.isdigit() or len(pincode) != 6:
                rows_skipped += 1
                continue

            # Optional columns — default to empty string if not in CSV
            office_type = row.get("office_type", "").strip()
            delivery    = row.get("delivery",    "").strip()
            division    = row.get("division",    "").strip()
            region      = row.get("region",      "").strip()
            circle      = row.get("circle",      "").strip()

            cursor.execute("""
                INSERT INTO postal_offices
                    (office_name, pincode, district, state, locality,
                     office_type, delivery, division, region, circle)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (office_name, pincode, district, state, locality,
                  office_type, delivery, division, region, circle))

            rows_imported += 1

    conn.commit()
    conn.close()
    return rows_imported


def main():
    parser = argparse.ArgumentParser(
        description="Import postal CSV data into postal.db"
    )
    parser.add_argument("--csv", default=DEFAULT_CSV,
                        help=f"Path to CSV file (default: {DEFAULT_CSV})")
    parser.add_argument("--db",  default=DEFAULT_DB,
                        help=f"Path to SQLite database (default: {DEFAULT_DB})")
    args = parser.parse_args()

    print(f"\nImporting postal data")
    print(f"  CSV source : {args.csv}")
    print(f"  Database   : {args.db}")
    print()

    count = import_csv(args.csv, args.db)

    print(f"  Rows imported : {count}")
    print(f"\nDone. Database ready at: {args.db}")
    print("\nNOTE: The default dataset is a PROTOTYPE for demonstration purposes.")
    print("      It is NOT the official India Post Pincode Directory.")
    print("      For official data: https://data.gov.in/resource/all-india-pincode-directory\n")


if __name__ == "__main__":
    main()
