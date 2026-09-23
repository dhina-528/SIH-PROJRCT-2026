"""
db.py  —  Database access layer

Responsible for:
- Opening / closing the SQLite connection
- Fetching broad candidate records that could match a structured address
- Pincode lookup (for wrong-PIN detection)

It does NOT do fuzzy matching — that's matcher.py's job.
This layer just fetches rows from the database efficiently.
"""

import sqlite3
import os
from typing import Optional

# postal.db lives one level up from services/
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "postal.db")


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with row_factory set so rows behave like dicts."""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            f"Database not found at {DB_PATH}. "
            "Run: python scripts/import_data.py"
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # lets us do row["office_name"] instead of row[0]
    return conn


def row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a sqlite3.Row to a plain dict."""
    return dict(row)


def search_candidates(
    locality:  Optional[str] = None,
    district:  Optional[str] = None,
    state:     Optional[str] = None,
    pincode:   Optional[str] = None,
    limit:     int = 50,
) -> list[dict]:
    """
    Pull candidate postal records from the database.

    Strategy: cast a reasonably wide net so the fuzzy matcher has good material
    to work with.  We filter by state first (most selective for large datasets),
    then optionally by district or pincode.

    Returns a list of dicts, each representing one postal_offices row.
    Returns empty list if DB is unavailable.
    """
    try:
        conn = get_connection()
        cur  = conn.cursor()

        params: list = []
        clauses: list[str] = []

        # Pincode is the strongest signal — if the user supplied one, use it
        # as the primary filter and return results for that pincode only.
        if pincode:
            clauses.append("pincode = ?")
            params.append(pincode)

        # Locality is a strong signal and should narrow the search before fuzzy scoring.
        if locality:
            clauses.append("LOWER(locality) LIKE ?")
            params.append(f"%{locality.lower()}%")

        # State narrows the search significantly
        if state:
            clauses.append("LOWER(state) LIKE ?")
            params.append(f"%{state.lower()}%")

        # District further narrows
        if district:
            clauses.append("LOWER(district) LIKE ?")
            params.append(f"%{district.lower()}%")

        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""

        sql = f"""
            SELECT id, office_name, pincode, district, state,
                   locality, office_type, delivery, division, region, circle
            FROM postal_offices
            {where_sql}
            LIMIT ?
        """
        params.append(limit)
        cur.execute(sql, params)
        rows = [row_to_dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    except FileNotFoundError as e:
        print(f"[db.py] WARNING: {e}")
        return []
    except sqlite3.Error as e:
        print(f"[db.py] SQLite error: {e}")
        return []


def search_by_pincode(pincode: str) -> list[dict]:
    """
    Return all postal offices that match an exact pincode.
    Used for wrong-PIN detection.
    """
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute(
            "SELECT * FROM postal_offices WHERE pincode = ?",
            (pincode,)
        )
        rows = [row_to_dict(r) for r in cur.fetchall()]
        conn.close()
        return rows
    except (FileNotFoundError, sqlite3.Error) as e:
        print(f"[db.py] search_by_pincode error: {e}")
        return []


def get_all_records(limit: int = 500) -> list[dict]:
    """
    Fallback: return a broad sample of all records when no filters
    match anything.  Used when state/district extraction failed completely.
    """
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute(
            "SELECT * FROM postal_offices ORDER BY state, district LIMIT ?",
            (limit,)
        )
        rows = [row_to_dict(r) for r in cur.fetchall()]
        conn.close()
        return rows
    except (FileNotFoundError, sqlite3.Error) as e:
        print(f"[db.py] get_all_records error: {e}")
        return []
