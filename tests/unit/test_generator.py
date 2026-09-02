"""
test_generator.py — Unit Tests for Qwen2.5-7B Generator Abstraction
"""

import json
from typing import Iterator
import httpx
import pytest
from unittest.mock import MagicMock, patch

from anchor.config import settings
from anchor.models.generator import QwenGenerator


def test_generator_initialization_defaults():
    gen = QwenGenerator()
    assert gen.base_url == settings.OLLAMA_BASE_URL.rstrip("/")
    assert gen.model_name == settings.OLLAMA_MODEL
    assert gen.timeout == 30.0


def test_generator_initialization_custom():
    gen = QwenGenerator(
        base_url="http://127.0.0.1:11434/",
        model_name="qwen2.5:7b-custom",
        timeout=15.0,
    )
    assert gen.base_url == "http://127.0.0.1:11434"
    assert gen.model_name == "qwen2.5:7b-custom"
    assert gen.timeout == 15.0


def test_generator_is_available_success():
    gen = QwenGenerator()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "models": [{"name": "qwen2.5:7b-instruct-q4_K_M"}]
    }

    with patch.object(httpx.Client, "get", return_value=mock_response):
        assert gen.is_available() is True


def test_generator_is_available_failure():
    gen = QwenGenerator()
    with patch.object(httpx.Client, "get", side_effect=httpx.ConnectError("Connection refused")):
        assert gen.is_available() is False


def test_generator_generate_sync():
    gen = QwenGenerator()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": "Under DFPDS-2026 Schedule 07, Fleet Commander tier limit is ₹15.0 Cr.",
        "done": True,
    }

    with patch.object(httpx.Client, "post", return_value=mock_response) as mock_post:
        result = gen.generate(
            prompt="What is the Schedule 7 limit?",
            system_prompt="You are a military assistant.",
            temperature=0.1,
            max_tokens=256,
        )

        assert "Schedule 07" in result
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        json_body = call_kwargs.get("json", {})
        assert json_body["model"] == gen.model_name
        assert json_body["prompt"] == "What is the Schedule 7 limit?"
        assert json_body["system"] == "You are a military assistant."
        assert json_body["stream"] is False
        assert json_body["options"]["temperature"] == 0.1
        assert json_body["options"]["num_predict"] == 256


def test_generator_generate_stream():
    gen = QwenGenerator()
    tokens = ["Under ", "DFPDS-2026 ", "Schedule 07, ", "limit is ", "₹15.0 Cr."]
    lines = [
        json.dumps({"response": tok, "done": (i == len(tokens) - 1)})
        for i, tok in enumerate(tokens)
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.iter_lines.return_value = lines

    with patch.object(httpx.Client, "stream") as mock_stream_ctx:
        mock_stream_ctx.return_value.__enter__.return_value = mock_response

        stream_gen = gen.generate_stream(
            prompt="What is Schedule 7?",
            system_prompt="Strict grounding.",
        )
        assert isinstance(stream_gen, Iterator)
        collected = list(stream_gen)
        assert "".join(collected) == "Under DFPDS-2026 Schedule 07, limit is ₹15.0 Cr."


def test_generator_connection_error_raises_runtime_error():
    gen = QwenGenerator()
    with patch.object(httpx.Client, "post", side_effect=httpx.ConnectError("Failed to connect")):
        with pytest.raises(RuntimeError, match="Failed to communicate with Ollama service"):
            gen.generate("Test prompt")
