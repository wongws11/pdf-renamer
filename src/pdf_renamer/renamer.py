"""
Core PDF renaming logic
"""

from pathlib import Path
from typing import Optional, Tuple

from .file_collector import FileCollector
from .logger import Logger
from .pdf_utils import (
    FilenameGenerator,
    FileUtils,
    LLMAnalyzer,
    PDFCache,
    PDFConverter,
    ResponseParser,
)
from .stats import ProcessingStats


class PDFRenamer:
    """Main PDF renaming orchestrator"""

    def __init__(
        self,
        verbose: bool = False,
        use_cache: bool = True,
        cache_path: Optional[Path] = None,
        max_workers: int = 4,
        receipt: bool = False,
    ):
        self.verbose = verbose
        self.max_workers = max_workers
        self.receipt = receipt

        # Initialize logger
        self.logger = Logger(verbose)

        # Initialize statistics
        self.stats = ProcessingStats()

        # Initialize utilities
        self.llm_analyzer = LLMAnalyzer(verbose=verbose)
        self.pdf_converter = PDFConverter()
        self.file_utils = FileUtils()
        self.response_parser = ResponseParser()
        self.filename_generator = FilenameGenerator()
        self.file_collector = FileCollector()

        # Initialize cache with connection pooling (always keep cache for writing)
        self.use_cache = use_cache
        default_cache_path = Path.home() / ".pdf-renamer" / "cache.db"
        self.cache = PDFCache(cache_path or default_cache_path)

    def check_server(self) -> bool:
        """Verify model is loaded"""
        return self.llm_analyzer.check_server()

    def process_pdf(
        self,
        pdf_path: Path,
        output_dir: Path,
        dry_run: bool = True,
        preserve_structure: bool = False,
        base_input_dir: Optional[Path] = None,
        receipt: bool = False,
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
                # Validate cache entry by filename to ensure file content hasn't changed
                # This prevents different PDFs with the same name from hitting old cache
                if self.cache.validate_cache_entry(pdf_path, checksum):
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
                            receipt,
                        )

            # Cache miss - analyze with LLM
            self.stats.cache_misses += 1

            if self.verbose:
                self.logger.debug(f"Processing {pdf_path.name}...")

            # Convert file to image
            image = self._load_image(pdf_path, file_ext)
            if not image:
                return False, "Image conversion failed"

            # Encode image
            image_base64 = self.pdf_converter.image_to_base64(image)

            # Analyze with LLM
            if self.verbose:
                self.logger.debug("Analyzing with LLM...")

            response = self.llm_analyzer.analyze_document(
                image_base64, pdf_path.name, receipt=receipt
            )

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
                self.logger.debug(f"Cached analysis for {pdf_path.name}")

            return self._apply_filename(
                pdf_path,
                output_dir,
                (date, description, doc_id),
                dry_run,
                preserve_structure,
                base_input_dir,
                file_ext,
                False,
                receipt,
            )

        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"{pdf_path.name}: {error_msg}")
            return False, error_msg

    def _load_image(self, file_path: Path, file_ext: str):
        """Load image from PDF or image file"""
        try:
            if file_ext == ".pdf":
                return self.pdf_converter.pdf_to_image(file_path)
            elif file_ext in [".jpg", ".jpeg", ".png"]:
                return self.pdf_converter.load_jpg_image(file_path)
            else:
                return None
        except Exception as e:
            raise Exception(f"Failed to load image from {file_path.name}: {str(e)}")

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
        receipt: bool = False,
    ) -> Tuple[bool, str]:
        """Apply filename to file"""
        date, description, doc_id = cached_data

        # Generate new filename
        new_filename = self.filename_generator.generate_filename(
            date, description, doc_id, 0, file_ext, receipt
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
            self.logger.info(f"{pdf_path} → {display_path} {cache_flag} [DRY RUN]")
            return True, new_filename
        else:
            return self._rename_file(
                pdf_path, final_output_dir, new_filename, date, description, doc_id, file_ext, from_cache, receipt
            )

    def _rename_file(
        self,
        pdf_path: Path,
        output_dir: Path,
        new_filename: str,
        date: Optional[str],
        description: str,
        doc_id: Optional[str],
        file_ext: str,
        from_cache: bool,
        receipt: bool,
    ) -> Tuple[bool, str]:
        """Rename file and handle duplicates"""
        new_path = output_dir / new_filename

        # Check if new filename is same as current filename
        if new_path == pdf_path:
            self.logger.info(f"⊘ {pdf_path.name}: Already has same name, skipping")
            self.stats.skipped += 1
            return True, str(pdf_path)

        # Handle duplicates
        counter = 1
        while new_path.exists():
            new_filename = self.filename_generator.generate_filename(
                date, description, doc_id, counter, file_ext, receipt
            )
            new_path = output_dir / new_filename
            counter += 1

        pdf_path.rename(new_path)
        # Track the renamed file
        checksum = self.file_utils.calculate_checksum(new_path)
        self.cache.track_renamed_file(str(pdf_path), str(new_path), checksum)

        cache_flag = "[CACHED]" if from_cache else ""
        self.logger.info(f"✓ {pdf_path.name} → {new_path.name} {cache_flag}")
        return True, str(new_path)

    def batch_process(
        self,
        input_dir: Path,
        output_dir: Optional[Path] = None,
        dry_run: bool = True,
        delay: float = 0.5,
        recursive: bool = False,
        include_images: bool = True,
        receipt: bool = False,
    ) -> dict:
        """Process all PDFs in directory with optimized performance"""
        import time

        if not input_dir.exists() or not input_dir.is_dir():
            self.logger.error(f"Input directory not found: {input_dir}")
            return {"success": [], "failed": []}

        # Use input dir as output if not specified
        if output_dir is None:
            output_dir = input_dir
        else:
            output_dir.mkdir(parents=True, exist_ok=True)

        # Collect all files
        all_files = self.file_collector.collect_files(input_dir, recursive, include_images)
        total = len(all_files)

        if total == 0:
            self.logger.warning("No PDF files found in directory")
            return {"success": [], "failed": []}

        self.logger.info(f"Found {total} file(s) to process {'(recursive)' if recursive else ''}")
        self.logger.info(f"Mode: {'DRY RUN' if dry_run else 'RENAME'}")
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
                receipt=receipt,
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
