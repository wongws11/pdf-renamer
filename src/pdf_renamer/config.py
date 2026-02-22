"""
CLI configuration and argument parsing
"""

import argparse
from pathlib import Path


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser"""
    parser = argparse.ArgumentParser(
        description="Automatically rename PDFs using vision model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "input_path", type=Path, help="Input directory or PDF/JPG file path"
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output directory for renamed files (default: same as input)",
    )

    parser.add_argument(
        "-e",
        "--execute",
        action="store_true",
        help="Actually rename files (default is dry-run)",
    )

    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Recursively process PDFs in subdirectories",
    )

    parser.add_argument(
        "--receipt",
        action="store_true",
        help="Receipt mode: use date_storename_description_id format",
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )

    parser.add_argument(
        "-d",
        "--delay",
        type=float,
        default=0.5,
        help="Delay between files in seconds (default: 0.5)",
    )

    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=4,
        help="Number of worker threads for processing (default: 4)",
    )

    parser.add_argument("--save-log", type=Path, help="Save results to JSON file")

    parser.add_argument(
        "--no-cache", action="store_true", help="Disable cache (re-analyze all PDFs)"
    )

    default_cache_dir = Path.home() / ".pdf-renamer"
    default_cache_dir.mkdir(parents=True, exist_ok=True)
    default_cache_path = default_cache_dir / "cache.db"

    parser.add_argument(
        "--cache-path",
        type=Path,
        default=default_cache_path,
        help=f"Path to cache database (default: {default_cache_path})",
    )

    parser.add_argument(
        "--cache-stats", action="store_true", help="Show cache statistics and exit"
    )

    parser.add_argument(
        "--no-image",
        action="store_false",
        dest="include_images",
        default=True,
        help="Exclude JPG and PNG files from processing",
    )

    return parser


def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = create_parser()
    return parser.parse_args()
