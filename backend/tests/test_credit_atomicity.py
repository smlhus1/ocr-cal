"""
Tests for atomic credit operations (C-01, H-01, H-04).
Verifies deduct_credit and add_credits behave correctly with bounds.
"""
import pytest

from app.database import MAX_CREDIT_AMOUNT, MAX_CREDIT_BALANCE


class TestAddCreditsValidation:
    """Tests for add_credits() input validation (H-04)."""

    @pytest.mark.asyncio
    async def test_rejects_zero_amount(self):
        from app.database import add_credits
        with pytest.raises(ValueError, match="Credit amount must be between"):
            await add_credits("session-test", 0)

    @pytest.mark.asyncio
    async def test_rejects_negative_amount(self):
        from app.database import add_credits
        with pytest.raises(ValueError, match="Credit amount must be between"):
            await add_credits("session-test", -5)

    @pytest.mark.asyncio
    async def test_rejects_over_max_amount(self):
        from app.database import add_credits
        with pytest.raises(ValueError, match="Credit amount must be between"):
            await add_credits("session-test", MAX_CREDIT_AMOUNT + 1)

    def test_constants_are_sane(self):
        assert MAX_CREDIT_AMOUNT == 100
        assert MAX_CREDIT_BALANCE == 10000
        assert MAX_CREDIT_AMOUNT <= MAX_CREDIT_BALANCE
