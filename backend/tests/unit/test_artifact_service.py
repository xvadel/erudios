"""
Unit tests for ArtifactService helper functions.
Tests the _strip_fences helper and schema validation without LLM calls.
"""
from __future__ import annotations

import json
import pytest

from app.modules.artifacts.service import _strip_fences


class TestStripFences:
    def test_strips_json_fence(self):
        raw = '```json\n{"key": "value"}\n```'
        result = _strip_fences(raw)
        assert result == '{"key": "value"}'
        # Must be valid JSON after stripping
        assert json.loads(result) == {"key": "value"}

    def test_strips_generic_fence(self):
        raw = '```\n{"a": 1}\n```'
        result = _strip_fences(raw)
        assert result == '{"a": 1}'

    def test_no_fence_unchanged(self):
        raw = '{"a": 1}'
        assert _strip_fences(raw) == raw

    def test_strips_leading_trailing_whitespace(self):
        raw = '  \n{"a": 1}\n  '
        result = _strip_fences(raw)
        assert result == '{"a": 1}'

    def test_strips_nested_content_correctly(self):
        raw = '```json\n[\n  {"question": "What is X?", "correct_index": 0}\n]\n```'
        result = _strip_fences(raw)
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert parsed[0]["question"] == "What is X?"

    def test_empty_string(self):
        assert _strip_fences("") == ""

    def test_fence_without_closing(self):
        """If there's an opening fence but no closing, stripping should still remove the first line."""
        raw = '```json\n{"a": 1}'
        result = _strip_fences(raw)
        assert result == '{"a": 1}'
