"""
Main entry point for running the PDF Renamer as a module.

Usage: python -m pdf_renamer [arguments]
"""

import sys
from pathlib import Path

# Ensure the package can be imported when run as a PyInstaller bundle
if __name__ == "__main__":
    # Add src directory to path so pdf_renamer can be found
    current_dir = Path(__file__).parent.parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    
    from pdf_renamer.cli import main
    main()
