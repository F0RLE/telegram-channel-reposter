"""Process management for services"""
import psutil
import os
import logging
from typing import List, Optional, Dict
from .command_executor import CommandExecutor

logger = logging.getLogger(__name__)


class ProcessManager:
    """Manages processes for services"""
    
    @staticmethod
    def find_processes_by_name(name: str) -> List[psutil.Process]:
        """Find all processes by name"""
        processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    proc_name = proc.info['name'] or ''
                    proc_exe = proc.info['exe'] or ''
                    
                    if name.lower() in proc_name.lower() or name.lower() in proc_exe.lower():
                        processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.error(f"Error finding processes: {e}")
        
        return processes
    
    @staticmethod
    def find_processes_by_path(path: str) -> List[psutil.Process]:
        """Find processes by executable path"""
        processes = []
        if not os.path.exists(path):
            return processes
        
        try:
            abs_path = os.path.abspath(path)
            for proc in psutil.process_iter(['pid', 'exe']):
                try:
                    proc_exe = proc.info['exe']
                    if proc_exe and os.path.abspath(proc_exe) == abs_path:
                        processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.error(f"Error finding processes by path: {e}")
        
        return processes
    
    @staticmethod
    def kill_processes(processes: List[psutil.Process], timeout: int = 5) -> int:
        """Kill processes gracefully, then force if needed"""
        killed = 0
        for proc in processes:
            try:
                proc.terminate()
                killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Wait for processes to terminate
        gone, alive = psutil.wait_procs(processes, timeout=timeout)
        
        # Force kill remaining processes
        for proc in alive:
            try:
                proc.kill()
                killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return killed
    
    @staticmethod
    def kill_all_by_name(name: str) -> int:
        """Kill all processes by name"""
        processes = ProcessManager.find_processes_by_name(name)
        return ProcessManager.kill_processes(processes)
    
    @staticmethod
    def kill_all_by_path(path: str) -> int:
        """Kill all processes by path"""
        processes = ProcessManager.find_processes_by_path(path)
        return ProcessManager.kill_processes(processes)
    
    @staticmethod
    def is_process_running(name_or_path: str) -> bool:
        """Check if process is running"""
        processes = ProcessManager.find_processes_by_name(name_or_path)
        if not processes:
            processes = ProcessManager.find_processes_by_path(name_or_path)
        return len(processes) > 0

