# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-01-20

### Added

- `--receipt` option to change naming convention for receipt files.

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

### Features
- Vision model analysis for automatic document classification
- Configurable Ollama server connection
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
