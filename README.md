# PDF Renamer 📄✨

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Automatically rename PDFs and images using a vision-language model (Qwen2.5-VL) running locally. Perfect for organizing document collections without cloud dependencies.

## Key Features

- **Local AI Processing**: Uses Qwen2.5-VL directly via `llama.cpp` for privacy and offline usage. No external API keys needed.
- **Auto-Download**: Automatically fetches the required models from HuggingFace (`unsloth/Qwen2.5-VL-3B-Instruct-GGUF`).
- **High Accuracy**: Specifically optimized for reading and summarizing invoices, receipts, and forms.
- **Smart Formatting**: Extracts dates, descriptions, and IDs into consistent filenames (`YYYY-MM-DD_Description_ID.pdf`).
- **Receipt Mode**: specialized formatting for thermal receipts.
- **Fast Caching**: SQLite-backed caching prevents re-analyzing identical files, saving time on subsequent runs.
- **Multi-threaded**: Processes multiple files simultaneously for significantly better throughput.

## Prerequisites

- **Python 3.13+**
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

```bash
# Clone the repository
git clone https://github.com/wongws11/pdf-renamer.git
cd pdf-renamer

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the application
pip install -e .
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

*Note: On the first run, it will download the Qwen2.5-VL model (approx. 2GB).*

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
