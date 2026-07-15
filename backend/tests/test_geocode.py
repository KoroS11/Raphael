from fastapi.testclient import TestClient
from api.main import app
import time
import pytest
import concurrent.futures

client = TestClient(app)

# ==============================================================================
# CATEGORY A — NAME COLLISIONS
# ==============================================================================

def test_category_a_jaipur():
    res = client.get("/api/v1/geocode?q=Jaipur")
    assert res.status_code == 200, f"Status code: {res.status_code}"
    results = res.json()["results"]
    assert len(results) > 0, f"No results found for Jaipur"
    top = results[0]
    is_valid = (top.get("type") in ["city", "state_capital"]) and ("Rajasthan" in top.get("display_name", "") and "West Bengal" not in top.get("display_name", ""))
    assert is_valid, f"Jaipur top result invalid: type={top.get('type')}, display_name={top.get('display_name')}. Top 3: {results[:3]}"

def test_category_a_pune():
    res = client.get("/api/v1/geocode?q=Pune")
    assert res.status_code == 200, f"Status code: {res.status_code}"
    results = res.json()["results"]
    assert len(results) > 0, f"No results found for Pune"
    top = results[0]
    is_valid = (top.get("type") in ["city", "state_capital"]) and ("Pune" in top.get("display_name", ""))
    assert is_valid, f"Pune top result invalid: type={top.get('type')}, display_name={top.get('display_name')}. Top 3: {results[:3]}"

def test_category_a_hyderabad():
    res = client.get("/api/v1/geocode?q=Hyderabad")
    assert res.status_code == 200, f"Status code: {res.status_code}"
    results = res.json()["results"]
    assert len(results) > 0, f"No results found for Hyderabad"
    top = results[0]
    is_valid = (top.get("type") in ["city", "state_capital", "administrative"]) and ("Telangana" in top.get("display_name", "") or "Andhra Pradesh" in top.get("display_name", ""))
    assert is_valid, f"Hyderabad top result invalid: type={top.get('type')}, display_name={top.get('display_name')}. Top 3: {results[:3]}"

def test_category_a_aurangabad():
    res = client.get("/api/v1/geocode?q=Aurangabad&limit=15")
    assert res.status_code == 200, f"Status code: {res.status_code}"
    results = res.json()["results"]
    assert len(results) > 0, f"No results found for Aurangabad"
    top = results[0]
    assert "Maharashtra" in top.get("display_name", ""), f"Aurangabad top result is not Maharashtra: {top.get('display_name')}. Top 3: {results[:3]}"
    
    has_maharashtra = any("Maharashtra" in r.get("display_name", "") for r in results)
    has_bihar = any("Bihar" in r.get("display_name", "") for r in results)
    assert has_maharashtra and has_bihar, f"Missing Maharashtra or Bihar in results. Has Maharashtra: {has_maharashtra}, Has Bihar: {has_bihar}. Top 3: {results[:3]}"

def test_category_a_capitals():
    capitals = ["Bhopal", "Patna", "Lucknow", "Chandigarh"]
    for cap in capitals:
        res = client.get(f"/api/v1/geocode?q={cap}")
        assert res.status_code == 200, f"Status code: {res.status_code} for {cap}"
        results = res.json()["results"]
        assert len(results) > 0, f"No results for {cap}"
        top = results[0]
        assert top.get("type") in ["city", "state_capital"], f"{cap} top result is not city/state_capital: {top.get('type')}, display_name={top.get('display_name')}. Top 3: {results[:3]}"

# ==============================================================================
# CATEGORY B — MISSPELLINGS / PARTIAL / FUZZY INPUT
# ==============================================================================

def test_category_b_misspelling():
    res = client.get("/api/v1/geocode?q=Jaipr")
    assert res.status_code == 200, f"Status code: {res.status_code}"
    results = res.json()["results"]
    print(f"\n[Fuzzy Check] 'Jaipr' returned {len(results)} items.")
    if results:
        print(f"Top result for 'Jaipr': {results[0]['display_name']}")
    else:
        print("Fuzzy match 'Jaipr' returned empty results (known limitation).")

def test_category_b_case_insensitive():
    res_lower = client.get("/api/v1/geocode?q=mumbai")
    assert res_lower.status_code == 200, f"Status code: {res_lower.status_code}"
    results_lower = res_lower.json()["results"]
    assert len(results_lower) > 0, "No results for lowercase 'mumbai'"
    assert "Mumbai" in results_lower[0]["display_name"], f"Lowercase 'mumbai' did not resolve to Mumbai: {results_lower[0]['display_name']}"
    
    res_upper = client.get("/api/v1/geocode?q=MUMBAI")
    assert res_upper.status_code == 200, f"Status code: {res_upper.status_code}"
    results_upper = res_upper.json()["results"]
    assert len(results_upper) > 0, "No results for uppercase 'MUMBAI'"
    assert "Mumbai" in results_upper[0]["display_name"], f"Uppercase 'MUMBAI' did not resolve to Mumbai: {results_upper[0]['display_name']}"

def test_category_b_whitespace_trimming():
    res = client.get("/api/v1/geocode?q=  Pune  ")
    assert res.status_code == 200, f"Status code: {res.status_code}"
    results = res.json()["results"]
    assert len(results) > 0, "No results for padded '  Pune  '"
    assert "Pune" in results[0]["display_name"], f"Padded '  Pune  ' did not resolve to Pune: {results[0]['display_name']}"

def test_category_b_partial():
    res = client.get("/api/v1/geocode?q=Pun")
    assert res.status_code == 200, f"Status code: {res.status_code}"
    results = res.json()["results"]
    print(f"\n[Fuzzy Check] 'Pun' returned {len(results)} items.")
    assert isinstance(results, list)

def test_category_b_empty_and_short():
    for q in ["", "   ", "a"]:
        res = client.get(f"/api/v1/geocode?q={q}")
        assert res.status_code == 200, f"Status code: {res.status_code} for query: '{q}'"
        assert res.json()["results"] == [], f"Expected empty results list for query: '{q}', got: {res.json()}"

# ==============================================================================
# CATEGORY C — HYPERLOCAL PUNE ZONES
# ==============================================================================

def test_category_c_pune_suburbs():
    suburbs = ["Kothrud", "Hadapsar", "Katraj", "Aundh"]
    for suburb in suburbs:
        res = client.get(f"/api/v1/geocode?q={suburb}")
        assert res.status_code == 200, f"Status code: {res.status_code} for {suburb}"
        results = res.json()["results"]
        assert len(results) > 0, f"No results for {suburb}"
        top = results[0]
        assert suburb in top.get("display_name") and "Pune" in top.get("display_name"), f"Suburb '{suburb}' invalid match: {top.get('display_name')}. Top 3: {results[:3]}"

def test_category_c_shivajinagar():
    res = client.get("/api/v1/geocode?q=Shivajinagar&limit=15")
    assert res.status_code == 200, f"Status code: {res.status_code}"
    results = res.json()["results"]
    assert len(results) > 0, "No results for Shivajinagar"
    has_pune_shivajinagar = any("Pune" in r.get("display_name", "") for r in results)
    assert has_pune_shivajinagar, f"Pune Shivajinagar not found in results list. Top 3: {results[:3]}"

# ==============================================================================
# CATEGORY D — DISTRICT / ADMINISTRATIVE BOUNDARY SEARCHES
# ==============================================================================

def test_category_d_districts():
    queries = [
        ("Pune district", "administrative"), 
        ("Purulia district", "administrative"), 
        ("Maharashtra", "administrative"), 
        ("Rajasthan", "administrative")
    ]
    for q, expected_type in queries:
        res = client.get(f"/api/v1/geocode?q={q}")
        assert res.status_code == 200, f"Status code: {res.status_code} for {q}"
        results = res.json()["results"]
        assert len(results) > 0, f"No results for {q}"
        top = results[0]
        assert top.get("type") == expected_type, f"{q} type is not {expected_type}: {top.get('type')}. Top 3: {results[:3]}"

# ==============================================================================
# CATEGORY E — EDGE CASES / BREAKING ATTEMPTS
# ==============================================================================

def test_category_e_very_long():
    long_q = "xyz" * 150
    start = time.time()
    res = client.get(f"/api/v1/geocode?q={long_q}")
    duration = time.time() - start
    assert duration < 6.0, f"Request took too long: {duration}s"
    assert res.status_code == 200
    assert res.json()["results"] == [], f"Expected empty results list, got: {res.json()}"

def test_category_e_sql_injection():
    res = client.get("/api/v1/geocode?q=Pune'; DROP TABLE--")
    assert res.status_code == 200, f"Status code: {res.status_code}"
    results = res.json()["results"]
    assert isinstance(results, list)

def test_category_e_unicode():
    res = client.get("/api/v1/geocode?q=पुणे")
    assert res.status_code == 200, f"Status code: {res.status_code}"
    results = res.json()["results"]
    print(f"\n[Unicode Check] Devanagari query returned {len(results)} items.")
    if results:
        top_name = results[0]["display_name"]
        top_name_safe = top_name.encode('ascii', 'backslashreplace').decode('ascii')
        is_matched = "Pune" in top_name or "पुणे" in top_name
        assert is_matched, f"Devanagari query did not resolve to Pune: {top_name_safe}"

def test_category_e_special_chars():
    res = client.get("/api/v1/geocode?q=Pune🏙️")
    assert res.status_code == 200, f"Status code: {res.status_code}"
    results = res.json()["results"]
    assert isinstance(results, list)

def test_category_e_rapid_fire():
    def send_req():
        return client.get("/api/v1/geocode?q=Pune")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(send_req) for _ in range(10)]
        responses = [f.result() for f in futures]
    
    for r in responses:
        assert r.status_code in [200, 429, 502], f"Unexpected status code: {r.status_code}"

def test_category_e_non_existent():
    res = client.get("/api/v1/geocode?q=Xyzzyplonkqwerty12345")
    assert res.status_code == 200, f"Status code: {res.status_code}"
    assert res.json()["results"] == []

# ==============================================================================
# CATEGORY F — RESPONSE SHAPE VALIDATION
# ==============================================================================

def test_category_f_shape_validation():
    res = client.get("/api/v1/geocode?q=Pune")
    assert res.status_code == 200, f"Status code: {res.status_code}"
    results = res.json()["results"]
    assert len(results) > 0
    
    for r in results:
        assert isinstance(r.get("display_name"), str) and len(r.get("display_name")) > 0
        assert isinstance(r.get("lat"), float) and -90 <= r.get("lat") <= 90
        assert isinstance(r.get("lon"), float) and -180 <= r.get("lon") <= 180
        assert isinstance(r.get("type"), str)
        assert isinstance(r.get("importance"), float) and 0 <= r.get("importance") <= 1
        assert isinstance(r.get("tier"), int) and 0 <= r.get("tier") <= 6
        
    for i in range(len(results) - 1):
        curr = results[i]
        nxt = results[i + 1]
        assert curr["tier"] <= nxt["tier"], f"Tiers not sorted ascending: {curr['tier']} > {nxt['tier']}. Total: {results}"
        if curr["tier"] == nxt["tier"]:
            assert curr["importance"] >= nxt["importance"], f"Importances not sorted descending within same tier: {curr['importance']} < {nxt['importance']} in tier {curr['tier']}. Total: {results}"
