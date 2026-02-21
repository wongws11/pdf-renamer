import pytest
from pathlib import Path
from pdf_renamer.pdf_utils import PDFCache

def test_cache_set_and_get(tmp_path):
    cache_db = tmp_path / "test_cache.db"
    cache = PDFCache(cache_db)
    
    # Test setting
    cache.set(
        checksum="abcd1234efgh",
        filename="test.pdf",
        date="2023-01-01",
        description="Test Doc",
        doc_id="ID1",
        file_size=1024
    )
    
    # Test getting
    result = cache.get("abcd1234efgh")
    assert result is not None
    date, desc, doc_id = result
    assert date == "2023-01-01"
    assert desc == "Test Doc"
    assert doc_id == "ID1"
    
    # Test getting non-existent
    assert cache.get("nonexistent") is None
    
    cache.close()

def test_cache_tracking_renamed(tmp_path):
    cache_db = tmp_path / "test_cache2.db"
    cache = PDFCache(cache_db)
    
    cache.track_renamed_file(
        original_path="/path/to/old.pdf",
        new_path="/path/to/new.pdf",
        checksum="12345"
    )
    
    assert cache.get_renamed_file("/path/to/old.pdf") == "/path/to/new.pdf"
    cache.close()
