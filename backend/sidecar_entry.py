"""
Raphael — Python sidecar entry point for Tauri packaging.
Starts ONLY the FastAPI backend via uvicorn.
MLflow, Prefect, Mage.ai are NOT started here.
"""
import sys
import os
import signal
import subprocess

# Resolve database path to AppData when running as packaged sidecar
# When running in development (not frozen), use relative path
if getattr(sys, 'frozen', False):
    # Running as PyInstaller bundle
    app_data = os.environ.get('APPDATA', os.path.expanduser('~'))
    db_dir = os.path.join(app_data, 'Raphael')
    os.makedirs(db_dir, exist_ok=True)
    os.environ['RAPHAEL_DB_PATH'] = os.path.join(db_dir, 'raphael.db')
    # Add the bundled app directory to sys.path
    bundle_dir = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
    sys.path.insert(0, bundle_dir)
    # Set the frontend dist path pointing to bundled frontend_dist folder
    os.environ['RAPHAEL_FRONTEND_DIST'] = os.path.join(bundle_dir, 'frontend_dist')
else:
    # Development mode — use existing relative path
    os.environ.setdefault('RAPHAEL_DB_PATH', 
                          os.path.join(os.path.dirname(__file__), 
                                       '..', 'data', 'raphael.db'))
    os.environ['RAPHAEL_FRONTEND_DIST'] = os.path.join(
        os.path.dirname(__file__),
        '..', 'raphael-frontend', 'dist', 'client'
    )

def main():
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
    )

if __name__ == "__main__":
    main()
