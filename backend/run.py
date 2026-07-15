import ssl
try:
    orig_load_windows_store_certs = ssl.SSLContext._load_windows_store_certs
    def patched_load_windows_store_certs(self, storename, purpose):
        try:
            orig_load_windows_store_certs(self, storename, purpose)
        except ssl.SSLError:
            pass
    ssl.SSLContext._load_windows_store_certs = patched_load_windows_store_certs
except AttributeError:
    pass

import os
import sys
import uvicorn

# Ensure the backend directory is in the sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    port = int(os.environ.get("RAPHAEL_PORT", 8000))
    host = "127.0.0.1"
    uvicorn.run("api.main:app", host=host, port=port, log_level="info", reload=False)
