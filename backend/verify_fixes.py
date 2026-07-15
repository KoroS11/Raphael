r"""
VERIFICATION PASS — Architecture v1 Freeze Gate
Checks three critical fixes before any further work proceeds.
Run from backend root: C:\Users\harsh\anaconda3\envs\raphael-env\python.exe verify_fixes.py
"""
import sys, os

# Windows DLL overrides for MKL/OMP, Stan compiler, and SpatiaLite
if sys.platform == 'win32':
    conda_prefix = os.environ.get("RAPHAEL_CONDA_PREFIX") or os.environ.get("CONDA_PREFIX") or r"C:\Users\harsh\anaconda3\envs\raphael-env"
    lib_bin = os.path.join(conda_prefix, "Library", "bin")
    if os.path.exists(lib_bin):
        if lib_bin not in os.environ["PATH"]:
            os.environ["PATH"] = lib_bin + os.pathsep + os.environ["PATH"]
        if hasattr(os, 'add_dll_directory'):
            try:
                os.add_dll_directory(lib_bin)
            except Exception:
                pass

# Monkeypatch Windows SSL default cert loading to bypass ASN1 NOT_ENOUGH_DATA certificate store bug
import ssl
orig_load_default_certs = ssl.SSLContext.load_default_certs
def patched_load_default_certs(self, purpose=ssl.Purpose.SERVER_AUTH):
    try:
        return orig_load_default_certs(self, purpose)
    except Exception:
        try:
            import certifi
            self.load_verify_locations(certifi.where())
        except Exception:
            pass
ssl.SSLContext.load_default_certs = patched_load_default_certs

# IMPORT TORCH FIRST to resolve Windows OpenMP/MKL DLL collision quirk
try:
    import torch
except Exception as te:
    print(f"Pre-import torch failed: {te}")

sys.path.insert(0, '.')

print("=" * 60)
print("VERIFICATION 1 — Q-proxy / Plume concentration realism")
print("=" * 60)
try:
    from ml.plume import _pg_class_from_wind, _sigma_y, _sigma_z, centre_line_concentration
    sy_m = _sigma_y('D', 1000.0)
    sz_m = _sigma_z('D', 1000.0)
    Q = 50000.0  # μg/s, the corrected proxy
    u = 3.0
    # Wait, the signature in plume.py is: centre_line_concentration(Q, u, x_m, H, pg_class)
    # The user's verify_fixes.py call was: centre_line_concentration(Q, u, 1.0, 0.0, sy_m, sz_m)
    # Let's check: the signature we have in plume.py doesn't match this exact order or parameter count!
    # Wait, in plume.py:
    # def centre_line_concentration(Q, u, x_m, H=10.0, pg_class="D")
    # Let's make sure our verification handles whichever signature is defined.
    import inspect
    sig = inspect.signature(centre_line_concentration)
    print(f"centre_line_concentration signature: {sig}")
    if len(sig.parameters) == 5:
        # Standard signature: (Q, u, x_m, H, pg_class)
        # 1km distance = 1000m. H = 5.0.
        conc = centre_line_concentration(Q, u, 1000.0, 5.0, 'D')
    else:
        # Call it with positional args
        conc = centre_line_concentration(Q, u, 1.0, 0.0, sy_m, sz_m)
    print(f"Concentration @ 1km, Class D, Q=50000 ug/s: {conc:.3f} ug/m3")
    if 1.0 <= conc <= 500.0:
        print("VERDICT: PASS — concentration in physically realistic range")
    else:
        print(f"VERDICT: FAIL — expected 1-500 ug/m3, got {conc:.6f}")
        print("  -> Q proxy fix NOT applied correctly. Check ml/plume.py and ml/pcad.py")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"VERDICT: FAIL — import/execution error: {e}")

print()
print("=" * 60)
print("VERIFICATION 2 — Prophet recent-data filter")
print("=" * 60)
try:
    import inspect
    from ml import forecast
    src = inspect.getsource(forecast.run_hybrid_forecast)
    has_cutoff = "days=30" in src or "Timedelta(days=30)" in src
    has_fit_recent = "df_fit" in src
    print(f"'days=30' cutoff present in source: {has_cutoff}")
    print(f"'df_fit' variable (filtered frame) used for training: {has_fit_recent}")
    if has_cutoff and has_fit_recent:
        # find the actual m.fit(...) call and confirm it uses df_fit not df
        fit_line = [l for l in src.splitlines() if "m.fit(" in l]
        print(f"Prophet .fit() call line(s): {fit_line}")
        if any("df_fit" in l for l in fit_line):
            print("VERDICT: PASS — Prophet fits on filtered recent window")
        else:
            print("VERDICT: FAIL — filter exists but m.fit() still uses unfiltered df")
    else:
        print("VERDICT: FAIL — recent-data filter not found in run_hybrid_forecast")
except Exception as e:
    print(f"VERDICT: FAIL — import/execution error: {e}")

print()
print("=" * 60)
print("VERIFICATION 3 — Cross-station validation produces points")
print("=" * 60)
try:
    import sqlite3
    DB_PATH = os.path.abspath('data/raphael.db')
    assert os.path.exists(DB_PATH), f"DB not found: {DB_PATH}"
    conn = sqlite3.connect(DB_PATH)

    region_id = conn.execute(
        "SELECT id FROM regions WHERE name='Pune Metropolitan Region'"
    ).fetchone()
    if not region_id:
        print("VERDICT: FAIL — no Pune region found in DB")
    else:
        region_id = region_id[0]
        stations = conn.execute("""
            SELECT DISTINCT station_name,
                   json_extract(raw_payload, '$.lat') as lat,
                   json_extract(raw_payload, '$.lon') as lon
            FROM raw_observations
            WHERE layer_type='aq' AND region_id=?
        """, (region_id,)).fetchall()

        n_with_coords = sum(1 for s in stations if s[1] is not None and s[2] is not None)
        print(f"Total distinct AQ stations: {len(stations)}")
        print(f"Stations with lat/lon in raw_payload: {n_with_coords}")

        if n_with_coords == 0:
            print("Falling back to KNOWN_STATIONS hardcoded lookup check...")
            # crude check: are there at least 2 stations >2km apart in the known dict used by notebook 4?
            KNOWN_STATIONS = {
                'Savitribai Phule Pune University, Pune - MPCB': (18.5308, 73.8474),
                'Hadapsar, Pune - MPCB': (18.4983, 73.9258),
                'Katraj, Pune - MPCB': (18.4500, 73.8650),
                'Pashan, Pune - MPCB': (18.5295, 73.8025),
            }
            matched = [s[0] for s in stations if s[0] in KNOWN_STATIONS]
            print(f"Station names matching KNOWN_STATIONS dict: {matched}")
            if len(matched) >= 2:
                print("VERDICT: CONDITIONAL PASS — fallback dict has enough matches, "
                      "but confirm notebook 4 Section 3 was actually re-executed with this path")
            else:
                print("VERDICT: FAIL — neither raw_payload coords nor KNOWN_STATIONS "
                      "produce >=2 matched stations. Cross-station validation will stay empty.")
        else:
            print("VERDICT: PASS (data available) — but you must confirm "
                  "notebooks/04_gaussian_plume_validation.ipynb Section 3 "
                  "was re-executed and outputs/04b_cross_station.png regenerated after this fix")
except Exception as e:
    print(f"VERDICT: FAIL — import/execution error: {e}")

print()
print("=" * 60)
print("GATE SUMMARY — do not proceed to rule formalization or")
print("notebook re-execution until all three show PASS above.")
print("=" * 60)
