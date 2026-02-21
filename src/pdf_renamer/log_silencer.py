import ctypes
import os
import sys
from typing import Optional, Callable

# Global variable to hold the callback so it's not garbage collected
_llama_log_callback = None

def _mute_log_callback(level, message, user_data):
    """No-op callback to suppress logs"""
    pass

def configure_logging(verbose: bool = False):
    """
    Configures global logging for llama.cpp.
    
    If verbose is False, installs a no-op callback to silence all llama.cpp logs.
    This is thread-safe and affects the global process state.
    """
    if verbose:
        return

    global _llama_log_callback
    
    if _llama_log_callback is not None:
        return

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
    except Exception as e:
        # Fallback if something goes wrong with ctypes
        if verbose:
            print(f"Warning: Failed to suppress llama.cpp logs: {e}", file=sys.stderr)

class SuppressLlamaLogs:
    """
    Legacy Context manager.
    Now just a wrapper that ensures global logging is configured if not already.
    Kept for backward compatibility but largely redundant if configure_logging is called at startup.
    """
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        if not self.verbose:
            configure_logging(verbose=False)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
