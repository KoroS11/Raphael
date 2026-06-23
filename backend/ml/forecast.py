"""
Raphael — Stage 3: FORECAST (Prophet per Zone per Layer)

Trains a Prophet model per zone per layer type and generates 48-hour
forecasts with exceedance windows. All runs tracked in MLflow.
"""
import os
import sys

# Windows DLL overrides for MKL/OMP and Stan compiler
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
conda_prefix = os.environ.get("CONDA_PREFIX") or r"C:\Users\harsh\anaconda3\envs\raphael-env"
lib_bin = os.path.join(conda_prefix, "Library", "bin")
if os.path.exists(lib_bin) and lib_bin not in os.environ["PATH"]:
    os.environ["PATH"] = lib_bin + os.pathsep + os.environ["PATH"]

import uuid
import pandas as pd
import numpy as np
try:
    import mlflow
except ImportError:
