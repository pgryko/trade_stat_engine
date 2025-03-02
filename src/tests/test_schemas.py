import pytest
from pydantic import ValidationError

from src.schemas import BatchRequest, StatsResponse


class TestModels:
    def test_batch_request_valid(self):
        request = BatchRequest(symbol="AAPL", values=[1.0, 2.0, 3.0])
        assert request.symbol == "AAPL"
        assert request.values == [1.0, 2.0, 3.0]

    def test_batch_request_empty_symbol(self):
        with pytest.raises(ValueError) as excinfo:
            BatchRequest(symbol="", values=[1.0, 2.0, 3.0])
        assert "Symbol must be non-empty" in str(excinfo.value)

    def test_batch_request_long_symbol(self):
        with pytest.raises(ValueError) as excinfo:
            BatchRequest(symbol="A" * 21, values=[1.0, 2.0, 3.0])
        assert "Symbol must be non-empty and not exceed 20 characters" in str(
            excinfo.value
        )

    def test_batch_request_empty_values(self):
        with pytest.raises(ValidationError) as excinfo:
            BatchRequest(symbol="AAPL", values=[])
        assert "min_items" in str(excinfo.value).lower()

    def test_batch_request_too_many_values(self):
        with pytest.raises(ValidationError) as excinfo:
            BatchRequest(symbol="AAPL", values=[1.0] * 10001)
        assert "max_items" in str(excinfo.value).lower()

    def test_stats_response(self):
        response = StatsResponse(min=1.0, max=5.0, last=5.0, avg=3.0, var=2.0)
        assert response.min == 1.0
        assert response.max == 5.0
        assert response.last == 5.0
        assert response.avg == 3.0
        assert response.var == 2.0
