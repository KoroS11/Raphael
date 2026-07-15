"""
Test robustness fixes for forecast.py and clustering.py.
Verifies: MLflow isolation, atomic transactions, fallback paths.
Run from backend root: python tests/test_robustness_fixes.py
"""
import sys
import os
import ast
import inspect

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

# Ensure backend dir is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pre-import torch first to resolve Windows MKL/OpenMP DLL collision quirk
try:
    import torch
except Exception:
    pass

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name} — {detail}")


print("=" * 60)
print("TEST SUITE: Robustness fixes for forecast.py & clustering.py")
print("=" * 60)

# ----------------------------------------------------------------
# 1. STRUCTURAL CHECKS — parse the AST to verify patterns exist
# ----------------------------------------------------------------
print("\n--- forecast.py structural checks ---")

forecast_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "ml", "forecast.py"
)
with open(forecast_path, "r", encoding="utf-8") as f:
    forecast_src = f.read()

forecast_tree = ast.parse(forecast_src)

# Check MockMLflow exists (MLflow isolation pattern)
class_names = [n.name for n in ast.walk(forecast_tree) if isinstance(n, ast.ClassDef)]
check("MockMLflow class defined", "MockMLflow" in class_names,
      f"found classes: {class_names}")

# Check try/except around mlflow import
has_mlflow_try_import = False
for node in ast.walk(forecast_tree):
    if isinstance(node, ast.Try):
        for child in ast.walk(node):
            if isinstance(child, ast.Import):
                for alias in child.names:
                    if alias.name == "mlflow":
                        has_mlflow_try_import = True
check("MLflow import wrapped in try/except", has_mlflow_try_import)

# Check train_and_forecast function exists
func_names = [n.name for n in ast.walk(forecast_tree) if isinstance(n, ast.FunctionDef)]
check("train_and_forecast() defined", "train_and_forecast" in func_names,
      f"found functions: {func_names}")
check("_generate_explanation() defined", "_generate_explanation" in func_names)

# Check for DELETE before INSERT pattern (atomic transaction)
check("DELETE before INSERT pattern in forecast source",
      "DELETE FROM ml_outputs" in forecast_src and "bulk_save_objects" in forecast_src,
      "should have DELETE + bulk_save_objects in same transaction")

# Check for db.rollback() in error path
check("db.rollback() in error handler", "db.rollback()" in forecast_src,
      "forecast should rollback on Prophet failure")

# Check for defensive MLflow logging
check("Defensive MLflow log_params (try/except)",
      'mlflow.log_params' in forecast_src and 'non-fatal' in forecast_src,
      "MLflow calls should be wrapped with non-fatal handling")

# Check that mlflow.set_tracking_uri is wrapped in try/except
check("mlflow.set_tracking_uri wrapped in try/except",
      "try:" in forecast_src.split("set_tracking_uri")[0][-100:] if "set_tracking_uri" in forecast_src else False,
      "top-level set_tracking_uri should be wrapped")

# Check ResidualLSTM class (hybrid forecaster)
check("ResidualLSTM class defined", "ResidualLSTM" in class_names)
check("run_hybrid_forecast() defined", "run_hybrid_forecast" in func_names)

# ----------------------------------------------------------------
print("\n--- clustering.py structural checks ---")

clustering_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "ml", "clustering.py"
)
with open(clustering_path, "r", encoding="utf-8") as f:
    clustering_src = f.read()

clustering_tree = ast.parse(clustering_src)

class_names_c = [n.name for n in ast.walk(clustering_tree) if isinstance(n, ast.ClassDef)]
func_names_c = [n.name for n in ast.walk(clustering_tree) if isinstance(n, ast.FunctionDef)]

check("MockMLflow class defined", "MockMLflow" in class_names_c)
check("cluster_zones() defined", "cluster_zones" in func_names_c)
check("assign_cluster_labels() defined", "assign_cluster_labels" in func_names_c)
check("_fallback_clustering() defined", "_fallback_clustering" in func_names_c)
check("_fallback_label() defined", "_fallback_label" in func_names_c)

# Check atomic transaction pattern
delete_count = clustering_src.count("DELETE FROM ml_outputs")
check("Atomic DELETE+INSERT in cluster_zones and _fallback_clustering",
      delete_count >= 2,
      f"found {delete_count} DELETE statements, expected >= 2")

# Check MLflow isolation (try/except around mlflow calls)
check("MLflow tracking failure is non-fatal",
      "non-fatal" in clustering_src,
      "clustering should catch MLflow errors as non-fatal")

# Check fallback path
check("Fallback clustering when insufficient zones",
      "_fallback_clustering" in clustering_src and "fallback-v1.0" in clustering_src)

# Check stable label assignment
check("Stable label assignment via centroid ranking",
      "inverse_transform" in clustering_src and "argsort" in clustering_src,
      "should rank centroids by stress for stable labels")

# ----------------------------------------------------------------
# 2. IMPORT CHECKS — verify the modules actually import
# ----------------------------------------------------------------
print("\n--- Import checks ---")

try:
    from ml.clustering import cluster_zones, assign_cluster_labels, _fallback_clustering
    check("ml.clustering imports successfully", True)
except Exception as e:
    check("ml.clustering imports successfully", False, str(e))

try:
    from ml.forecast import train_and_forecast, _generate_explanation
    check("ml.forecast core functions import successfully", True)
except Exception as e:
    check("ml.forecast core functions import successfully", False, str(e))

# ----------------------------------------------------------------
# 3. SIGNATURE CHECKS
# ----------------------------------------------------------------
print("\n--- Signature checks ---")

try:
    sig = inspect.signature(train_and_forecast)
    params = list(sig.parameters.keys())
    check("train_and_forecast signature has db, zone_id, layer_type, horizon_hours",
          params == ["db", "zone_id", "layer_type", "horizon_hours"],
          f"got: {params}")
except Exception as e:
    check("train_and_forecast signature check", False, str(e))

try:
    sig = inspect.signature(cluster_zones)
    params = list(sig.parameters.keys())
    check("cluster_zones signature has db, region_id",
          params == ["db", "region_id"],
          f"got: {params}")
except Exception as e:
    check("cluster_zones signature check", False, str(e))

# ----------------------------------------------------------------
# 4. FILE SIZE SANITY
# ----------------------------------------------------------------
print("\n--- File size sanity ---")

forecast_size = os.path.getsize(forecast_path)
clustering_size = os.path.getsize(clustering_path)
check(f"forecast.py size is substantial ({forecast_size} bytes)",
      forecast_size > 5000,
      f"only {forecast_size} bytes — still truncated?")
check(f"clustering.py size is substantial ({clustering_size} bytes)",
      clustering_size > 3000,
      f"only {clustering_size} bytes — still truncated?")

# ----------------------------------------------------------------
print("\n" + "=" * 60)
print(f"RESULTS: {PASS} passed, {FAIL} failed out of {PASS + FAIL} checks")
print("=" * 60)
sys.exit(1 if FAIL > 0 else 0)
