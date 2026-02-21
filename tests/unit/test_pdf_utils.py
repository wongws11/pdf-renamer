import pytest
from pathlib import Path
from pdf_renamer.pdf_utils import FilenameGenerator, ResponseParser, FileUtils

def test_filename_generator_normal():
    generator = FilenameGenerator()
    filename = generator.generate_filename(
        date="2023-01-01",
        description="Invoice Store",
        doc_id="INV123",
        counter=0,
        file_ext=".pdf",
        receipt=False
    )
    assert filename == "2023-01-01_Invoice_Store_INV123.pdf"

def test_filename_generator_no_date():
    generator = FilenameGenerator()
    filename = generator.generate_filename(
        date=None,
        description="Unknown Doc",
        doc_id=None,
        counter=0,
        file_ext=".pdf",
        receipt=False
    )
    assert filename == "Unknown_Doc.pdf"

def test_filename_generator_receipt_mode():
    generator = FilenameGenerator()
    filename = generator.generate_filename(
        date="2024-05-12",
        description="Walmart Groceries",
        doc_id="8493",
        counter=2,
        file_ext=".jpg",
        receipt=True
    )
    assert filename == "2024-05-12_Walmart_Groceries_8493_v2.jpg"

def test_response_parser_valid():
    parser = ResponseParser()
    response = """
Date: 2024-10-15
Description: Auto Insurance
ID: POL-999
    """
    date, desc, doc_id = parser.parse_response(response, "original.pdf")
    assert date == "2024-10-15"
    assert desc == "Auto Insurance"
    assert doc_id == "POL-999"

def test_response_parser_missing_fields():
    parser = ResponseParser()
    response = "Random text that doesn't match"
    date, desc, doc_id = parser.parse_response(response, "my_file.pdf")
    assert date is None
    assert desc == "my_file"
    assert doc_id is None

def test_file_utils_checksum(tmp_path):
    # Create a temporary file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello World")
    
    utils = FileUtils()
    checksum = utils.calculate_checksum(test_file)
    assert isinstance(checksum, str)
    assert len(checksum) == 64  # SHA-256 is 64 hex characters
