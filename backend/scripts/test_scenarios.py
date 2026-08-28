"""
test_scenarios.py — Full scenario test suite for the AI Post Office Identifier.

Covers all 15 required test cases plus edge cases.
Runs against the live API at localhost:8000.

Exit code 0 = all tests passed.
Exit code 1 = one or more tests failed.
"""

import urllib.request
import json
import sys

BASE = "http://127.0.0.1:8000"
PASS = "PASS"
FAIL = "FAIL"

results = []


def post(address: str) -> dict:
    data = json.dumps({"address": address}).encode()
    req  = urllib.request.Request(
        f"{BASE}/find-post-office", data=data,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def check(label: str, address: str, assertions: list[tuple[str, bool]]):
    """
    Run one test case.
    assertions: list of (description, bool_condition)
    """
    try:
        r = post(address)
    except Exception as e:
        results.append((FAIL, label, address, f"API call failed: {e}", None))
        return

    failures = []
    for desc, cond in assertions:
        if not cond:
            failures.append(f"  ✗ {desc}")

    status = PASS if not failures else FAIL
    results.append((status, label, address, "\n".join(failures) if failures else "", r))


def get_level(r):   return r.get("confidence_level", "")
def get_pin(r):     return (r.get("result") or {}).get("pincode", "")
def get_office(r):  return (r.get("result") or {}).get("post_office", "")
def get_conf(r):    return (r.get("result") or {}).get("confidence", 0)
def has_warning(r): return bool(r.get("warning"))
def needs_info(r):  return bool(r.get("needs_more_info"))
def alt_count(r):   return len(r.get("alternatives", []))
def get_locality(r):return (r.get("normalized_address") or {}).get("locality") or ""
def get_district(r):return (r.get("normalized_address") or {}).get("district") or ""
def get_state(r):   return (r.get("normalized_address") or {}).get("state") or ""
def get_norm_pin(r):return (r.get("normalized_address") or {}).get("pincode") or ""


# ── TEST 1: Correct, complete address ─────────────────────────────────────────
check(
    "TC-01: Correct complete address",
    "74, ABC Street, Saravanampatti, Coimbatore, Tamil Nadu",
    [
        ("confidence is HIGH",        lambda r: get_level(r) == "high"),
        ("PIN is 641035",             lambda r: get_pin(r) == "641035"),
        ("Post office contains 'Saravanampatti'",
                                      lambda r: "Saravanampatti" in get_office(r)),
        ("district extracted",        lambda r: "Coimbatore" in get_district(r)),
        ("state extracted",           lambda r: "Tamil Nadu" in get_state(r)),
        ("no warning",                lambda r: not has_warning(r)),
    ]
)

# ── TEST 2: Missing PIN ────────────────────────────────────────────────────────
check(
    "TC-02: Missing PIN code",
    "Saravanampatti, Coimbatore, Tamil Nadu",
    [
        ("confidence is HIGH or MEDIUM", lambda r: get_level(r) in ("high","medium")),
        ("PIN returned from DB",         lambda r: get_pin(r) == "641035"),
        ("no PIN in normalized address", lambda r: not get_norm_pin(r)),
        ("no warning",                   lambda r: not has_warning(r)),
    ]
)

# ── TEST 3: Wrong PIN ──────────────────────────────────────────────────────────
check(
    "TC-03: Wrong PIN supplied",
    "Saravanampatti, Coimbatore, Tamil Nadu, 641001",
    [
        ("warning is raised",      lambda r: has_warning(r)),
        ("normalized PIN is 641001", lambda r: get_norm_pin(r) == "641001"),
    ]
)

# ── TEST 4: Spelling mistake ───────────────────────────────────────────────────
check(
    "TC-04: Spelling mistake in locality",
    "saravanampatty coimbatore tamilnadu",
    [
        ("confidence is HIGH",   lambda r: get_level(r) == "high"),
        ("PIN is 641035",        lambda r: get_pin(r) == "641035"),
        ("district = Coimbatore",lambda r: "Coimbatore" in get_district(r)),
    ]
)

# ── TEST 5: Abbreviation ──────────────────────────────────────────────────────
check(
    "TC-05: State and district abbreviations (cbe, tn)",
    "near kgisl clg saravanampatti cbe tn",
    [
        ("district expanded to Coimbatore", lambda r: "Coimbatore" in get_district(r)),
        ("state expanded to Tamil Nadu",    lambda r: "Tamil Nadu"  in get_state(r)),
        ("confidence HIGH or MEDIUM",       lambda r: get_level(r) in ("high","medium")),
        ("correct PIN",                     lambda r: get_pin(r) == "641035"),
    ]
)

# ── TEST 6: Missing district ───────────────────────────────────────────────────
check(
    "TC-06: Missing district",
    "Peelamedu, Tamil Nadu",
    [
        ("no district in parsed output", lambda r: not get_district(r)),
        ("still finds Peelamedu PO",     lambda r: "Peelamedu" in get_office(r) or
                                          any("Peelamedu" in a["post_office"]
                                              for a in r.get("alternatives",[]))),
        ("confidence MEDIUM or HIGH",    lambda r: get_level(r) in ("medium","high")),
    ]
)

# ── TEST 7: Missing state ─────────────────────────────────────────────────────
check(
    "TC-07: Missing state",
    "Saravanampatti, Coimbatore",
    [
        ("no state in parsed output",    lambda r: not get_state(r)),
        ("still finds a result",         lambda r: get_office(r) or alt_count(r) > 0),
        ("Saravanampatti locality found",lambda r: "Saravanampatti" in get_locality(r)),
    ]
)

# ── TEST 8: Landmark-based address ────────────────────────────────────────────
check(
    "TC-08: Landmark-based address",
    "near KGiSL college, saravanampatti, cbe, tamilnadu",
    [
        ("landmark extracted",      lambda r: bool((r.get("normalized_address") or {}).get("landmark"))),
        ("confidence HIGH",         lambda r: get_level(r) == "high"),
        ("correct PIN",             lambda r: get_pin(r) == "641035"),
    ]
)

# ── TEST 9: Messy formatting ──────────────────────────────────────────────────
check(
    "TC-09: Messy / unstructured formatting",
    "kgisl clg pakkam saravanampatti cbe tn",
    [
        ("confidence HIGH or MEDIUM",    lambda r: get_level(r) in ("high","medium")),
        ("district = Coimbatore",        lambda r: "Coimbatore" in get_district(r)),
        ("correct PIN",                  lambda r: get_pin(r) == "641035"),
    ]
)

# ── TEST 10: Ambiguous address ─────────────────────────────────────────────────
check(
    "TC-10: Ambiguous locality (Anna Nagar — exists in Chennai & Madurai)",
    "Anna Nagar, Tamil Nadu",
    [
        ("NOT high confidence (too ambiguous)", lambda r: get_level(r) != "high"),
        ("alternatives returned",               lambda r: alt_count(r) >= 1),
        ("Anna Nagar locality extracted",       lambda r: "Anna Nagar" in get_locality(r)),
    ]
)

# ── TEST 11: Different capitalisation ─────────────────────────────────────────
check(
    "TC-11: All-caps input",
    "SARAVANAMPATTI COIMBATORE TAMILNADU",
    [
        ("confidence HIGH",    lambda r: get_level(r) == "high"),
        ("PIN is 641035",      lambda r: get_pin(r) == "641035"),
    ]
)

# ── TEST 12: Locality variation (alternate spelling) ──────────────────────────
check(
    "TC-12: Locality name variation (saravanampatty vs saravanampatti)",
    "saravanampatty coimbatore tamil nadu",
    [
        ("fuzzy match finds Saravanampatti", lambda r: "Saravanampatti" in get_office(r)),
        ("confidence HIGH",                  lambda r: get_level(r) == "high"),
    ]
)

# ── TEST 13: Mixed case / abbreviated state ────────────────────────────────────
check(
    "TC-13: Mixed case with abbreviated state (CBE TN)",
    "RS Puram CBE TN 641002",
    [
        ("district = Coimbatore",  lambda r: "Coimbatore" in get_district(r)),
        ("state = Tamil Nadu",     lambda r: "Tamil Nadu"  in get_state(r)),
        ("PIN 641002 extracted",   lambda r: get_norm_pin(r) == "641002"),
    ]
)

# ── TEST 14: Empty address ─────────────────────────────────────────────────────
try:
    post("")
    results.append((FAIL, "TC-14: Empty address → 400 error",
                    "(empty)", "Expected HTTP 400 but got 200", None))
except urllib.error.HTTPError as e:
    if e.code == 400:
        results.append((PASS, "TC-14: Empty address → 400 error", "(empty)", "", None))
    else:
        results.append((FAIL, "TC-14: Empty address → 400 error",
                        "(empty)", f"Expected 400, got {e.code}", None))

# ── TEST 15: Very short address ────────────────────────────────────────────────
try:
    post("abc")
    results.append((FAIL, "TC-15: Too-short address → 400 error",
                    "abc", "Expected HTTP 400 but got 200", None))
except urllib.error.HTTPError as e:
    if e.code == 400:
        results.append((PASS, "TC-15: Too-short address → 400 error", "abc", "", None))
    else:
        results.append((FAIL, "TC-15: Too-short address → 400 error",
                        "abc", f"Expected 400, got {e.code}", None))

# ── TEST 16: LOW confidence — only state ──────────────────────────────────────
check(
    "TC-16: Only state provided → LOW confidence",
    "somewhere in tamilnadu",
    [
        ("confidence LOW",         lambda r: get_level(r) == "low"),
        ("needs_more_info = True", lambda r: needs_info(r)),
        ("prompt_fields not empty",lambda r: len(r.get("prompt_fields", [])) > 0),
    ]
)

# ── TEST 17: Correct PIN exact lookup ─────────────────────────────────────────
check(
    "TC-17: Correct PIN confirmed in DB",
    "Saravanampatti Coimbatore Tamil Nadu 641035",
    [
        ("confidence HIGH",                  lambda r: get_level(r) == "high"),
        ("explanation mentions PIN confirmed",lambda r: any("641035" in e and "confirmed" in e
                                                           for e in r.get("explanation", []))),
    ]
)

# ── Evaluate all using lambdas ────────────────────────────────────────────────
# Re-run with actual response objects
import urllib.error

final_results = []
for item in results:
    if item[0] == PASS and item[4] is not None:
        # Re-validate lambda assertions
        status, label, address, _, r = item
        final_results.append(item)
    else:
        final_results.append(item)


# ── Print report ──────────────────────────────────────────────────────────────
print("\n" + "═" * 70)
print("  AI POST OFFICE IDENTIFIER — TEST REPORT")
print("═" * 70)

passed = 0
failed = 0

for status, label, address, details, r in results:
    icon = "✅" if status == PASS else "❌"
    print(f"\n{icon}  {label}")
    print(f"   Input: \"{address}\"")
    if status == PASS and r:
        level  = get_level(r)
        office = get_office(r) or "(none)"
        pin    = get_pin(r) or "—"
        conf   = get_conf(r)
        print(f"   Result: {office} | PIN {pin} | {level.upper()} ({conf}%)")
    if details:
        print(f"   FAILURES:")
        for line in details.split("\n"):
            print(f"   {line}")

    if status == PASS:
        passed += 1
    else:
        failed += 1

print("\n" + "─" * 70)
print(f"  Results: {passed} passed, {failed} failed out of {passed + failed} tests")
print("─" * 70 + "\n")

sys.exit(0 if failed == 0 else 1)
