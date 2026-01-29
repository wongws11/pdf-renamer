"""
PDF Renamer CLI - Backward compatibility wrapper

This module is kept for backward compatibility. 
New code should import from the refactored modules:
- config.py: CLI configuration and argument parsing
- renamer.py: Core PDF renaming logic
- main.py: Main entry point and orchestration
- stats.py: Processing statistics
- logger.py: Logging utilities
- file_collector.py: File collection utilities
"""

# Re-export for backward compatibility
from .main import main
from .renamer import PDFRenamer
from .stats import ProcessingStats

__all__ = ["main", "PDFRenamer", "ProcessingStats"]

