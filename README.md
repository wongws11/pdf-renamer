# PDF Renamer 📄✨

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Automatically rename PDFs and images using a vision-language model (Qwen3.5) running locally. Perfect for organizing document collections without cloud dependencies.

## Key Features

- **Local AI Processing**: Uses Qwen3.5 directly via `llama.cpp` for privacy and offline usage. No external API keys needed.
- **Auto-Download & Auto-Size**: Automatically fetches the right model from HuggingFace based on your machine's memory — `unsloth/Qwen3.5-27B-GGUF` (≥30 GB RAM), `unsloth/Qwen3.5-9B-GGUF` (≥16 GB), or `unsloth/Qwen3.5-4B-GGUF` otherwise. Override with `--model-size`.
- **High Accuracy**: Specifically optimized for reading and summarizing invoices, receipts, and forms.
- **Smart Formatting**: Extracts dates, descriptions, and IDs into consistent filenames (`YYYY-MM-DD_Description_ID.pdf`).
- **Receipt Mode**: specialized formatting for thermal receipts.
- **Fast Caching**: SQLite-backed caching prevents re-analyzing identical files, saving time on subsequent runs.
- **Multi-threaded**: Processes multiple files simultaneously for significantly better throughput.

## Prerequisites

- **Python 3.12+**
- **Poppler**: Required for converting PDF pages to images.

### Installing Poppler

**macOS (Homebrew)**
```bash
brew install poppler
```

**Ubuntu/Debian**
```bash
sudo apt-get install poppler-utils
```

**Windows**
Download and extract the latest [poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases/), and add the `bin/` directory to your system PATH.

## Installation

We recommend installing `pdf-renamer` globally from your local checkout using [`uv`](https://docs.astral.sh/uv/getting-started/installation/). This keeps dependencies such as `llama-cpp-python` isolated from your other Python projects while making the `pdf-renamer` command available on your PATH.

```bash
uv tool install --python 3.12 --editable .
```

The editable installation reflects source-code changes immediately. Reinstall it after changing project dependencies or packaging metadata:
```bash
uv tool install --python 3.12 --editable --force .
```

### Local Development / Manual Installation

To modify the code, use `uv` to create and synchronize the project environment:

```bash
# Clone the repository
git clone https://github.com/wongws11/pdf-renamer.git
cd pdf-renamer

# Create the environment and install the application and development dependencies
uv sync

# Run the test suite
uv run pytest
```

## Quick Start

Run the tool on a single file or a directory of PDFs:

```bash
# Dry run on a single file (preview changes)
pdf-renamer document.pdf

# Actually rename the file
pdf-renamer document.pdf -e

# Process an entire directory of PDFs recursively and apply changes
pdf-renamer ./invoices/ -e -r
```

*Note: On the first run, it will download the Qwen3.5 model selected for your machine (~4 GB for 4B, ~7 GB for 9B, ~18 GB for 27B).*

## Command Line Arguments

| Argument | Short | Type | Default | Description |
|----------|-------|------|---------|-------------|
| `input_path` | — | Path | — | **Required.** Input directory or PDF/JPG/PNG file path |
| `--output` | `-o` | Path | Same as input | Output directory for renamed files |
| `--execute` | `-e` | Flag | False | Actually rename files (default is dry-run mode) |
| `--recursive` | `-r` | Flag | False | Recursively process files in subdirectories |
| `--receipt` | — | Flag | False | Receipt mode: use `date_storename_description_id` format |
| `--verbose` | `-v` | Flag | False | Enable verbose logging (shows model loading details) |
| `--delay` | `-d` | Float | 0.5 | Delay between file processing in seconds |
| `--workers` | `-w` | Integer | 4 | Number of worker threads for parallel processing |
| `--save-log` | — | Path | — | Save processing results to JSON file |
| `--no-cache` | — | Flag | False | Disable cache (re-analyze all PDFs, slower) |
| `--cache-path` | — | Path | `~/.pdf-renamer/cache.db` | Custom path to cache database |
| `--cache-stats` | — | Flag | False | Show cache statistics and exit |
| `--no-image` | — | Flag | False | Exclude JPG and PNG files from processing |
| `--model-size` | — | Choice | `auto` | Built-in vision model size: `auto`, `27b`, `9b`, or `4b` |

### Examples

```bash
# Process all PDFs in a directory (dry-run)
pdf-renamer ./documents/

# Process and rename files
pdf-renamer ./documents/ -e

# Process recursively with custom output directory
pdf-renamer ./documents/ -e -r -o ./renamed/

# Process receipts with receipt-specific format
pdf-renamer ./receipts/ -e --receipt

# Verbose output with custom delay between files
pdf-renamer ./documents/ -e -v --delay 1.0

# Process with custom number of workers
pdf-renamer ./documents/ -e -w 8

# Save results to JSON and use custom cache location
pdf-renamer ./documents/ -e --save-log results.json --cache-path /tmp/cache.db

# Show cache statistics
pdf-renamer --cache-stats

# Force re-analysis (skip cache)
pdf-renamer ./documents/ -e --no-cache

# Exclude images from processing
pdf-renamer ./mixed_files/ -e --no-image

# Force a specific model size instead of auto-detection
pdf-renamer ./documents/ -e --model-size 9b
```

## Architecture & Code Structure

The project is structured into modular components:

- `cli.py` & `main.py`: CLI parsing and program entry point
- `renamer.py`: Orchestrates the renaming logic and handles cache interactions
- `pdf_utils.py`: Contains core utilities including the `LLMAnalyzer` (managing the `llama-cpp-python` session) and file operations
- `stats.py`: Tracks success/failure/skip statistics
- `logger.py`: Custom logging utility

## Troubleshooting

### Model Loading Error

```
ERROR: Model failed to load!
```
**Solution**: Ensure you have enough disk space (at least 3GB free) and that your system meets the requirements for running local LLMs. If the download is interrupted, clearing your Hugging Face cache (`~/.cache/huggingface/hub/`) and retrying may help.

### PDF2Image Error
```
pdf2image.exceptions.PDFInfoNotInstalledError: Unable to get page count.
```
**Solution**: This happens when Poppler is not installed or not in your system PATH. See the Prerequisites section above.

## Acknowledgements

- [HuggingFace](https://huggingface.co/) - For model distribution
- [llama.cpp](https://github.com/ggerganov/llama.cpp) & [llama-cpp-python](https://github.com/abetlen/llama-cpp-python) - For running local LLMs efficiently
- [Qwen](https://qwenlm.github.io/) - For their incredible open source vision models
