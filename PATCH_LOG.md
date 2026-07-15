# RAPHAEL Backend Robustness — Patch Log & Remaining Work Tracker

This document serves as a living tracker of backend robustness improvements, security audits, verification logs, and unresolved items.

---

## Part 1 — Patches Already Applied

The following robustness fixes are verified as active in the codebase:

### 1. MLflow Session Isolation
*   **Location**: [`backend/ml/forecast.py` (`train_and_forecast`)](file:///c:/Users/harsh/Raphael/backend/ml/forecast.py#L85-L109)
*   **Details**: Attempting `mlflow.set_experiment` and `mlflow.start_run` is isolated in a standalone `try/except` block. Logging of parameters and metrics is similarly wrapped defensively. A tracking server outage does not block or crash the main Prophet model training or database updates.
*   **Test State**: **PASS** (verified via `tests/test_robustness_fixes.py::TestRobustnessFixes::test_mlflow_outage_handling`).

### 2. RandomForest Fit/Predict Concurrency Lock
*   **Location**: [`backend/ml/attribution.py` (`AnomalyAttributor`)](file:///c:/Users/harsh/Raphael/backend/ml/attribution.py#L51-L60)
*   **Details**: Added an instance-level `self.lock = threading.Lock()`.
    *   `fit()` attempts to acquire the lock non-blockingly (`blocking=False`), logging `attribution_fit_already_running` and returning `False` on overlap.
    *   `attribute()` uses a blocking context (`with self.lock:`) around classifier prediction (`self.clf.predict_proba`) to prevent concurrent read-during-fit corruption.
*   **Test State**: **PASS** (verified via `test_attribution_concurrency_lock` for fit contention and `test_attribution_fit_predict_contention` for fit-vs-predict blocking behavior).

### 3. Atomic Database Transactions
*   **Location**:
    *   [`backend/ml/forecast.py` (`train_and_forecast`)](file:///c:/Users/harsh/Raphael/backend/ml/forecast.py#L150-L179)
    *   [`backend/ml/clustering.py` (`cluster_zones`)](file:///c:/Users/harsh/Raphael/backend/ml/clustering.py#L159-L186)
    *   [`backend/ml/clustering.py` (`_fallback_clustering`)](file:///c:/Users/harsh/Raphael/backend/ml/clustering.py#L205-L232)
*   **Details**: Intermediate commits between deletion queries and bulk inserts were removed. Database sessions now run `DELETE` and `bulk_save_objects` within a single transaction followed by a final `db.commit()`.
*   **Test State**:
    *   **Clustering**: **PASS** (verified via fallback-path and primary KMeans-path atomicity tests).
    *   **Forecasting Verification Gap**: **OPEN** (Test 1 verifies that forecasting completes and writes rows, but does not run a concurrent-read test; therefore, a zero-read window is physically mitigated but remains unverified under high-concurrency simulation).

### 4. Tauri v2 Native Startup Dialog
*   **Location**: [`src-tauri/src/lib.rs`](file:///c:/Users/harsh/Raphael/src-tauri/src/lib.rs#L77-L84)
*   **Details**: Added `tauri-plugin-dialog = "2.0.0-beta.0"` to [`Cargo.toml`](file:///c:/Users/harsh/Raphael/src-tauri/Cargo.toml) (resolving to stable v2-compatible `2.7.1` in compilation toolchain). The startup loop awaits backend availability on port 8000. If it fails, it displays a native Windows error dialog stating: *"Failed to launch the environmental backend service on port 8000..."* blockingly before cleanly exiting.
*   **Test State**: **PASS** (verified manually by executing the Tauri client compiled target with the backend offline; thread blocked on `.blocking_show()` and exited cleanly on dismissal).

### 5. Conda SSL Store-Cert Monkeypatch
*   **Location**:
    *   [`backend/verify_fixes.py`](file:///c:/Users/harsh/Raphael/backend/verify_fixes.py#L8-L19)
    *   [`backend/run.py`](file:///c:/Users/harsh/Raphael/backend/run.py)
*   **Details**: Patched `ssl.SSLContext._load_windows_store_certs` inside a try/except on startup. It traps individual certificate load errors (the Anaconda Windows certificate store parsing bug) and skips corrupt entries, keeping certificate validation enabled for all external HTTPS requests.
*   **Test State**: **PASS** (verified by the successful execution of local verification checks making external network API calls without crash).

### 6. Robustness Test Coverage
*   **Location**: [`backend/tests/test_robustness_fixes.py`](file:///c:/Users/harsh/Raphael/backend/tests/test_robustness_fixes.py)
*   **Details**: Implemented a comprehensive test suite of 6 unit tests covering:
    1.  MLflow connection outages/failures handling.
    2.  RandomForest fit lock contention.
    3.  RandomForest fit-vs-predict blocking safety.
    4.  Zone clustering fallback transaction atomicity.
    5.  Zone clustering primary KMeans transaction atomicity.
    6.  Prophet fit failure database transaction rollback.
*   **Test State**: **PASS** (all 6 tests execute successfully in 225.5 seconds).

---

## Part 2 — Known Outstanding Work

| Item | File(s) | Priority | Status | Notes / Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **POST Request Schema Validation** | [`backend/api/routes/reports.py`](file:///c:/Users/harsh/Raphael/backend/api/routes/reports.py)<br>[`backend/api/routes/alerts.py`](file:///c:/Users/harsh/Raphael/backend/api/routes/alerts.py) | **Critical** | Not Started | POST endpoints currently accept generic dict models. Converting to strict Pydantic schemas avoids corrupt schema insertions. |
| **Scheduler vs Manual Execution Lock** | `backend/api/routes/system.py`<br>`backend/scheduler.py` | **Critical** | Not Started | Runs on manual API triggers can overlap scheduled cycles. Needs a shared system/file lock to prevent DB & GPU collision. |
| **MODIS Ingestion Temp Folder Leak** | [`backend/ingestion/flows/ndvi_modis.py`](file:///c:/Users/harsh/Raphael/backend/ingestion/flows/ndvi_modis.py#L157)<br>[`backend/ingestion/flows/lst_modis.py`](file:///c:/Users/harsh/Raphael/backend/ingestion/flows/lst_modis.py#L156) | **Should Fix** | Not Started | Granule downloads create temp folders that leak on execution failures. Needs a `finally` block with `shutil.rmtree()` cleanup. |
| **WS Event Broadcast Concurrency** | [`backend/api/routes/ws.py`](file:///c:/Users/harsh/Raphael/backend/api/routes/ws.py#L19-L26) | **Should Fix** | Not Started | Broadcasts run `await` sequentially in a `for` loop. A single slow/hung websocket connection blocks broadcasts to all other users. |
| **Days Range Validation** | [`backend/api/routes/anomalies.py`](file:///c:/Users/harsh/Raphael/backend/api/routes/anomalies.py#L9) | **Should Fix** | Not Started | Query parameter `days` is unvalidated. Passing negative or massive values causes unexpected SQL ranges or huge memory usage. |
| **Defensive Zone Geometry Parsing** | [`backend/db/queries.py`](file:///c:/Users/harsh/Raphael/backend/db/queries.py#L61) | **Should Fix** | Not Started | Geometry `json.loads` calls are unshielded. Malformed geometry strings stored in SpatiaLite columns will crash the API. |
| **APScheduler Traceback Logging** | [`backend/scheduler.py`](file:///c:/Users/harsh/Raphael/backend/scheduler.py#L151-L156) | **Should Fix** | Not Started | `event.exception` is logged but its traceback is omitted. Finding crash sites in scheduled tasks is extremely difficult. |
| **Tauri Toolchain Upgrade** | [`src-tauri/Cargo.toml`](file:///c:/Users/harsh/Raphael/src-tauri/Cargo.toml)<br>`src-tauri/tauri.conf.json` | **Should Fix** | Not Started | Tauri dependencies are locked to outdated RC builds. Needs upgrade to the stable 2.x line in a dedicated isolated branch. |
| **MLflow Server Configuration** | `backend/ml/forecast.py`<br>`backend/ml/clustering.py` | **Nice to Have** | Not Started | Currently falls back to mock logging during outages. Requires configuring a persistent local/remote MLflow tracking server. |
| **Cross-Station Geolocation Coverage** | `backend/db/queries.py`<br>`backend/ingestion/` | **Nice to Have** | Not Started | 0 of 17 raw payload stations carry lat/lon. Corroboration relies on hardcoded lookups covering ~24% of sensors. |
| **Red Team Independent Data Inputs** | `backend/ml/red_team.py` | **Nice to Have** | Not Started | Validation relies entirely on internal checks. Wired Sentinel-5P/satellite data would yield truly independent corroboration. |
| **Frontend Static View Implementations** | `raphael-frontend/` | **Teammate Owned** | In Progress | Frontend views (Alerts, Reports, Settings) are static/mocked. Tracked here for visibility only; do not modify frontend files. |

---

## Part 3 — Definition of Done (DoD)

To certify that the RAPHAEL backend is fully hardened, any subsequent PR or modification must meet the following checklist:

1.  **Strict Request Sanitization**: All API endpoints accepting bodies (`POST`/`PUT`/`PATCH`) must validate input types against schema models (no freeform `dict` inputs).
2.  **Resource Cleanup Guarantees**: All filesystem tasks that create folders or download local artifacts (GIS raster assets, satellite granules) must operate inside a `finally` block or context manager ensuring deletion upon exit/failure.
3.  **Crash Resilience**: A breakdown of auxiliary integrations (e.g. MLflow server, geocoding lookups, external alert dispatch webhooks) must be isolated with try-except blocks, falling back to clean local defaults without aborting core application workflows.
4.  **Transaction Boundaries**: Operations performing sequential `DELETE` and `INSERT` steps must execute inside single SQLAlchemy transaction transactions (`db.commit()` only on execution completeness), preventing empty database states from being read.
5.  **Test Enforcement**: All newly added endpoints, transaction changes, or concurrent workers must carry matching automated unit tests validating successful runs, lock timing, and rollback behaviors under failure.
