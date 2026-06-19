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
