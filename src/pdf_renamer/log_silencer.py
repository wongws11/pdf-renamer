import os
import sys

class SuppressLlamaLogs:
    """Context manager to suppress stdout and stderr at the C-level (file descriptor level)"""
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.fd_null = None
        self.old_stderr = None
        self.old_stdout = None

    def __enter__(self):
        if self.verbose:
            return self

        self.fd_null = os.open(os.devnull, os.O_WRONLY)
        self.old_stderr = os.dup(sys.stderr.fileno())
        self.old_stdout = os.dup(sys.stdout.fileno())
        
        # Flush to make sure nothing is caught in buffers
        sys.stderr.flush()
        sys.stdout.flush()

        os.dup2(self.fd_null, sys.stderr.fileno())
        os.dup2(self.fd_null, sys.stdout.fileno())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.verbose:
            return

        # Flush again before restoring
        sys.stderr.flush()
        sys.stdout.flush()
        
        # Restore old descriptors
        os.dup2(self.old_stderr, sys.stderr.fileno())
        os.dup2(self.old_stdout, sys.stdout.fileno())
        
        # Close the duplicated descriptors
        os.close(self.fd_null)
        os.close(self.old_stderr)
        os.close(self.old_stdout)
