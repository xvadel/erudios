from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.providers.llms.budget import BudgetTracker, Provider, DAILY_LIMITS


class TestBudgetTracker:

    @pytest.mark.asyncio
    async def test_can_use_returns_true_when_budget_available(self):
        tracker = BudgetTracker()
        with patch.object(tracker, "get_remaining", return_value=500_000):
            result = await tracker.can_use(Provider.GEMINI_FLASH, 1000)
            assert result is True

    @pytest.mark.asyncio
    async def test_can_use_returns_false_when_budget_exhausted(self):
        tracker = BudgetTracker()
        with patch.object(tracker, "get_remaining", return_value=0):
            result = await tracker.can_use(Provider.GEMINI_FLASH, 1000)
            assert result is False

    @pytest.mark.asyncio
    async def test_can_use_returns_false_when_insufficient_budget(self):
        tracker = BudgetTracker()
        with patch.object(tracker, "get_remaining", return_value=100):
            result = await tracker.can_use(Provider.GEMINI_FLASH, estimated_tokens=500)
            assert result is False

    @pytest.mark.asyncio
    async def test_get_remaining_returns_full_limit_when_no_usage(self):
        tracker = BudgetTracker()
        with patch.object(tracker, "get_used", return_value=0):
            remaining = await tracker.get_remaining(Provider.GROQ_LLAMA)
            assert remaining == DAILY_LIMITS[Provider.GROQ_LLAMA]

    @pytest.mark.asyncio
    async def test_get_remaining_correctly_subtracts_usage(self):
        tracker = BudgetTracker()
        with patch.object(tracker, "get_used", return_value=100_000):
            remaining = await tracker.get_remaining(Provider.GEMINI_FLASH)
            expected = DAILY_LIMITS[Provider.GEMINI_FLASH] - 100_000
            assert remaining == expected

    @pytest.mark.asyncio
    async def test_get_remaining_never_goes_negative(self):
        tracker = BudgetTracker()
        # Simulate over-use
        with patch.object(tracker, "get_used", return_value=999_999_999):
            remaining = await tracker.get_remaining(Provider.GEMINI_FLASH)
            assert remaining == 0

    def test_daily_limits_are_positive(self):
        for provider, limit in DAILY_LIMITS.items():
            assert limit > 0, f"Limit for {provider} should be positive"

    def test_groq_llama_has_1m_daily_limit(self):
        """Confirm corrected Groq Llama limit (1M TPD)."""
        assert DAILY_LIMITS[Provider.GROQ_LLAMA] >= 900_000
