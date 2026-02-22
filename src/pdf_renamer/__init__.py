"""
PDF Renamer - AI-powered PDF document classification and renaming.

Main package initialization.
"""

from .pdf_utils import (
    PDFCache,
    PDFConverter,
    FileUtils,
    ResponseParser,
    FilenameGenerator,
    LLMAnalyzer,
    ConnectionPool,
)
from .cli import PDFRenamer, ProcessingStats

__version__ = "1.3.0"
__author__ = "Wing Wong"

__all__ = [
    "PDFCache",
    "PDFConverter",
    "FileUtils",
    "ResponseParser",
    "FilenameGenerator",
    "LLMAnalyzer",
    "ConnectionPool",
    "PDFRenamer",
    "ProcessingStats",
]
