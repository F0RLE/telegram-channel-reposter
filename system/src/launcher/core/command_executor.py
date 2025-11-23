"""Command executor with unified error handling and logging"""
import subprocess
import logging
from typing import Optional, Dict, Any, List, Tuple
import os

logger = logging.getLogger(__name__)


class CommandExecutor:
    """Unified command executor with error handling and logging"""
    
    @staticmethod
    def _get_startupinfo() -> subprocess.STARTUPINFO:
        """Get Windows startup info for hidden window"""
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        return startupinfo
    
    @staticmethod
    def run(
        cmd: List[str],
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
        env: Optional[Dict[str, str]] = None,
        capture_output: bool = True,
        text: bool = True,
        log_prefix: str = "",
        raise_on_error: bool = False
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Execute command with unified error handling
        
        Args:
            cmd: Command to execute
            cwd: Working directory
            timeout: Timeout in seconds
            env: Environment variables
            capture_output: Capture stdout/stderr
            text: Return text instead of bytes
            log_prefix: Prefix for log messages
            raise_on_error: Raise exception on error
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            startupinfo = CommandExecutor._get_startupinfo()
            
            result = subprocess.run(
                cmd,
                cwd=cwd,
                env=env,
                capture_output=capture_output,
                text=text,
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=startupinfo
            )
            
            stdout = result.stdout if capture_output else None
            stderr = result.stderr if capture_output else None
            
            if result.returncode != 0:
                if raise_on_error:
                    raise subprocess.CalledProcessError(
                        result.returncode, cmd, stdout, stderr
                    )
                if log_prefix and stderr:
                    logger.warning(f"{log_prefix} Command failed: {stderr[:200]}")
                return False, stdout, stderr
            
            return True, stdout, stderr
            
        except subprocess.TimeoutExpired as e:
            if raise_on_error:
                raise
            if log_prefix:
                logger.error(f"{log_prefix} Command timeout after {timeout}s")
            return False, None, f"Timeout after {timeout}s"
            
        except Exception as e:
            if raise_on_error:
                raise
            if log_prefix:
                logger.error(f"{log_prefix} Command error: {e}")
            return False, None, str(e)
    
    @staticmethod
    def run_async(
        cmd: List[str],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        log_prefix: str = ""
    ) -> subprocess.Popen:
        """
        Execute command asynchronously
        
        Returns:
            Popen process object
        """
        try:
            startupinfo = CommandExecutor._get_startupinfo()
            
            process = subprocess.Popen(
                cmd,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=startupinfo
            )
            
            return process
            
        except Exception as e:
            if log_prefix:
                logger.error(f"{log_prefix} Failed to start process: {e}")
            raise

