"""
Utility classes and functions for PDF processing
"""

import base64
import hashlib
import io
import re
import sqlite3
import subprocess
from pathlib import Path
from typing import Tuple, Optional, Dict, List
import threading

from pdf2image import convert_from_path
from PIL import Image
from huggingface_hub import hf_hub_download
from llama_cpp import Llama
from llama_cpp.llama_chat_format import Qwen25VLChatHandler


# Thread-safe connection pool for database
class ConnectionPool:
    """Simple thread-safe connection pool for SQLite"""

    def __init__(self, db_path: Path, pool_size: int = 5):
        self.db_path = db_path
        self.pool_size = pool_size
        self._connections = []
        self._lock = threading.Lock()
        self._init_pool()

    def _init_pool(self):
        """Initialize connection pool"""
        for _ in range(self.pool_size):
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            self._connections.append(conn)

    def get_connection(self):
        """Get a connection from the pool"""
        with self._lock:
            if self._connections:
                return self._connections.pop()
        return sqlite3.connect(str(self.db_path), check_same_thread=False)

    def return_connection(self, conn):
        """Return a connection to the pool"""
        with self._lock:
            if len(self._connections) < self.pool_size:
                self._connections.append(conn)
            else:
                conn.close()

    def close_all(self):
        """Close all connections in pool"""
        with self._lock:
            for conn in self._connections:
                conn.close()
            self._connections.clear()


class PDFCache:
    """SQLite cache for PDF analysis results with connection pooling"""

    def __init__(self, db_path: Path = Path("pdf_cache.db"), pool_size: int = 5):
        self.db_path = db_path
        self.pool = ConnectionPool(db_path, pool_size)
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        conn = self.pool.get_connection()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pdf_analysis (
                    checksum TEXT PRIMARY KEY,
                    filename TEXT,
                    date TEXT,
                    description TEXT,
                    doc_id TEXT,
                    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    file_size INTEGER
                )
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_checksum ON pdf_analysis(checksum)
            """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS renamed_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_path TEXT UNIQUE,
                    new_path TEXT,
                    checksum TEXT,
                    renamed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_renamed_original ON renamed_files(original_path)
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_renamed_checksum ON renamed_files(checksum)
            """
            )
            conn.commit()
        finally:
            self.pool.return_connection(conn)

    def get(self, checksum: str) -> Optional[Tuple[Optional[str], str, Optional[str]]]:
        """Get cached analysis result by content checksum

        Returns cached result only if checksum matches, ensuring different
        files with the same name won't incorrectly reuse old cache entries.
        """
        conn = self.pool.get_connection()
        try:
            cursor = conn.execute(
                "SELECT date, description, doc_id FROM pdf_analysis WHERE checksum = ?",
                (checksum,),
            )
            row = cursor.fetchone()
            return row if row else None
        finally:
            self.pool.return_connection(conn)

    def validate_cache_entry(self, file_path: Path, checksum: str) -> bool:
        """Validate that a file's current checksum matches its cache entry

        Ensures that if a file with the same name was replaced with different
        content, it won't incorrectly use the old cache. This is a safety check.
        """
        conn = self.pool.get_connection()
        try:
            cursor = conn.execute(
                "SELECT checksum FROM pdf_analysis WHERE filename = ?",
                (file_path.name,),
            )
            row = cursor.fetchone()
            if not row:
                return True  # No cache entry, not a validation failure

            cached_checksum = row[0]
            return cached_checksum == checksum
        finally:
            self.pool.return_connection(conn)

    def set(
        self,
        checksum: str,
        filename: str,
        date: Optional[str],
        description: str,
        doc_id: Optional[str],
        file_size: int,
    ):
        """Cache analysis result"""
        conn = self.pool.get_connection()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO pdf_analysis 
                (checksum, filename, date, description, doc_id, file_size)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (checksum, filename, date, description, doc_id, file_size),
            )
            conn.commit()
        finally:
            self.pool.return_connection(conn)

    def batch_get(
        self, checksums: List[str]
    ) -> Dict[str, Tuple[Optional[str], str, Optional[str]]]:
        """Get multiple cached results efficiently"""
        if not checksums:
            return {}

        conn = self.pool.get_connection()
        try:
            placeholders = ",".join("?" * len(checksums))
            cursor = conn.execute(
                f"""
                SELECT checksum, date, description, doc_id 
                FROM pdf_analysis 
                WHERE checksum IN ({placeholders})
            """,
                checksums,
            )

            return {row[0]: (row[1], row[2], row[3]) for row in cursor.fetchall()}
        finally:
            self.pool.return_connection(conn)

    def stats(self) -> dict:
        """Get cache statistics"""
        conn = self.pool.get_connection()
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM pdf_analysis")
            count = cursor.fetchone()[0]

            cursor = conn.execute(
                """
                SELECT MIN(analyzed_at), MAX(analyzed_at) 
                FROM pdf_analysis
            """
            )
            first, last = cursor.fetchone()

            return {"total_cached": count, "first_entry": first, "last_entry": last}
        finally:
            self.pool.return_connection(conn)

    def is_file_renamed(self, file_path: str) -> bool:
        """Check if a file has already been renamed"""
        conn = self.pool.get_connection()
        try:
            cursor = conn.execute(
                "SELECT 1 FROM renamed_files WHERE original_path = ?", (file_path,)
            )
            return cursor.fetchone() is not None
        finally:
            self.pool.return_connection(conn)

    def track_renamed_file(self, original_path: str, new_path: str, checksum: str):
        """Track a renamed file"""
        conn = self.pool.get_connection()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO renamed_files 
                (original_path, new_path, checksum)
                VALUES (?, ?, ?)
            """,
                (original_path, new_path, checksum),
            )
            conn.commit()
        finally:
            self.pool.return_connection(conn)

    def get_renamed_file(self, file_path: str) -> Optional[str]:
        """Get the new path of a renamed file"""
        conn = self.pool.get_connection()
        try:
            cursor = conn.execute(
                "SELECT new_path FROM renamed_files WHERE original_path = ?",
                (file_path,),
            )
            row = cursor.fetchone()
            return row[0] if row else None
        finally:
            self.pool.return_connection(conn)

    def close(self):
        """Close all database connections"""
        self.pool.close_all()


class PDFConverter:
    """Utility class for PDF to image conversion with memory optimization"""

    # Class-level cache for DPI setting
    DEFAULT_DPI = 300

    @staticmethod
    def pdf_to_image(pdf_path: Path, dpi: int = DEFAULT_DPI) -> Optional[Image.Image]:
        """Convert first page of PDF to image with memory cleanup"""
        try:
            images = convert_from_path(
                pdf_path, dpi=dpi, first_page=1, last_page=1, fmt="png"
            )
            return images[0] if images else None
        except Exception as e:
            raise Exception(f"Failed to convert {pdf_path.name}: {str(e)}")

    @staticmethod
    def load_jpg_image(jpg_path: Path) -> Optional[Image.Image]:
        """Load JPG/PNG file as image with auto-conversion"""
        try:
            image = Image.open(jpg_path)
            # Convert to RGB if necessary for consistency
            if image.mode != "RGB":
                image = image.convert("RGB")
            return image
        except Exception as e:
            raise Exception(f"Failed to load {jpg_path.name}: {str(e)}")

    @staticmethod
    def image_to_base64(image: Image.Image) -> str:
        """Convert PIL Image to base64 string with memory cleanup"""
        buffered = io.BytesIO()
        try:
            image.save(buffered, format="PNG", optimize=True)
            return base64.b64encode(buffered.getvalue()).decode()
        finally:
            buffered.close()


class FileUtils:
    """Utility class for file operations with efficient checksum calculation"""

    CHUNK_SIZE = 65536  # 64KB chunks for better performance

    @staticmethod
    def calculate_checksum(pdf_path: Path) -> str:
        """Calculate SHA256 checksum of file efficiently"""
        sha256_hash = hashlib.sha256()
        with open(pdf_path, "rb") as f:
            for chunk in iter(lambda: f.read(FileUtils.CHUNK_SIZE), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    @staticmethod
    def calculate_checksums_batch(file_paths: List[Path]) -> Dict[str, str]:
        """Calculate checksums for multiple files"""
        return {str(path): FileUtils.calculate_checksum(path) for path in file_paths}


class ResponseParser:
    """Utility class for parsing LLM responses"""

    @staticmethod
    def parse_response(
        llm_response: str, filename: str = ""
    ) -> Tuple[Optional[str], str, Optional[str]]:
        """Parse LLM response into structured data"""
        # Use filename (without extension) as fallback description
        fallback_description = Path(filename).stem if filename else "Document"

        date = None
        description = fallback_description
        doc_id = None

        # Extract date
        date_match = re.search(r"Date:\s*(\d{4}-\d{2}-\d{2})", llm_response)
        if date_match:
            date = date_match.group(1)

        # Extract description
        desc_match = re.search(
            r"Description:\s*(.+?)(?:\n|$)", llm_response, re.IGNORECASE
        )
        if desc_match:
            description = desc_match.group(1).strip()
            description = re.sub(r"[^\w\s-]", "", description)
            description = re.sub(r"\s+", " ", description).strip()

            if description.upper() in ["NONE", "UNKNOWN", ""] or len(description) < 2:
                description = fallback_description
            else:
                description = description[:50]

        # Extract ID
        id_match = re.search(r"ID:\s*(.+?)(?:\n|$)", llm_response, re.IGNORECASE)
        if id_match:
            doc_id = id_match.group(1).strip()
            doc_id = re.sub(r"[^\w\s-]", "", doc_id)
            doc_id = doc_id.replace(" ", "_")

            if doc_id.upper() in ["NONE", "UNKNOWN", "NA", "N_A"] or len(doc_id) < 2:
                doc_id = None
            else:
                doc_id = doc_id[:30]

        return date, description, doc_id


class FilenameGenerator:
    """Utility class for generating PDF filenames"""

    @staticmethod
    def generate_filename(
        date: Optional[str],
        description: str,
        doc_id: Optional[str],
        counter: int = 0,
        file_ext: str = ".pdf",
        receipt: bool = False,
    ) -> str:
        """Create sanitized filename.

        Formats:
        - Normal mode: Description_ID.pdf or YYYY-MM-DD_Description_ID.pdf if date found
        - Receipt mode: YYYY-MM-DD_storename_description_id.pdf (date_storename_description_id)

        If description or doc_id is missing, or marked as NONE, they are omitted.
        """
        parts = []

        # Add date only if available
        if date:
            parts.append(date)

        # In receipt mode, description is treated as storename and doc_id as description
        if receipt and receipt != "NONE":
            # description becomes storename
            storename_clean = description.replace(" ", "_")
            parts.append(storename_clean)

            # doc_id becomes description (if it exists)
            if doc_id and doc_id != "NONE":
                parts.append(doc_id)
        else:
            # Normal mode
            # Add description (replace spaces with underscores)
            description_clean = description.replace(" ", "_")
            parts.append(description_clean)

            # Add ID only if it exists
            if doc_id and doc_id != "NONE":
                parts.append(doc_id)

        # Add counter if needed
        if counter > 0:
            parts.append(f"v{counter}")

        filename = "_".join(parts) + file_ext

        # Ensure reasonable length
        if len(filename) > 200:
            filename = filename[: 197 - len(file_ext)] + file_ext

        return filename

from .log_silencer import SuppressLlamaLogs

class LLMAnalyzer:
    """Utility class for LLM analysis via HuggingFace and llama.cpp"""

    def __init__(self, server_url: str = "", verbose: bool = False):
        # server_url is kept for API compatibility but not used
        self.llm = None
        self.verbose = verbose
        self.repo_id = "unsloth/Qwen2.5-VL-3B-Instruct-GGUF"
        self.model_filename = "Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf"
        self.mmproj_filename = "mmproj-F16.gguf"
        
        # Download and load the model on initialization
        self._initialize_model()

    def _initialize_model(self):
        """Download (if needed) and initialize the model"""
        if self.verbose:
            print(f"Loading vision model (may download on first run)...")
        try:
            with SuppressLlamaLogs(verbose=self.verbose):
                model_path = hf_hub_download(repo_id=self.repo_id, filename=self.model_filename)
                mmproj_path = hf_hub_download(repo_id=self.repo_id, filename=self.mmproj_filename)
                
                chat_handler = Qwen25VLChatHandler(clip_model_path=mmproj_path)
                
                # Using -1 for Metal/GPU support automatically if available
                self.llm = Llama(
                    model_path=model_path,
                    chat_handler=chat_handler,
                    n_ctx=4096,
                    n_gpu_layers=-1,
                    verbose=self.verbose
                )
        except Exception as e:
            raise Exception(f"Failed to initialize model: {str(e)}")

    def check_server(self) -> bool:
        """Verify model is loaded"""
        return self.llm is not None

    def analyze_document(
        self,
        image_base64: str,
        filename: str = "",
        model: str = "",
        receipt: bool = False,
    ) -> str:
        """Send image to the built-in model for analysis"""
        if not self.llm:
            raise Exception("Model is not initialized")

        if receipt:
            # Prompt for receipt mode
            prompt = f"""Analyze this receipt or invoice and provide:

1. Date (YYYY-MM-DD format, or NONE if not visible)
2. Store/Merchant name (the business that issued this receipt - be concise!)
3. Item description or transaction type (primary item purchased or service - or NONE if not visible)

Original filename: {filename}

Consider original filename might contain hints. 
If you consider original filename useful, 
you may use it to infer missing details after careful consideration only if the receipt is unclear.

Format your response EXACTLY as:
Date: [date]
Description: [store/merchant name] [item description or NONE]
ID: [document ID or NONE]

Examples:
Date: 2024-07-12
Description: Walmart Grocery
ID: 1234567890

Date: 2023-05-15
Description: Shell Gas Station Fuel Purchase
ID: NONE

Only extract what you actually see in the receipt."""
        else:
            # Original prompt for normal mode
            prompt = f"""Analyze this document and provide:

1. Date (YYYY-MM-DD format, or NONE if not visible)
2. Brief description (2-4 words maximum - be concise!)
3. Document ID/Reference number (invoice number, reference, policy number, etc. - or NONE if not visible)

Original filename: {filename}

Consider original filename might contain hints. 
If you consider original filename useful, 
you may use it to infer missing details after careful consideration only if the document content is unclear.

Format your response EXACTLY as:
Date: [date]
Description: [short description]
ID: [document ID or NONE]

Examples:
Date: 2024-07-12
Description: Kwik Fit Invoice
ID: 147218533

Date: 2023-05-15
Description: Insurance Policy
ID: POL-2023-5678

Only extract what you actually see in the document."""

        try:
            with SuppressLlamaLogs(verbose=self.verbose):
                response = self.llm.create_chat_completion(
                    max_tokens=256,
                    temperature=0.1,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}},
                                {"type": "text", "text": prompt}
                            ]
                        }
                    ]
                )

            if isinstance(response, dict) and "choices" in response and len(response["choices"]) > 0:
                content = response["choices"][0]["message"].get("content", "")
                if content is None:
                    return ""
                return content
            else:
                raise Exception("Empty response from model")

        except Exception as e:
            raise Exception(f"Model request failed: {str(e)}")

    def close(self):
        """Cleanup resources"""
        if self.llm:
            # Let garbage collection handle it or any explicit close if needed
            self.llm = None
