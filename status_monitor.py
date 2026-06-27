import os
import sys
import time
import glob
import psutil
from datetime import datetime

WORKSPACE_DIR = r"c:\Users\harsh\Raphael"
STATUS_FILE = os.path.join(WORKSPACE_DIR, "terminal_status.md")
TASKS_PATTERN = r"C:\Users\harsh\.gemini\antigravity-ide\brain\*\.system_generated\tasks\task-*.log"

def get_process_info(script_name):
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
        try:
            cmd = proc.info.get('cmdline') or []
            cmd_str = " ".join(cmd).lower()
            if script_name.lower() in cmd_str and "python" in cmd_str:
                started = datetime.fromtimestamp(proc.info['create_time']).strftime('%Y-%m-%d %H:%M:%S')
                return {
                    "pid": proc.info['pid'],
                    "cmd": " ".join(cmd),
                    "started": started,
                    "status": "RUNNING"
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return {"status": "STOPPED"}

def main():
    print("Status monitor starting...")
    while True:
        try:
            backend_info = get_process_info("run.py")
            scheduler_info = get_process_info("scheduler.py")
            
            task_files = sorted(glob.glob(TASKS_PATTERN), key=os.path.getmtime, reverse=True)
            
            run_log = "[No active run.py log]"
            sched_log = "[No active scheduler.py log]"
            
            for fpath in task_files:
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        header = f.read(8000).lower()
                        if "run.py" in header or "uvicorn" in header or "api starting" in header or "raphael api" in header:
                            if run_log == "[No active run.py log]":
                                f.seek(0)
                                run_log = "".join(f.readlines()[-15:])
                        elif "scheduler.py" in header or "apscheduler" in header or "ingestion job" in header or "scheduler starting" in header:
                            if sched_log == "[No active scheduler.py log]":
                                f.seek(0)
                                sched_log = "".join(f.readlines()[-15:])
                except Exception:
                    pass

            # Read from today's application log as fallback
            app_log_dir = os.path.join(WORKSPACE_DIR, "data", "logs")
            app_logs = sorted(glob.glob(os.path.join(app_log_dir, "raphael-*.log")), key=os.path.getmtime, reverse=True)
            if app_logs and run_log == "[No active run.py log]":
                try:
                    with open(app_logs[0], "r", encoding="utf-8", errors="ignore") as f:
                        run_log = "".join(f.readlines()[-15:])
                except Exception:
                    pass

            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            md_content = f"""# RAPHAEL — Background Processes Status
Last Updated: `{now_str}`

## 1. FastAPI Backend (run.py)
* **Status**: {backend_info['status']}
"""
            if backend_info['status'] == "RUNNING":
                md_content += f"""* **Process ID**: `{backend_info['pid']}`
* **Command**: `{backend_info['cmd']}`
* **Started**: `{backend_info['started']}`
"""
            md_content += f"""
### Recent Output:
```text
{run_log}
```

## 2. Background Scheduler (scheduler.py)
* **Status**: {scheduler_info['status']}
"""
            if scheduler_info['status'] == "RUNNING":
                md_content += f"""* **Process ID**: `{scheduler_info['pid']}`
* **Command**: `{scheduler_info['cmd']}`
* **Started**: `{scheduler_info['started']}`
"""
            md_content += f"""
### Recent Output:
```text
{sched_log}
```

---
*Note: This status file is updated automatically every second by the background status monitor daemon.*
"""
            with open(STATUS_FILE, "w", encoding="utf-8") as f:
                f.write(md_content)
            
        except Exception as e:
            print(f"Error in monitor: {e}", file=sys.stderr)
            
        time.sleep(1.0)

if __name__ == "__main__":
    main()
