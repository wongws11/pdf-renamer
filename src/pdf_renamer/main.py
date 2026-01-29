"""
Main entry point and orchestration
"""

import json
import sys
from pathlib import Path

from .config import parse_args
from .logger import Logger
from .pdf_utils import PDFCache
from .renamer import PDFRenamer


def show_cache_stats(cache_path: Path):
    """Display cache statistics and exit"""
    cache = PDFCache(cache_path)
    stats = cache.stats()
    print("=" * 70)
    print("CACHE STATISTICS")
    print("=" * 70)
    print(f"Cache file: {cache_path}")
    print(f"Total entries: {stats['total_cached']}")
    print(f"First entry: {stats['first_entry']}")
    print(f"Last entry: {stats['last_entry']}")
    cache.close()
    sys.exit(0)


def check_ollama_connection(renamer: PDFRenamer, server_url: str):
    """Check Ollama connection and get model info"""
    print("Checking Ollama connection...")
    if not renamer.check_server():
        print("\n❌ ERROR: Cannot connect to Ollama!")
        print(f"   Make sure it's running at {server_url}")
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


def process_single_file(renamer: PDFRenamer, args) -> dict:
    """Process a single PDF file"""
    output_dir = args.output or args.input_path.parent
    success, message = renamer.process_pdf(
        pdf_path=args.input_path,
        output_dir=output_dir,
        dry_run=not args.execute,
        receipt=args.receipt,
    )
    return {
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


def process_directory(renamer: PDFRenamer, args) -> dict:
    """Process all PDFs in a directory"""
    return renamer.batch_process(
        input_dir=args.input_path,
        output_dir=args.output,
        dry_run=not args.execute,
        delay=args.delay,
        recursive=args.recursive,
        include_images=args.include_images,
        receipt=args.receipt,
    )


def save_results(results: dict, output_file: Path):
    """Save processing results to JSON file"""
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_file}")


def main():
    """Main entry point"""
    args = parse_args()

    # Show cache stats if requested
    if args.cache_stats:
        show_cache_stats(args.cache_path)

    # Initialize renamer
    renamer = PDFRenamer(
        server_url=args.server,
        verbose=args.verbose,
        use_cache=not args.no_cache,
        cache_path=args.cache_path,
        max_workers=args.workers,
        receipt=args.receipt,
    )

    # Check Ollama connection
    check_ollama_connection(renamer, args.server)

    # Process PDFs
    if args.input_path.is_file():
        results = process_single_file(renamer, args)
    else:
        results = process_directory(renamer, args)

    # Save log if requested
    if args.save_log:
        save_results(results, args.save_log)

    # Exit with appropriate code
    sys.exit(0 if renamer.stats.failed == 0 else 1)


if __name__ == "__main__":
    main()
