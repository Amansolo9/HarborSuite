from decimal import Decimal

import pytest

from backend.services.credit_score import CreditScoreService


def test_credit_score_base_formula() -> None:
    score = CreditScoreService.calculate(rating=4, penalties=[Decimal("20")])
    assert score == 710


def test_credit_score_clamps_to_minimum() -> None:
    score = CreditScoreService.calculate(rating=1, penalties=[Decimal("1000")])
    assert score == 300


def test_credit_score_rejects_invalid_rating() -> None:
    with pytest.raises(ValueError):
        CreditScoreService.calculate(rating=0)
