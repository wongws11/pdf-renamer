"""
PDF Renamer CLI - Automatically rename PDFs using Qwen2-VL vision model
Optimized for batch processing large volumes of files with performance enhancements.
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from .pdf_utils import (
    FilenameGenerator,
    FileUtils,
    LLMAnalyzer,
    PDFCache,
    PDFConverter,
    ResponseParser,
)


class ProcessingStats:
    """Track processing statistics"""

    def __init__(self):
        self.processed = 0
        self.failed = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.skipped = 0

    def __str__(self) -> str:
        total = self.processed + self.failed + self.skipped
        hit_rate = (
            (self.cache_hits / (self.cache_hits + self.cache_misses) * 100)
            if (self.cache_hits + self.cache_misses) > 0
            else 0
        )

        return f"""
SUMMARY
{'='*70}
Total processed: {self.processed}/{total}
Failed: {self.failed}/{total}
Skipped: {self.skipped}/{total}

Cache Statistics:
  Cache hits: {self.cache_hits} (reused previous analysis)
  Cache misses: {self.cache_misses} (new LLM analysis)
  Hit rate: {hit_rate:.1f}%
"""


class PDFRenamer:
    def __init__(
        self,
        server_url: str = "http://127.0.0.1:8080",
        verbose: bool = False,
        use_cache: bool = True,
        cache_path: Optional[Path] = None,
        max_workers: int = 4,
    ):
        self.server_url = server_url
        self.verbose = verbose
        self.max_workers = max_workers

        # Initialize statistics
        self.stats = ProcessingStats()

        # Initialize utilities
        self.llm_analyzer = LLMAnalyzer(server_url)
        self.pdf_converter = PDFConverter()
        self.file_utils = FileUtils()
        self.response_parser = ResponseParser()
        self.filename_generator = FilenameGenerator()

        # Initialize cache with connection pooling (always keep cache for writing)
        self.use_cache = use_cache
        self.cache = PDFCache(cache_path or Path("pdf_cache.db"))

    def log(self, message: str, level: str = "INFO"):
        """Simple logging with timestamp"""
        if level == "DEBUG" and not self.verbose:
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def check_server(self) -> bool:
        """Verify Ollama is running"""
        return self.llm_analyzer.check_server()

    def process_pdf(
        self,
        pdf_path: Path,
        output_dir: Path,
        dry_run: bool = True,
        preserve_structure: bool = False,
        base_input_dir: Optional[Path] = None,
    ) -> Tuple[bool, str]:
        """Process single PDF file with optimized cache lookups"""

        if not pdf_path.exists():
            return False, "File not found"

        try:
            # Get file extension
            file_ext = pdf_path.suffix.lower()
            if file_ext.lower() not in [".pdf", ".jpg", ".jpeg", ".png"]:
                return False, f"Unsupported file type: {file_ext}"

            # Check if already renamed (early exit)
            if self.use_cache and self.cache:
                renamed_path = self.cache.get_renamed_file(str(pdf_path))
                if renamed_path:
                    return True, renamed_path

            # Calculate checksum
            checksum = self.file_utils.calculate_checksum(pdf_path)

            # Check cache first (only if cache is enabled)
            cached_result = None
            if self.use_cache and self.cache:
                cached_result = self.cache.get(checksum)
                if cached_result:
                    self.stats.cache_hits += 1
                    return self._apply_filename(
                        pdf_path,
                        output_dir,
                        cached_result,
                        dry_run,
                        preserve_structure,
                        base_input_dir,
                        file_ext,
                        True,
                    )

            # Cache miss - analyze with LLM
            self.stats.cache_misses += 1

            if self.verbose:
                self.log(f"Processing {pdf_path.name}...")

            try:
                if file_ext == ".pdf":
                    image = self.pdf_converter.pdf_to_image(pdf_path)
                elif file_ext in [".jpg", ".jpeg", ".png"]:
                    image = self.pdf_converter.load_jpg_image(pdf_path)
                else:
                    return False, f"Unsupported file type: {file_ext}"
            except Exception as e:
                return False, str(e)

            if not image:
                return False, "Image conversion failed"

            # Encode image
            image_base64 = self.pdf_converter.image_to_base64(image)

            # Analyze with LLM
            if self.verbose:
                self.log("Analyzing with LLM...")

            response = self.llm_analyzer.analyze_document(image_base64, pdf_path.name)

            # Parse response
            date, description, doc_id = self.response_parser.parse_response(
                response, pdf_path.name
            )

            # Always cache the result (even if cache is disabled, we update it)
            self.cache.set(
                checksum,
                pdf_path.name,
                date,
                description,
                doc_id,
                pdf_path.stat().st_size,
            )
            if self.verbose:
                self.log(f"Cached analysis for {pdf_path.name}", "DEBUG")

            return self._apply_filename(
                pdf_path,
                output_dir,
                (date, description, doc_id),
                dry_run,
                preserve_structure,
                base_input_dir,
                file_ext,
                False,
            )

        except Exception as e:
            error_msg = str(e)
            self.log(f"✗ {pdf_path.name}: {error_msg}", "ERROR")
            return False, error_msg

    def _apply_filename(
        self,
        pdf_path: Path,
        output_dir: Path,
        cached_data: Tuple[Optional[str], str, Optional[str]],
        dry_run: bool,
        preserve_structure: bool,
        base_input_dir: Optional[Path],
        file_ext: str,
        from_cache: bool,
    ) -> Tuple[bool, str]:
        """Apply filename to file"""
        date, description, doc_id = cached_data

        # Generate new filename
        new_filename = self.filename_generator.generate_filename(
            date, description, doc_id, 0, file_ext
        )

        # Determine output path
        if preserve_structure and base_input_dir:
            relative_path = pdf_path.parent.relative_to(base_input_dir)
            final_output_dir = output_dir / relative_path
            final_output_dir.mkdir(parents=True, exist_ok=True)
        else:
            final_output_dir = output_dir

        if dry_run:
            display_path = str(final_output_dir / new_filename)
            cache_flag = "[CACHED]" if from_cache else ""
            self.log(f"{pdf_path} → {display_path} {cache_flag} [DRY RUN]")
            return True, new_filename
        else:
            new_path = final_output_dir / new_filename

            # Check if new filename is same as current filename
            if new_path == pdf_path:
                self.log(f"⊘ {pdf_path.name}: Already has same name, skipping")
                self.stats.skipped += 1
                return True, str(pdf_path)

            # Handle duplicates
            counter = 1
            while new_path.exists():
                new_filename = self.filename_generator.generate_filename(
                    date, description, doc_id, counter, file_ext
                )
                new_path = final_output_dir / new_filename
                counter += 1

            pdf_path.rename(new_path)
            # Track the renamed file
            checksum = self.file_utils.calculate_checksum(new_path)
            self.cache.track_renamed_file(str(pdf_path), str(new_path), checksum)

            cache_flag = "[CACHED]" if from_cache else ""
            self.log(f"✓ {pdf_path.name} → {new_path} {cache_flag}")
            return True, str(new_path)

    def _collect_files(
        self, input_dir: Path, recursive: bool, include_images: bool
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

    def batch_process(
        self,
        input_dir: Path,
        output_dir: Optional[Path] = None,
        dry_run: bool = True,
        delay: float = 0.5,
        recursive: bool = False,
        include_images: bool = True,
    ) -> dict:
        """Process all PDFs in directory with optimized performance"""

        if not input_dir.exists() or not input_dir.is_dir():
            self.log(f"Input directory not found: {input_dir}", "ERROR")
            return {"success": [], "failed": []}

        # Use input dir as output if not specified
        if output_dir is None:
            output_dir = input_dir
        else:
            output_dir.mkdir(parents=True, exist_ok=True)

        # Collect all files
        all_files = self._collect_files(input_dir, recursive, include_images)
        total = len(all_files)

        if total == 0:
            self.log("No PDF files found in directory", "WARNING")
            return {"success": [], "failed": []}

        self.log(
            f"Found {total} file(s) to process {'(recursive)' if recursive else ''}"
        )
        self.log(f"Mode: {'DRY RUN' if dry_run else 'RENAME'}")
        print()

        results = {"success": [], "failed": []}

        # Process files
        for i, pdf_file in enumerate(all_files, 1):
            # Show relative path for nested files
            if recursive:
                display_name = str(pdf_file.relative_to(input_dir))
            else:
                display_name = pdf_file.name

            print(f"[{i}/{total}] {display_name}... ", end="", flush=True)

            success, result = self.process_pdf(
                pdf_file,
                output_dir,
                dry_run,
                preserve_structure=recursive,
                base_input_dir=input_dir if recursive else None,
            )

            if success:
                results["success"].append({"original": pdf_file.name, "new": result})
                self.stats.processed += 1
                print("✓")
            else:
                results["failed"].append({"file": pdf_file.name, "error": result})
                self.stats.failed += 1
                print("✗")

            # Small delay to avoid overwhelming the server
            if i < total:
                time.sleep(delay)

        # Print summary
        print("\n" + "=" * 70)
        print(str(self.stats))

        if results["failed"]:
            print("Failed files:")
            for item in results["failed"]:
                print(f"  - {item['file']}: {item['error']}")

        if self.use_cache and self.cache:
            cache_stats = self.cache.stats()
            print(f"\nTotal cache entries: {cache_stats['total_cached']}")

        return results

    def __del__(self):
        """Cleanup resources"""
        if self.cache:
            self.cache.close()
        self.llm_analyzer.close()


def main():
    parser = argparse.ArgumentParser(
        description="Automatically rename PDFs using vision model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Before running, start Ollama:
  ollama serve
        """,
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
        "-s",
        "--server",
        default="http://127.0.0.1:11434",
        help="Ollama server URL (default: http://127.0.0.1:11434)",
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

    parser.add_argument(
        "--cache-path",
        type=Path,
        default=Path("pdf_cache.db"),
        help="Path to cache database (default: pdf_cache.db)",
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

    args = parser.parse_args()

    # Show cache stats if requested
    if args.cache_stats:
        cache = PDFCache(args.cache_path)
        stats = cache.stats()
        print("=" * 70)
        print("CACHE STATISTICS")
        print("=" * 70)
        print(f"Cache file: {args.cache_path}")
        print(f"Total entries: {stats['total_cached']}")
        print(f"First entry: {stats['first_entry']}")
        print(f"Last entry: {stats['last_entry']}")
        cache.close()
        sys.exit(0)

    # Initialize renamer
    renamer = PDFRenamer(
        server_url=args.server,
        verbose=args.verbose,
        use_cache=not args.no_cache,
        cache_path=args.cache_path,
        max_workers=args.workers,
    )

    # Check if server is running
    print("Checking Ollama connection...")
    if not renamer.check_server():
        print("\n❌ ERROR: Cannot connect to Ollama!")
        print(f"   Make sure it's running at {args.server}")
        print("\nStart with:")
        print("  ollama serve")
        sys.exit(1)

    print("✓ Connected to Ollama")

    # Get first available model
    print("Detecting available model...")
    model_name = renamer.llm_analyzer.get_first_model()
    if not model_name:
        print("\n❌ ERROR: No models found in Ollama!")
        print("Pull a model first with: ollama pull qwen2-vl")
        sys.exit(1)

    print(f"✓ Using model: {model_name}\n")

    # Process PDFs
    if args.input_path.is_file():
        # Single file processing
        output_dir = args.output or args.input_path.parent
        success, message = renamer.process_pdf(
            pdf_path=args.input_path, output_dir=output_dir, dry_run=not args.execute
        )
        results = {
            "files_processed": 1 if success else 0,
            "files_failed": 0 if success else 1,
            "files": [
                {
                    "file": str(args.input_path),
                    "status": "success" if success else "failed",
                    "message": message,
                }
            ],
        }
    else:
        # Directory processing
        results = renamer.batch_process(
            input_dir=args.input_path,
            output_dir=args.output,
            dry_run=not args.execute,
            delay=args.delay,
            recursive=args.recursive,
            include_images=args.include_images,
        )

    # Save log if requested
    if args.save_log:
        with open(args.save_log, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {args.save_log}")

    # Exit with appropriate code
    sys.exit(0 if renamer.stats.failed == 0 else 1)


if __name__ == "__main__":
    main()
