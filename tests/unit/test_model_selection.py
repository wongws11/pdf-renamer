from unittest.mock import patch

from pdf_renamer.pdf_utils import (
    RAM_THRESHOLD_27B_BYTES,
    RAM_THRESHOLD_9B_BYTES,
    _select_model_size,
)


def test_select_model_size_forces_27b():
    assert _select_model_size("27b") == "27b"


def test_select_model_size_forces_9b():
    assert _select_model_size("9b") == "9b"


def test_select_model_size_forces_4b():
    assert _select_model_size("4b") == "4b"


def test_select_model_size_invalid_falls_back_to_auto():
    # Unknown value should be treated as "auto"
    with patch("pdf_renamer.pdf_utils._get_total_ram_bytes", return_value=0):
        assert _select_model_size("bogus") == "4b"


def test_select_model_size_auto_at_27b_threshold_picks_27b():
    with patch(
        "pdf_renamer.pdf_utils._get_total_ram_bytes",
        return_value=RAM_THRESHOLD_27B_BYTES,
    ):
        assert _select_model_size("auto") == "27b"


def test_select_model_size_auto_above_27b_threshold_picks_27b():
    with patch(
        "pdf_renamer.pdf_utils._get_total_ram_bytes",
        return_value=RAM_THRESHOLD_27B_BYTES + 1,
    ):
        assert _select_model_size("auto") == "27b"


def test_select_model_size_auto_just_below_27b_threshold_picks_9b():
    with patch(
        "pdf_renamer.pdf_utils._get_total_ram_bytes",
        return_value=RAM_THRESHOLD_27B_BYTES - 1,
    ):
        assert _select_model_size("auto") == "9b"


def test_select_model_size_auto_at_9b_threshold_picks_9b():
    with patch(
        "pdf_renamer.pdf_utils._get_total_ram_bytes",
        return_value=RAM_THRESHOLD_9B_BYTES,
    ):
        assert _select_model_size("auto") == "9b"


def test_select_model_size_auto_below_9b_threshold_picks_4b():
    with patch(
        "pdf_renamer.pdf_utils._get_total_ram_bytes",
        return_value=RAM_THRESHOLD_9B_BYTES - 1,
    ):
        assert _select_model_size("auto") == "4b"


def test_select_model_size_auto_unknown_ram_is_conservative():
    with patch("pdf_renamer.pdf_utils._get_total_ram_bytes", return_value=0):
        assert _select_model_size("auto") == "4b"
