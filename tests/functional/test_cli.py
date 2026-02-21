import pytest
from pathlib import Path
from pdf_renamer.main import main
from unittest.mock import patch
import sys

@patch('pdf_renamer.main.PDFRenamer')
def test_cli_help(mock_renamer, monkeypatch, capsys):
    monkeypatch.setattr(sys, 'argv', ['pdf-renamer', '--help'])
    
    with pytest.raises(SystemExit) as e:
        main()
    
    assert e.value.code == 0
    
    captured = capsys.readouterr()
    assert "Automatically rename PDFs using vision model" in captured.out

@patch('pdf_renamer.main.PDFRenamer')
def test_cli_dry_run(mock_renamer_class, tmp_path, monkeypatch):
    mock_renamer = mock_renamer_class.return_value
    mock_renamer.check_server.return_value = True
    mock_renamer.stats.failed = 0
    mock_renamer.process_pdf.return_value = (True, "renamed.pdf")
    
    test_pdf = tmp_path / "test.pdf"
    test_pdf.write_bytes(b"dummy")
    
    monkeypatch.setattr(sys, 'argv', ['pdf-renamer', str(test_pdf)])
    
    with pytest.raises(SystemExit) as e:
        main()
    
    assert e.value.code == 0
    mock_renamer.process_pdf.assert_called_once()
    args, kwargs = mock_renamer.process_pdf.call_args
    assert kwargs['dry_run'] is True

@patch('pdf_renamer.main.PDFRenamer')
def test_cli_execution_with_output_dir(mock_renamer_class, tmp_path, monkeypatch):
    mock_renamer = mock_renamer_class.return_value
    mock_renamer.check_server.return_value = True
    mock_renamer.stats.failed = 0
    
    # We are mocking batch_process because the input is a directory
    mock_renamer.batch_process.return_value = {"success": [], "failed": []}
    
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    
    monkeypatch.setattr(sys, 'argv', ['pdf-renamer', str(input_dir), '-o', str(output_dir), '-e'])
    
    with pytest.raises(SystemExit) as e:
        main()
    
    assert e.value.code == 0
    mock_renamer.batch_process.assert_called_once()
    args, kwargs = mock_renamer.batch_process.call_args
    assert kwargs['dry_run'] is False
    assert kwargs['output_dir'] == output_dir
