from pathlib import Path
from pdf_renamer.renamer import PDFRenamer
from unittest.mock import patch

@patch('pdf_renamer.renamer.LLMAnalyzer')
@patch('pdf_renamer.renamer.PDFConverter')
def test_process_pdf_integration(mock_converter_class, mock_llm_class, tmp_path):
    # Mock LLMAnalyzer
    mock_llm = mock_llm_class.return_value
    mock_llm.analyze_document.return_value = "Date: 2024-05-01\nDescription: Utility Bill\nID: UB999"
    
    # Mock PDFConverter
    mock_converter = mock_converter_class.return_value
    mock_converter.pdf_to_image.return_value = "mock_image_obj"
    mock_converter.image_to_base64.return_value = "mock_base64_string"

    # Setup directories and test file
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()
    
    test_pdf = input_dir / "scanned_001.pdf"
    test_pdf.write_bytes(b"%PDF-1.4 mock content")

    cache_db = tmp_path / "test_cache.db"

    renamer = PDFRenamer(
        verbose=False,
        use_cache=True,
        cache_path=cache_db,
        max_workers=1,
        receipt=False
    )
    
    # Run the test
    success, result_path = renamer.process_pdf(
        test_pdf,
        output_dir=output_dir,
        dry_run=False
    )
    
    assert success is True
    assert "2024-05-01_Utility_Bill_UB999.pdf" in result_path
    
    # Check that output file exists
    assert Path(result_path).exists()
    
    # Verify the original file was moved/renamed
    assert not test_pdf.exists()

    renamer.__del__()
