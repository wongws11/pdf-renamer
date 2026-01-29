"""
Logger for PDF Renamer
"""

from datetime import datetime


class Logger:
    """Simple logging with timestamp"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp"""
        if level == "DEBUG" and not self.verbose:
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def info(self, message: str):
        """Log info message"""
        self.log(message, "INFO")

    def error(self, message: str):
        """Log error message"""
        self.log(message, "ERROR")

    def debug(self, message: str):
        """Log debug message"""
        self.log(message, "DEBUG")

    def warning(self, message: str):
        """Log warning message"""
        self.log(message, "WARNING")
