# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-02-21

### Added
- **Comprehensive logging suppression** for both llama.cpp and CLIP vision encoder
  - File descriptor redirection to `/dev/null` for C-level logs
  - Thread-safe llama.cpp callback-based suppression
  - Early logging configuration in main entry point before model initialization
- **Complete CLI documentation** in README.md
  - New "Command Line Arguments" table with all 13 parameters clearly documented
  - "Examples" section with 8 practical usage patterns covering common scenarios
  - Clear descriptions for each argument and their default values

### Fixed
- **CLIP vision encoder logs** no longer print in quiet mode
  - Previously only llama.cpp logs were suppressed via callback
  - CLIP logs from the vision model initialization and inference were still visible
  - Solution: Dual suppression using callbacks (llama.cpp) + FD redirection (CLIP/other C libraries)
- **Logging behavior** now correctly suppresses all C-level output by default
  - Verbose mode (`-v`) shows all logs as expected
  - Non-verbose mode suppresses all C-level output from both llama.cpp and CLIP

### Changed
- `configure_logging()` function signature unchanged but implementation enhanced
  - Now handles both llama.cpp callback registration AND file descriptor redirection
  - Supports suppression of logs from multiple C libraries simultaneously
- Updated `SuppressLlamaLogs` class to reflect dual suppression approach
- Main entry point (`main.py`) now calls `configure_logging()` early before model initialization

### Technical Details
- File descriptor redirection approach: stdout (FD 1) and stderr (FD 2) redirected to `/dev/null`
- Redirection applied globally for process lifetime (thread-safe)
- Callback approach remains for llama.cpp-specific logging control
- Fallback mechanisms in place for both suppression methods

## [1.1.0] - 2026-02-20

### Added
- **Local LLM inference** via `llama-cpp-python` replacing Ollama
  - Qwen2.5-VL-3B built-in inference without external HTTP service
  - Auto-download of models from HuggingFace on first run
  - Automatic Metal/CUDA GPU acceleration (`n_gpu_layers=-1`)
- **Comprehensive test suite** with 100% passing tests
  - 6 unit tests for PDF utilities and caching functionality
  - 1 integration test for renamer orchestration
  - 3 functional tests for CLI operations
- **Enhanced GitHub Actions CI/CD**
  - Binary builds for Windows, macOS (x86_64 + arm64), and Linux
  - Uses `pip install .` for consistent dependency resolution

### Removed
- Ollama server dependency (external HTTP service requirement)
- `requests` library (no longer needed for API calls)
- `requirements.txt` (consolidated into `pyproject.toml` as single source of truth)

### Fixed
- Pylance type errors in import statements and function signatures
- Model initialization GPU acceleration now automatic and reliable
- Cache entry validation prevents stale data from files with identical names

### Changed
- Version bumped to 1.1.0 (minor feature addition)
- PyInstaller specification updated for `llama_cpp` and `huggingface_hub` imports
- GitHub Actions workflow simplified to use `pip install .` instead of requirements.txt

## [1.0.1] - 2026-01-27

### Added
- CI/CD workflows for building and releasing binaries for Windows, macOS (x86_64 and arm64), and Linux.

## [1.0.0] - 2026-01-27

### Added
- AI-powered PDF classification using Qwen2.5-VL vision model
- Smart caching with SQLite database to avoid re-analyzing documents
- Dry-run mode to preview changes before execution
- Recursive directory processing
- Batch file processing with configurable delays
- Cache statistics and management commands
- Support for PDF, JPG, and PNG files
- Thread-safe connection pooling for database operations
- Persistent file rename tracking
- `--receipt` option to change naming convention for receipt files
- Vision model analysis for automatic document classification
- Configurable Ollama server connection (pre 1.1.0)
- Customizable output directory structure
- Directory structure preservation option
- Comprehensive logging and error handling
- JSON output for processing results
- Efficient memory management for large batches

## [1.0] - Initial Release

### Added
- Basic PDF to image conversion
- LLM-based document analysis
- File naming and organization

---

[1.2.0]: https://github.com/wongws11/pdf-renamer/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/wongws11/pdf-renamer/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/wongws11/pdf-renamer/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/wongws11/pdf-renamer/compare/v1.0...v1.0.0
