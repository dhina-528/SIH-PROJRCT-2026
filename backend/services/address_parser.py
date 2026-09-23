"""
address_parser.py  —  Address understanding / normalization service

Responsible for taking a raw messy address string and extracting:
  - landmark
  - locality
  - city
  - district
  - state
  - pincode

TWO MODES:
  1. LLM parser  — uses OpenAI if OPENAI_API_KEY is set in .env
  2. Fallback parser — pure Python rule-based, no API needed

The application works fully without an API key.
The LLM is used ONLY for understanding/normalization.
It is NEVER used as a source for PIN codes.
If the LLM response contains a pincode that was not in the original input,
that pincode is discarded.

IMPORTANT: The LLM may not invent a PIN. If a PIN is not explicitly
present in the raw input, the pincode field is always None.
"""

import re
import os
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Abbreviation / alias maps
# These are the core of the fallback parser.
# ─────────────────────────────────────────────────────────────────────────────

STATE_ALIASES: dict[str, str] = {
    # Tamil Nadu
    "tn": "Tamil Nadu", "tamilnadu": "Tamil Nadu", "tamil nadu": "Tamil Nadu",
    "tamilnad": "Tamil Nadu", "t.n": "Tamil Nadu", "t.n.": "Tamil Nadu",
    # Karnataka
    "ka": "Karnataka", "karnataka": "Karnataka", "kk": "Karnataka",
    # Kerala
    "kl": "Kerala", "kerala": "Kerala",
    # Andhra Pradesh
    "ap": "Andhra Pradesh", "andhra": "Andhra Pradesh", "andhra pradesh": "Andhra Pradesh",
    # Telangana
    "tg": "Telangana", "telangana": "Telangana",
    # Maharashtra
    "mh": "Maharashtra", "maharashtra": "Maharashtra",
    # Gujarat
    "gj": "Gujarat", "gujarat": "Gujarat",
    # Rajasthan
    "rj": "Rajasthan", "rajasthan": "Rajasthan",
    # Uttar Pradesh
    "up": "Uttar Pradesh", "uttar pradesh": "Uttar Pradesh",
    # West Bengal
    "wb": "West Bengal", "west bengal": "West Bengal",
    # Delhi
    "dl": "Delhi", "delhi": "Delhi", "new delhi": "Delhi",
    # Punjab
    "pb": "Punjab", "punjab": "Punjab",
    # Haryana
    "hr": "Haryana", "haryana": "Haryana",
    # Madhya Pradesh
    "mp": "Madhya Pradesh", "madhya pradesh": "Madhya Pradesh",
    # Bihar
    "br": "Bihar", "bihar": "Bihar",
    # Odisha
    "od": "Odisha", "odisha": "Odisha", "orissa": "Odisha",
    # Assam
    "as": "Assam", "assam": "Assam",
}

DISTRICT_ALIASES: dict[str, str] = {
    # Coimbatore
    "cbe": "Coimbatore", "coimbatore": "Coimbatore", "kovai": "Coimbatore",
    "coimbatoor": "Coimbatore", "coimbatore dt": "Coimbatore",
    # Chennai
    "mds": "Chennai", "madras": "Chennai", "chennai": "Chennai",
    # Madurai
    "madurai": "Madurai", "mdu": "Madurai",
    # Salem
    "salem": "Salem",
    # Tiruchirappalli
    "trichy": "Tiruchirappalli", "tiruchirappalli": "Tiruchirappalli",
    "tiruchi": "Tiruchirappalli",
    # Tiruppur
    "tiruppur": "Tiruppur", "tirupur": "Tiruppur",
    # Erode
    "erode": "Erode",
    # Vellore
    "vellore": "Vellore",
    # Bengaluru
    "bangalore": "Bengaluru", "bengaluru": "Bengaluru", "blr": "Bengaluru",
    "bengalore": "Bengaluru",
    # Mumbai
    "mumbai": "Mumbai", "bombay": "Mumbai",
    # Pune
    "pune": "Pune",
    # Hyderabad
    "hyderabad": "Hyderabad", "hyd": "Hyderabad",
}

# Landmark keywords — phrases that signal what follows is a landmark
LANDMARK_PREFIXES = [
    "near", "opp", "opposite", "behind", "beside", "next to",
    "adj", "adjacent", "in front of", "close to", "landmark",
    "nr ", "b/w", "between",
]

# Words/tokens that should be stripped as noise
NOISE_TOKENS = {
    "post", "office", "po", "p.o", "p.o.", "pin", "pin:", "pincode",
    "dist", "dist.", "district", "state", "taluk", "mandal",
    "via", "at", "the", "and", "a", "an", "&", "-", ",", ".",
}

# Known multi-word locality names that contain short tokens (like "T Nagar")
# Map lowercase → proper form
LOCALITY_ALIASES: dict[str, str] = {
    "t nagar": "T Nagar",
    "rs puram": "RS Puram",
    "r s puram": "RS Puram",
    "anna nagar": "Anna Nagar",
    "k k nagar": "KK Nagar",
    "kk nagar": "KK Nagar",
    "r a puram": "RA Puram",
    "ra puram": "RA Puram",
    "saravanampatty": "Saravanampatti",
    "saravanampatti": "Saravanampatti",
    "kgisl college": "KGiSL College",
    "kgisl clg": "KGiSL College",
    "kgisl": "KGiSL",
}


def _extract_pincode(text: str) -> tuple[Optional[str], str]:
    """
    Find a 6-digit number in the text — that's the PIN.
    Returns (pincode_or_None, text_with_pin_removed).
    """
    match = re.search(r"\b(\d{6})\b", text)
    if match:
        pin = match.group(1)
        cleaned = text[:match.start()] + text[match.end():]
        return pin, cleaned.strip()
    return None, text


def _normalize_text(text: str) -> str:
    """Lowercase, remove extra punctuation and whitespace."""
    text = text.lower()
    text = re.sub(r"[,;/\\|]", " ", text)   # commas → spaces
    text = re.sub(r"\.(?!\d)", " ", text)    # dots → spaces (but not in decimals)
    text = re.sub(r"\s+", " ", text)         # collapse whitespace
    return text.strip()


def _extract_landmark(text: str) -> tuple[Optional[str], str]:
    """
    If the text contains a landmark prefix (e.g. 'near', 'opp'),
    extract ONLY the next 1-2 words as the landmark to avoid swallowing
    the rest of the address (locality, district, state tokens).
    The remaining tokens after the landmark are returned in the cleaned text.
    Returns (landmark_or_None, text_with_landmark_prefix_removed).
    """
    for prefix in LANDMARK_PREFIXES:
        pattern = rf"\b{re.escape(prefix)}\s+([^,\n]+)"
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            full_phrase = m.group(1).strip()
            all_words = full_phrase.split()
            # Take only 2 words as the landmark name (e.g. "KGiSL College")
            # Return the rest back into the address text for district/state matching
            landmark_words = all_words[:2]
            remaining_words = all_words[2:]
            landmark = " ".join(landmark_words)
            for alias_key, alias_val in LOCALITY_ALIASES.items():
                if landmark.lower() == alias_key:
                    landmark = alias_val
                    break
            if landmark and not any(ch.isupper() for ch in landmark):
                landmark = landmark.title()
            if landmark.lower() == 'kgisl' and not landmark.startswith('KGiSL'):
                landmark = 'KGiSL'
            # Build cleaned text: text before match + remaining words + text after match
            before = text[:m.start()]
            after = text[m.end():]
            remainder = " ".join(remaining_words)
            cleaned = (before + " " + remainder + " " + after).strip()
            cleaned = re.sub(r"\s+", " ", cleaned)
            return landmark, cleaned
    return None, text


def _match_state(tokens: list[str]) -> tuple[Optional[str], list[str]]:
    """Check each token (and pairs of tokens) against STATE_ALIASES."""
    remaining = list(tokens)
    # Try two-word combinations first (e.g. "tamil nadu")
    for i in range(len(tokens) - 1):
        bigram = f"{tokens[i]} {tokens[i+1]}"
        if bigram in STATE_ALIASES:
            remaining = [t for j, t in enumerate(tokens) if j != i and j != i + 1]
            return STATE_ALIASES[bigram], remaining
    # Single token
    for i, token in enumerate(tokens):
        if token in STATE_ALIASES:
            remaining = [t for j, t in enumerate(tokens) if j != i]
            return STATE_ALIASES[token], remaining
    return None, tokens


def _match_district(tokens: list[str]) -> tuple[Optional[str], list[str]]:
    """Check each token against DISTRICT_ALIASES."""
    remaining = list(tokens)
    for i, token in enumerate(tokens):
        if token in DISTRICT_ALIASES:
            remaining = [t for j, t in enumerate(tokens) if j != i]
            return DISTRICT_ALIASES[token], remaining
    return None, tokens


def fallback_parse(raw_address: str) -> dict:
    """
    Rule-based address parser.
    Works without any API key.

    Strategy:
    1. Extract 6-digit PIN if present.
    2. Extract landmark phrases (near X, opp Y, etc.).
    3. Normalize the remaining text.
    4. Match known state and district abbreviations/aliases.
    5. Treat the longest remaining token as the locality.

    Returns a structured dict with keys:
      landmark, locality, city, district, state, pincode
    """
    # Step 1: extract PIN (must be done on original text before normalization)
    pincode, text = _extract_pincode(raw_address)

    # Step 2: extract landmark before normalization (preserves casing for title)
    landmark, text = _extract_landmark(text)

    # Step 3: normalize
    text = _normalize_text(text)

    # Step 3b: check for known multi-word locality aliases BEFORE tokenizing
    # (e.g. "T Nagar", "RS Puram" would otherwise lose their short prefix tokens)
    found_locality_alias: Optional[str] = None
    for alias_key, alias_val in LOCALITY_ALIASES.items():
        if alias_key in text:
            found_locality_alias = alias_val
            text = text.replace(alias_key, "")  # remove it so it doesn't pollute tokens
            break

    # Step 4: tokenize — split on whitespace
    tokens = [t.strip() for t in text.split() if t.strip() and t.strip() not in NOISE_TOKENS]

    # Step 5: match state
    state, tokens = _match_state(tokens)

    # Step 6: match district
    district, tokens = _match_district(tokens)

    # Step 7: what's left is likely locality/city
    # Filter out very short noise tokens, then join the remaining as the locality.
    # Multi-word localities like "Anna Nagar", "RS Puram", "T Nagar" are common
    # in Indian addresses, so we keep all meaningful tokens rather than picking one.
    locality_tokens = [t for t in tokens if len(t) >= 2]
    locality = None

    # Use the pre-extracted alias if found
    if found_locality_alias:
        locality = found_locality_alias
    elif locality_tokens:
        # If we have 1–3 tokens, join them (e.g. "anna nagar" → "Anna Nagar")
        # If we have many tokens, the longest single one is probably the place name
        if len(locality_tokens) <= 3:
            locality = " ".join(t.title() for t in locality_tokens)
        else:
            # Too many tokens — fall back to longest as best guess
            locality = max(locality_tokens, key=len).title()

    # city = same as locality for our purposes
    city = locality

    # Also: if landmark was extracted but locality is empty,
    # use the landmark text as a locality hint (it's a real place name)
    if not locality and landmark:
        locality = landmark
        city = locality

    return {
        "landmark": landmark,
        "locality": locality,
        "city":     city,
        "district": district,
        "state":    state,
        "pincode":  pincode,
    }


# ─────────────────────────────────────────────────────────────────────────────
# LLM parser (OpenAI)
# ─────────────────────────────────────────────────────────────────────────────

LLM_SYSTEM_PROMPT = """You are an Indian postal address parser.

Extract the following fields from the given address:
- landmark: any nearby landmark mentioned (e.g. "KGiSL College")
- locality: the specific area/locality name (e.g. "Saravanampatti")
- city: the city name (e.g. "Coimbatore")
- district: the district name (e.g. "Coimbatore")
- state: the full state name (e.g. "Tamil Nadu")
- pincode: ONLY if a 6-digit number is explicitly present in the input. Otherwise null.

CRITICAL RULES:
1. NEVER invent or guess a pincode. If no 6-digit number appears in the input, pincode must be null.
2. Expand abbreviations: "cbe" → "Coimbatore", "tn" → "Tamil Nadu", "blr" → "Bengaluru"
3. Fix obvious spelling mistakes in place names.
4. Return ONLY a valid JSON object with exactly these keys: landmark, locality, city, district, state, pincode
5. All values must be strings or null. No arrays, no extra keys.

Example input: "near kgisl clg saravanampatti cbe tn"
Example output:
{
  "landmark": "KGiSL College",
  "locality": "Saravanampatti",
  "city": "Coimbatore",
  "district": "Coimbatore",
  "state": "Tamil Nadu",
  "pincode": null
}"""


REQUIRED_LLM_KEYS = {"landmark", "locality", "city", "district", "state", "pincode"}


def llm_available() -> bool:
    """Return True if an OpenAI API key is configured."""
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def _call_openai(raw_address: str) -> Optional[dict]:
    """
    Call the OpenAI API to parse the address.
    Returns the parsed dict, or None if the call fails for any reason
    (missing key, network error, quota exceeded, bad response, etc.).
    The caller always falls back to the rule-based parser on None.
    """
    try:
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            return None

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": LLM_SYSTEM_PROMPT},
                {"role": "user",   "content": raw_address},
            ],
            temperature=0,
            max_tokens=200,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        parsed = json.loads(content)

        # Validate response has all expected keys
        if not REQUIRED_LLM_KEYS.issubset(parsed.keys()):
            missing_keys = REQUIRED_LLM_KEYS - parsed.keys()
            logger.warning(f"LLM response missing keys {missing_keys} — falling back.")
            return None

        # Ensure all values are either strings or None (no lists, dicts, etc.)
        for key in REQUIRED_LLM_KEYS:
            val = parsed[key]
            if val is not None and not isinstance(val, str):
                parsed[key] = str(val)

        # ── SAFETY RULE: LLM must never invent a PIN ──────────────────────────
        # Only accept a pincode if a 6-digit number was explicitly in the input.
        if parsed.get("pincode"):
            pin_in_input = re.search(r"\b\d{6}\b", raw_address)
            llm_pin = re.sub(r"\D", "", str(parsed["pincode"]))  # strip non-digits
            if not pin_in_input or pin_in_input.group() != llm_pin:
                logger.warning(
                    f"LLM invented pincode '{parsed['pincode']}' not found in input — discarding."
                )
                parsed["pincode"] = None

        logger.info("LLM parser succeeded.")
        return parsed

    except json.JSONDecodeError as e:
        logger.warning(f"LLM returned invalid JSON: {e} — falling back.")
        return None
    except Exception as e:
        logger.warning(f"LLM parser failed ({type(e).__name__}: {e}) — falling back.")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def parse_address(raw_address: str) -> tuple[dict, str]:
    """
    Parse a raw address string into structured fields.

    Tries the LLM parser first (if API key is available).
    Falls back to the rule-based parser automatically.

    Returns:
        (structured_address: dict, parser_used: str)
        parser_used is "llm" or "fallback"
    """
    raw_address = raw_address.strip()

    # Try LLM first
    llm_result = _call_openai(raw_address)
    if llm_result:
        return llm_result, "llm"

    # Fallback to rule-based parser
    result = fallback_parse(raw_address)
    return result, "fallback"
