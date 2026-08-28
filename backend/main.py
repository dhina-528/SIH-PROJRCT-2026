"""
AI-Powered Delivery Post Office Identification System
Backend — main.py

Architecture:
  Raw Address
    → address_parser.py  (AI or fallback rule-based)
    → structured fields
    → matcher.py         (RapidFuzz + SQLite)
    → ranked candidates
    → confidence scoring
    → response

The LLM is used ONLY for address understanding.
All PIN codes and postal facts come exclusively from the SQLite database.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os

import os
import logging

from services.address_parser import parse_address, llm_available
from services.matcher import find_matches, check_pin_mismatch

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _log_startup_info():
    mode = "LLM (OpenAI gpt-4o-mini)" if llm_available() else "Rule-based fallback (no API key)"
    logger.info(f"Address parser mode: {mode}")


_log_startup_info()

app = FastAPI(
    title="AI Post Office Identifier",
    description=(
        "Hackathon MVP: Takes a messy Indian postal address, "
        "understands it using AI/NLP, searches a postal dataset, "
        "and returns the most likely Post Office and PIN code.\n\n"
        "**Data note:** Uses a prototype dataset. "
        "Not connected to official India Post systems."
    ),
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────

class AddressRequest(BaseModel):
    address: str


class NormalizedAddress(BaseModel):
    landmark: str | None = None
    locality:  str | None = None
    city:      str | None = None
    district:  str | None = None
    state:     str | None = None
    pincode:   str | None = None


class PostOfficeResult(BaseModel):
    post_office:  str
    pincode:      str
    district:     str
    state:        str
    locality:     str
    office_type:  str | None = None
    confidence:   int


class AddressResponse(BaseModel):
    input_address:     str
    normalized_address: NormalizedAddress
    parser_used:       str          # "llm" or "fallback"
    result:            PostOfficeResult | None = None
    confidence_level:  str          # "high" | "medium" | "low"
    explanation:       list[str]
    alternatives:      list[PostOfficeResult]
    warning:           str | None = None
    needs_more_info:   bool = False
    prompt_fields:     list[str]    # fields to ask user for when LOW


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.get("/", summary="Health check")
def health_check():
    return {
        "status":  "ok",
        "message": "AI Post Office Identifier backend is running.",
        "docs":    "/docs",
        "version": "0.2.0",
    }


@app.get("/parser-status", summary="Show which address parser is active")
def parser_status():
    """
    Returns which address parser is currently active.

    - **llm**: OpenAI API key is configured; addresses are parsed by GPT-4o-mini.
    - **fallback**: No API key; addresses are parsed by the built-in rule-based parser.

    The application works correctly in both modes.
    """
    if llm_available():
        return {
            "parser":      "llm",
            "model":       "gpt-4o-mini",
            "description": "AI address parser active (OpenAI API key configured).",
            "fallback_available": True,
        }
    return {
        "parser":      "fallback",
        "model":       None,
        "description": (
            "Rule-based fallback parser active. "
            "Set OPENAI_API_KEY in backend/.env to enable the AI parser."
        ),
        "fallback_available": True,
    }


@app.post(
    "/find-post-office",
    response_model=AddressResponse,
    summary="Identify Post Office from address",
)
def find_post_office(request: AddressRequest):
    """
    Takes a raw (possibly messy) Indian postal address and returns:
    - Normalized/structured address fields
    - Best matching Post Office and PIN code
    - Confidence level (HIGH / MEDIUM / LOW)
    - Explanation of why this result was selected
    - Alternatives when confidence is not high
    - Warning if user-supplied PIN does not match the database
    - Prompt for more information when confidence is low

    **Confidence levels** (heuristic scores, not guaranteed probabilities):
    - HIGH (80–100): One best result shown
    - MEDIUM (60–79): Top candidates shown, user asked to verify
    - LOW (<60): Insufficient information, user asked for more details
    """
    address = request.address.strip()

    # ── Input validation ──────────────────────────────────────────────────────
    if not address:
        raise HTTPException(status_code=400, detail="Address cannot be empty.")
    if len(address) < 5:
        raise HTTPException(
            status_code=400,
            detail="Address is too short. Please provide more details such as locality, district, or state.",
        )

    # ── Step 1: Parse / normalize the address ────────────────────────────────
    try:
        structured, parser_used = parse_address(address)
    except Exception as e:
        # Parser crashed — treat as fallback with empty structure
        structured  = {"landmark": None, "locality": None, "city": None,
                       "district": None, "state": None, "pincode": None}
        parser_used = "fallback"

    normalized = NormalizedAddress(
        landmark = structured.get("landmark"),
        locality  = structured.get("locality"),
        city      = structured.get("city"),
        district  = structured.get("district"),
        state     = structured.get("state"),
        pincode   = structured.get("pincode"),
    )

    # ── Step 2: Find matches ──────────────────────────────────────────────────
    try:
        matches = find_matches(structured, top_n=5)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Postal database unavailable: {str(e)}. "
                   "Ensure postal.db exists. Run: python scripts/import_data.py",
        )

    # ── Step 3: No matches at all ─────────────────────────────────────────────
    if not matches:
        return AddressResponse(
            input_address      = address,
            normalized_address = normalized,
            parser_used        = parser_used,
            result             = None,
            confidence_level   = "low",
            explanation        = ["No matching postal records found for this address."],
            alternatives       = [],
            warning            = None,
            needs_more_info    = True,
            prompt_fields      = _missing_fields(structured),
        )

    best       = matches[0]
    top_score  = best["confidence"]
    level      = best["confidence_level"]

    # ── Step 4: Wrong PIN detection ───────────────────────────────────────────
    # If the user supplied a PIN, find what the DB says the correct PIN
    # should be for this locality (by re-running match without the PIN filter),
    # then warn if it differs from the user's supplied PIN.
    warning = None
    user_pin = structured.get("pincode")
    if user_pin:
        # Find the best locality match without the PIN constraint
        structured_no_pin = {**structured, "pincode": None}
        locality_matches = find_matches(structured_no_pin, top_n=1)
        if locality_matches:
            expected_pin = locality_matches[0]["pincode"]
            if expected_pin and expected_pin != user_pin:
                warning = (
                    f"The supplied PIN {user_pin} does not match the expected PIN "
                    f"{expected_pin} for {locality_matches[0]['post_office']}. "
                    f"Please verify the correct PIN code."
                )

    # ── Step 5: Build response based on confidence level ─────────────────────

    def _to_result(m: dict) -> PostOfficeResult:
        return PostOfficeResult(
            post_office = m["post_office"],
            pincode     = m["pincode"],
            district    = m["district"],
            state       = m["state"],
            locality    = m["locality"],
            office_type = m.get("office_type"),
            confidence  = m["confidence"],
        )

    if level == "high":
        # Single confident result — no alternatives needed
        return AddressResponse(
            input_address      = address,
            normalized_address = normalized,
            parser_used        = parser_used,
            result             = _to_result(best),
            confidence_level   = "high",
            explanation        = best["explanation"],
            alternatives       = [],
            warning            = warning,
            needs_more_info    = False,
            prompt_fields      = [],
        )

    elif level == "medium":
        # Show top result + alternatives, ask user to confirm
        alternatives = [_to_result(m) for m in matches[1:4]]
        explanation  = best["explanation"] + [
            "Multiple possible matches found — please verify the correct one."
        ]
        return AddressResponse(
            input_address      = address,
            normalized_address = normalized,
            parser_used        = parser_used,
            result             = _to_result(best),
            confidence_level   = "medium",
            explanation        = explanation,
            alternatives       = alternatives,
            warning            = warning,
            needs_more_info    = False,
            prompt_fields      = [],
        )

    else:
        # LOW — don't confidently recommend; ask for more info
        top_candidates = [_to_result(m) for m in matches[:3]]
        missing = _missing_fields(structured)
        explanation = best["explanation"] + [
            "Confidence is too low to recommend a single Post Office.",
            "Please provide additional details.",
        ]
        return AddressResponse(
            input_address      = address,
            normalized_address = normalized,
            parser_used        = parser_used,
            result             = None,           # no confident recommendation
            confidence_level   = "low",
            explanation        = explanation,
            alternatives       = top_candidates, # still show what we found
            warning            = warning,
            needs_more_info    = True,
            prompt_fields      = missing,
        )


def _missing_fields(structured: dict) -> list[str]:
    """Return a list of address fields that were not extracted, for prompting the user."""
    missing = []
    if not structured.get("locality") and not structured.get("city"):
        missing.append("locality or area name")
    if not structured.get("district"):
        missing.append("district")
    if not structured.get("state"):
        missing.append("state")
    if not structured.get("pincode"):
        missing.append("PIN code (if known)")
    return missing
