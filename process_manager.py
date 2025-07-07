import psutil
import time
import os
import signal
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List

class EnhancedProcessManager:
    def __init__(self, name: str, pid_file: Path, status_file: Path, command: List[str], working_dir: str = None):
        self.name = name
        self.pid_file = pid_file
        self.status_file = status_file
        self.command = command
        self.working_dir = working_dir or os.getcwd()

    def get_pid(self) -> Optional[int]:
        if not self.pid_file.exists():
            return None
        try:
            return int(self.pid_file.read_text().strip())
        except (ValueError, IOError):
            return None

    def is_running(self) -> bool:
        pid = self.get_pid()
        if pid is None:
            return False

        if not psutil.pid_exists(pid):
            self._cleanup()
            return False

        try:
            p = psutil.Process(pid)
            # Check for zombie processes
            if p.status() == psutil.STATUS_ZOMBIE:
                self._cleanup()
                return False
            # Check if the command line of the process matches our command
            # This is a robust way to avoid PID reuse issues.
            if p.cmdline() == self.command:
                return True
            else:
                # PID has been reused by another process
                self._cleanup()
                return False
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # Process disappeared or we can't access it
            self._cleanup()
            return False

    def start(self):
        if self.is_running():
            print(f"{self.name} is already running.")
            return False

        try:
            # For debugging: redirect stdout/stderr to files
            log_dir = Path(self.working_dir) / 'logs'
            log_dir.mkdir(exist_ok=True)
            stdout_log = open(log_dir / f"{self.name}_stdout.log", 'w')
            stderr_log = open(log_dir / f"{self.name}_stderr.log", 'w')

            # Use start_new_session=True on POSIX to detach the process
            # from the controlling terminal, making it a true daemon.
            kwargs = {
                'cwd': self.working_dir,
                'start_new_session': True,
                'stdout': stdout_log,
                'stderr': stderr_log
            }
            if os.name == 'nt':  # For Windows
                kwargs.pop('start_new_session', None)
                # DETACHED_PROCESS flag for Windows
                from subprocess import DETACHED_PROCESS
                kwargs['creationflags'] = DETACHED_PROCESS

            process = subprocess.Popen(self.command, **kwargs)
            self._write_pid_file(process.pid)
            self._write_status_file("running", process.pid)
            print(f"{self.name} started successfully (PID: {process.pid}).")
            return True
        except Exception as e:
            print(f"Failed to start {self.name}: {e}")
            return False

    def stop(self, timeout: int = 10):
        if not self.is_running():
            print(f"{self.name} is not running.")
            self._cleanup()
            return True

        pid = self.get_pid()
        if not pid:
            # This case should be covered by is_running(), but as a safeguard:
            print(f"{self.name} is not running (no PID file).")
            return True

        try:
            process = psutil.Process(pid)
            process.terminate()
            try:
                process.wait(timeout=timeout)
            except psutil.TimeoutExpired:
                print(f"Graceful shutdown for {self.name} timed out. Killing...")
                process.kill()
            self._cleanup()
            print(f"{self.name} stopped successfully.")
            return True
        except psutil.NoSuchProcess:
            print(f"{self.name} process not found, cleaning up.")
            self._cleanup()
            return True
        except psutil.Error as e:
            print(f"Error stopping {self.name}: {e}")
            return False

    def restart(self):
        print(f"Restarting {self.name}...")
        if self.is_running():
            if not self.stop():
                print(f"Failed to stop {self.name}, aborting restart.")
                return False
        time.sleep(1)
        return self.start()

    def get_status(self) -> Dict[str, Any]:
        if not self.is_running():
            return {
                'name': self.name,
                'running': False,
                'pid': None,
                'status': 'stopped'
            }

        pid = self.get_pid()
        status = {
            'name': self.name,
            'running': True,
            'pid': pid,
        }
        if self.status_file.exists():
            try:
                status_from_file = json.loads(self.status_file.read_text())
                status.update(status_from_file)
            except (json.JSONDecodeError, IOError):
                # If status file is corrupt, we still have the basic running status
                pass
        return status

    def _write_pid_file(self, pid: int):
        try:
            self.pid_file.write_text(str(pid))
        except IOError as e:
            print(f"Warning: Could not write PID file: {e}")

    def _write_status_file(self, status: str, pid: Optional[int]):
        status_data = {
            'status': status,
            'pid': pid,
            'timestamp': time.time()
        }
        try:
            self.status_file.write_text(json.dumps(status_data, indent=4))
        except IOError as e:
            print(f"Warning: Could not write status file: {e}")

    def _cleanup(self):
        # Use missing_ok=True for Python 3.8+ on Path.unlink()
        # For broader compatibility, check for existence first.
        if self.pid_file.exists():
            try:
                self.pid_file.unlink()
            except OSError:
                pass
        if self.status_file.exists():
            try:
                self.status_file.unlink()
            except OSError:
                pass
