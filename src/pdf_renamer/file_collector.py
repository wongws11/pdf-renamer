"""
File collection and processing utilities
"""

from pathlib import Path
from typing import List


class FileCollector:
    """Utilities for collecting files to process"""

    @staticmethod
    def collect_files(
        input_dir: Path, recursive: bool, include_images: bool
    ) -> List[Path]:
        """Efficiently collect all files to process"""
        all_files = []

        if recursive:
            all_files.extend(sorted(input_dir.rglob("*.pdf")))
            if include_images:
                for pattern in ["*.jpg", "*.jpeg", "*.JPG", "*.JPEG", "*.png", "*.PNG"]:
                    all_files.extend(sorted(input_dir.rglob(pattern)))
        else:
            all_files.extend(sorted(input_dir.glob("*.pdf")))
            if include_images:
                for pattern in ["*.jpg", "*.jpeg", "*.JPG", "*.JPEG", "*.png", "*.PNG"]:
                    all_files.extend(sorted(input_dir.glob(pattern)))

        # Remove duplicates while preserving order
        seen = set()
        unique_files = []
        for f in all_files:
            if str(f) not in seen:
                seen.add(str(f))
                unique_files.append(f)

        return sorted(unique_files)
