import subprocess
import sys

subprocess.check_call([sys.executable, "-m", "flask", "db", "upgrade"])
os_exec = ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:create_app()"]
subprocess.check_call(os_exec)
