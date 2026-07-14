"""
VERIFICATION PASS — Architecture v1 Freeze Gate
Checks three critical fixes before any further work proceeds.
Run from backend root: python verify_fixes.py
"""
import sys, os

# Windows DLL overrides for MKL/OMP and Stan compiler
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
conda_prefix = r"C:\Users\harsh\anaconda3\envs\raphael-env"
lib_bin = os.path.join(conda_prefix, "Library", "bin")
if os.path.exists(lib_bin):
    if lib_bin not in os.environ["PATH"]:
        os.environ["PATH"] = lib_bin + os.pathsep + os.environ["PATH"]
    if sys.platform == 'win32' and hasattr(os, 'add_dll_directory'):
        try: os.add_dll_directory(lib_bin)
        except: pass

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
    # Note: plume.py signature order is (pg_class, x_m)
    sy_m = _sigma_y('D', 1.0 * 1000)
    sz_m = _sigma_z('D', 1.0 * 1000)
    Q = 50000.0  # ug/s, the corrected proxy
    u = 3.0
    
    # Check signature of centre_line_concentration
    import inspect
    sig = inspect.signature(centre_line_concentration)
    if len(sig.parameters) == 5:
        # standard signature: (Q, u, x_m, H, pg_class)
        conc = centre_line_concentration(Q, u, 1000.0, 5.0, 'D')
    else:
        conc = centre_line_concentration(Q, u, 1.0, 0.0, sy_m, sz_m)
        
    print(f"Concentration @ 1km, Class D, Q=50000 ug/s: {conc:.3f} ug/m3")
    if 1.0 <= conc <= 500.0:
        print("VERDICT: PASS — concentration in physically realistic range")
    else:
