import ctypes
import os
import sys
from typing import Optional, Callable

# Global variable to hold the callback so it's not garbage collected
_llama_log_callback = None
_fd_redirected = False
_saved_stdout_fd = None
_saved_stderr_fd = None
_devnull_fd = None

def _mute_log_callback(level, message, user_data):
    """No-op callback to suppress logs"""
    pass

def _redirect_fds_to_devnull():
    """Redirect stdout and stderr file descriptors to /dev/null"""
    global _fd_redirected, _saved_stdout_fd, _saved_stderr_fd, _devnull_fd
    
    if _fd_redirected:
        return
    
    try:
        # Open /dev/null
        _devnull_fd = os.open(os.devnull, os.O_WRONLY)
        
        # Save original FDs
        _saved_stdout_fd = os.dup(1)  # stdout
        _saved_stderr_fd = os.dup(2)  # stderr
        
        # Redirect FDs to /dev/null
        os.dup2(_devnull_fd, 1)  # stdout -> /dev/null
        os.dup2(_devnull_fd, 2)  # stderr -> /dev/null
        
        _fd_redirected = True
    except Exception as e:
        # If FD redirection fails, we'll try the callback approach instead
        pass

def _restore_fds():
    """Restore original stdout and stderr file descriptors"""
    global _fd_redirected, _saved_stdout_fd, _saved_stderr_fd, _devnull_fd
    
    if not _fd_redirected:
        return
    
    try:
        if _saved_stdout_fd is not None:
            os.dup2(_saved_stdout_fd, 1)
            os.close(_saved_stdout_fd)
        if _saved_stderr_fd is not None:
            os.dup2(_saved_stderr_fd, 2)
            os.close(_saved_stderr_fd)
        if _devnull_fd is not None:
            os.close(_devnull_fd)
        
        _fd_redirected = False
        _saved_stdout_fd = None
        _saved_stderr_fd = None
        _devnull_fd = None
    except Exception:
        pass

def configure_logging(verbose: bool = False):
    """
    Configures global logging for llama.cpp and CLIP.
    
    If verbose is False:
    1. Installs a no-op callback to silence llama.cpp logs (thread-safe)
    2. Redirects stdout/stderr FDs to /dev/null to suppress CLIP logs
    
    This affects the global process state.
    """
    if verbose:
        return

    global _llama_log_callback
    
    # Set up llama.cpp callback if not already done
    if _llama_log_callback is None:
        try:
            from llama_cpp import llama_log_set
            
            # Define the callback type: void (*)(enum ggml_log_level level, const char * text, void * user_data)
            # enum ggml_log_level is an int
            CALLBACK_TYPE = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p)
            
            # Create the C callback
            _llama_log_callback = CALLBACK_TYPE(_mute_log_callback)
            
            # Register it
            llama_log_set(_llama_log_callback, ctypes.c_void_p())
            
        except ImportError:
            # llama-cpp-python might not be installed or version mismatch
            pass
        except Exception:
            # Fallback if something goes wrong with ctypes
            pass
    
    # Redirect FDs for CLIP/other C libraries
    _redirect_fds_to_devnull()


class SuppressLlamaLogs:
    """
    Context manager to suppress llama.cpp and CLIP logs.
    Handles both callback-based suppression (llama.cpp) and FD redirection (CLIP).
    """
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.fds_redirected = False
        
        if not self.verbose:
            configure_logging(verbose=False)
            self.fds_redirected = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Note: FDs remain redirected globally for the lifetime of the process
        # This is intentional for thread safety
        pass
