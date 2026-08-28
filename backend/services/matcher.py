"""
matcher.py  —  Fuzzy matching engine + confidence scoring

Responsible for:
- Taking a structured address (from the parser)
- Fetching broad candidates from db.py
- Scoring each candidate with RapidFuzz
- Returning ranked candidates with scores and explanations

CONFIDENCE FORMULA (heuristic, not a scientific probability):
  Field             Weight    Notes
  ──────────────────────────────────────────────────────────
  locality match      35      strongest signal
  office_name match   25      post office name similarity
  district match      20      exact = full points, fuzzy = partial
  state match         15      exact = full points, fuzzy = partial
  pincode match        5      bonus if user supplied a PIN

  Raw score 0–100 is mapped to levels:
    80–100 → HIGH     (show single best result)
    60–79  → MEDIUM   (show top 3, ask user to verify)
    0–59   → LOW      (ask for more information)

This is clearly a HEURISTIC matching confidence score,
not a guaranteed probability of correctness.
"""

from rapidfuzz import fuzz
from typing import Optional
from services.db import search_candidates, get_all_records


# ─────────────────────────────────────────────
# Score weights  (must sum to 100)
# ─────────────────────────────────────────────
W_LOCALITY    = 35
W_OFFICE_NAME = 25
W_DISTRICT    = 20
W_STATE       = 15
W_PINCODE     =  5


def _fuzzy(a: Optional[str], b: Optional[str]) -> float:
    """
    Return a 0–100 similarity score between two strings.
    Returns 0 if either string is missing.
    Uses token_set_ratio which handles word-order differences well.
    """
    if not a or not b:
        return 0.0
    return fuzz.token_set_ratio(a.lower().strip(), b.lower().strip())


def _exact_or_fuzzy(a: Optional[str], b: Optional[str]) -> float:
    """
    Return 100 for exact match (case-insensitive), else fuzzy score.
    Used for district/state where exact is strongly preferred.
    """
    if not a or not b:
        return 0.0
    if a.lower().strip() == b.lower().strip():
        return 100.0
    return fuzz.token_set_ratio(a.lower().strip(), b.lower().strip())


def score_candidate(candidate: dict, structured: dict) -> tuple[float, list[str]]:
    """
    Score a single DB candidate against the parsed structured address.

    Returns:
        (score: float 0–100, explanation: list[str])
    """
    explanation: list[str] = []

    # ── locality ──────────────────────────────────────────────────────────────
    # Compare both locality field and office_name against the parsed locality
    parsed_locality = structured.get("locality") or structured.get("city") or ""
    db_locality     = candidate.get("locality", "")
    db_office       = candidate.get("office_name", "")

    locality_score = max(
        _fuzzy(parsed_locality, db_locality),
        _fuzzy(parsed_locality, db_office),
    )

    # ── office name ───────────────────────────────────────────────────────────
    parsed_landmark = structured.get("landmark", "")
    office_score = max(
        _fuzzy(parsed_locality, db_office),
        _fuzzy(parsed_landmark, db_office) if parsed_landmark else 0,
    )

    # ── district ──────────────────────────────────────────────────────────────
    district_score = _exact_or_fuzzy(
        structured.get("district", ""),
        candidate.get("district", "")
    )

    # ── state ─────────────────────────────────────────────────────────────────
    state_score = _exact_or_fuzzy(
        structured.get("state", ""),
        candidate.get("state", "")
    )

    # ── pincode bonus ─────────────────────────────────────────────────────────
    pincode_score = 0.0
    parsed_pin = structured.get("pincode", "")
    db_pin     = candidate.get("pincode", "")
    if parsed_pin and db_pin:
        pincode_score = 100.0 if parsed_pin.strip() == db_pin.strip() else 0.0

    # ── weighted total ────────────────────────────────────────────────────────
    total = (
        (locality_score    / 100) * W_LOCALITY    +
        (office_score      / 100) * W_OFFICE_NAME +
        (district_score    / 100) * W_DISTRICT    +
        (state_score       / 100) * W_STATE       +
        (pincode_score     / 100) * W_PINCODE
    )

    # ── build explanation ─────────────────────────────────────────────────────
    if locality_score >= 80:
        explanation.append(f"Locality matched ({db_locality})")
    elif locality_score >= 50:
        explanation.append(f"Locality partially matched ({db_locality})")

    if office_score >= 80:
        explanation.append(f"Post Office name matched ({db_office})")
    elif office_score >= 50:
        explanation.append(f"Post Office name partially matched ({db_office})")

    if district_score == 100:
        explanation.append(f"District matched ({candidate.get('district')})")
    elif district_score >= 60:
        explanation.append(f"District partially matched ({candidate.get('district')})")

    if state_score == 100:
        explanation.append(f"State matched ({candidate.get('state')})")
    elif state_score >= 60:
        explanation.append(f"State partially matched ({candidate.get('state')})")

    if parsed_pin and pincode_score == 100:
        explanation.append(f"Supplied PIN {parsed_pin} confirmed in database")
    elif parsed_pin and pincode_score == 0:
        explanation.append(f"Supplied PIN {parsed_pin} does not match database PIN {db_pin}")

    return round(total, 1), explanation


def confidence_level(score: float) -> str:
    """Map numeric score to a human-readable confidence level."""
    if score >= 80:
        return "high"
    elif score >= 60:
        return "medium"
    else:
        return "low"


def find_matches(structured: dict, top_n: int = 5) -> list[dict]:
    """
    Main entry point for the matching engine.

    Takes a structured address dict (output of the parser) and returns
    a list of ranked candidates, each with score and explanation.

    Each result dict contains:
        post_office, pincode, district, state, locality,
        confidence (int), explanation (list[str]), confidence_level (str)
    """
    # 1. Fetch broad candidates from DB
    candidates = search_candidates(
        locality = structured.get("locality") or structured.get("city"),
        district = structured.get("district"),
        state    = structured.get("state"),
        pincode  = structured.get("pincode"),
        limit    = 80,
    )

    # If filters returned nothing (very incomplete address), fall back to all records
    if not candidates:
        candidates = get_all_records(limit=200)

    if not candidates:
        return []

    # 2. Score every candidate
    scored: list[tuple[float, dict, list[str]]] = []
    for c in candidates:
        score, expl = score_candidate(c, structured)
        scored.append((score, c, expl))

    # 3. Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    # 4. Build result list
    results = []
    for score, c, expl in scored[:top_n]:
        results.append({
            "post_office":      c["office_name"],
            "pincode":          c["pincode"],
            "district":         c["district"],
            "state":            c["state"],
            "locality":         c["locality"],
            "office_type":      c.get("office_type", ""),
            "confidence":       int(score),
            "confidence_level": confidence_level(score),
            "explanation":      expl,
        })

    return results


def check_pin_mismatch(
    supplied_pin: str,
    best_match: dict,
) -> Optional[str]:
    """
    If the user supplied a PIN that differs from the matched record's PIN,
    return a warning string. Otherwise return None.
    """
    if not supplied_pin:
        return None
    db_pin = best_match.get("pincode", "")
    if supplied_pin.strip() != db_pin.strip():
        return (
            f"The supplied PIN {supplied_pin} does not match the "
            f"database PIN {db_pin} for {best_match.get('post_office', 'this Post Office')}."
        )
    return None
