import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from pdf_renamer.pdf_utils import LLMAnalyzer


def _fake_chat_handler_module(name_to_cls):
    """Build a fake llama_cpp.llama_chat_format module exposing given handlers."""
    mod = types.ModuleType("llama_cpp.llama_chat_format")
    for n, cls in name_to_cls.items():
        setattr(mod, n, cls)
    return mod


def test_build_chat_handler_prefers_mtmd():
    class MTMD:
        def __init__(self, clip_model_path=None):
            self.kind = "mtmd"

    class Qwen:
        def __init__(self, clip_model_path=None):
            self.kind = "qwen"

    class Llava:
        def __init__(self, clip_model_path=None):
            self.kind = "llava"

    fake_mod = _fake_chat_handler_module(
        {
            "MTMDChatHandler": MTMD,
            "Qwen25VLChatHandler": Qwen,
            "Llava16ChatHandler": Llava,
        }
    )
    with patch.dict(sys.modules, {"llama_cpp.llama_chat_format": fake_mod}):
        handler = LLMAnalyzer._build_chat_handler("/tmp/mmproj.gguf")
    assert handler.kind == "mtmd"


def test_build_chat_handler_falls_back_to_qwen_when_mtmd_missing():
    class Qwen:
        def __init__(self, clip_model_path=None):
            self.kind = "qwen"

    class Llava:
        def __init__(self, clip_model_path=None):
            self.kind = "llava"

    fake_mod = _fake_chat_handler_module(
        {"Qwen25VLChatHandler": Qwen, "Llava16ChatHandler": Llava}
    )
    with patch.dict(sys.modules, {"llama_cpp.llama_chat_format": fake_mod}):
        handler = LLMAnalyzer._build_chat_handler("/tmp/mmproj.gguf")
    assert handler.kind == "qwen"


def test_build_chat_handler_falls_back_when_mtmd_raises():
    class MTMD:
        def __init__(self, clip_model_path=None):
            raise ValueError("arch qwen35 not supported by MTMD")

    class Qwen:
        def __init__(self, clip_model_path=None):
            self.kind = "qwen"

    fake_mod = _fake_chat_handler_module(
        {"MTMDChatHandler": MTMD, "Qwen25VLChatHandler": Qwen}
    )
    with patch.dict(sys.modules, {"llama_cpp.llama_chat_format": fake_mod}):
        handler = LLMAnalyzer._build_chat_handler("/tmp/mmproj.gguf")
    assert handler.kind == "qwen"


def test_build_chat_handler_all_fail_raises():
    class MTMD:
        def __init__(self, clip_model_path=None):
            raise ValueError("nope")

    class Qwen:
        def __init__(self, clip_model_path=None):
            raise ValueError("nope")

    class Llava:
        def __init__(self, clip_model_path=None):
            raise ValueError("nope")

    fake_mod = _fake_chat_handler_module(
        {
            "MTMDChatHandler": MTMD,
            "Qwen25VLChatHandler": Qwen,
            "Llava16ChatHandler": Llava,
        }
    )
    with patch.dict(sys.modules, {"llama_cpp.llama_chat_format": fake_mod}):
        with pytest.raises(Exception, match="No compatible chat handler"):
            LLMAnalyzer._build_chat_handler("/tmp/mmproj.gguf")


def test_analyze_document_calls_chat_handler_with_enable_thinking_false():
    """We call the chat handler directly (not create_chat_completion) so we
    can pass enable_thinking=False through to the Jinja2 template render,
    which is the only reliable way to disable Qwen3.5 thinking via the
    Python binding."""
    analyzer = LLMAnalyzer.__new__(LLMAnalyzer)
    analyzer.llm = MagicMock()
    analyzer.verbose = False

    fake_handler = MagicMock()
    fake_handler.return_value = {
        "choices": [
            {"message": {"content": "Date: 2024-01-01\nDescription: Doc\nID: X1"}}
        ]
    }
    analyzer.llm.chat_handler = fake_handler

    analyzer.analyze_document("base64data", "file.pdf", receipt=False)

    fake_handler.assert_called_once()
    _, kwargs = fake_handler.call_args
    assert kwargs["enable_thinking"] is False
    assert "llama" in kwargs  # the handler is called with the llama instance


def test_analyze_document_falls_back_to_create_chat_completion_without_handler():
    """If no chat_handler is set, fall back to create_chat_completion."""
    analyzer = LLMAnalyzer.__new__(LLMAnalyzer)
    analyzer.llm = MagicMock()
    analyzer.llm.chat_handler = None
    analyzer.verbose = False

    analyzer.llm.create_chat_completion.return_value = {
        "choices": [
            {"message": {"content": "Date: 2024-01-01\nDescription: Doc\nID: X1"}}
        ]
    }

    result = analyzer.analyze_document("base64data", "file.pdf", receipt=False)
    assert "Date: 2024-01-01" in result
    analyzer.llm.create_chat_completion.assert_called_once()
