# test_app.py
import pytest
import numpy as np
import math
from fastapi.testclient import TestClient
from pydantic import ValidationError
from collections import deque
from fastapi import HTTPException

from main import app, SegmentTree, SymbolData, BatchRequest, StatsResponse, symbols_data


# Create a test client
client = TestClient(app)


# Clear global symbols_data before each test
@pytest.fixture(autouse=True)
def clear_symbols_data():
    symbols_data.clear()
    yield


# ======= Unit Tests =======


class TestSegmentTree:
    def test_init(self):
        tree = SegmentTree()
        assert isinstance(tree.buffer, deque)
        assert tree.tree_min == []
        assert tree.tree_max == []
        assert tree.tree_sum == []
        assert tree.tree_sum_sq == []
        assert tree.last_val is None
        assert tree.is_dirty is True

    def test_add_batch_single_value(self):
        tree = SegmentTree()
        tree.add_batch([5.0])
        assert list(tree.buffer) == [5.0]
        assert tree.last_val == 5.0
        assert tree.is_dirty is True

    def test_add_batch_multiple_values(self):
        tree = SegmentTree()
        tree.add_batch([1.0, 2.0, 3.0])
        assert list(tree.buffer) == [1.0, 2.0, 3.0]
        assert tree.last_val == 3.0
        assert tree.is_dirty is True

    def test_add_batch_multiple_calls(self):
        tree = SegmentTree()
        tree.add_batch([1.0, 2.0])
        tree.add_batch([3.0, 4.0])
        assert list(tree.buffer) == [1.0, 2.0, 3.0, 4.0]
        assert tree.last_val == 4.0
        assert tree.is_dirty is True

    def test_build_tree_empty(self):
        tree = SegmentTree()
        tree._build_tree()
        assert tree.tree_min == []
        assert tree.tree_max == []
        assert tree.tree_sum == []
        assert tree.tree_sum_sq == []
        assert tree.is_dirty is False

    def test_build_tree_non_empty(self):
        tree = SegmentTree()
        tree.add_batch([1.0, 3.0, 2.0])
        tree._build_tree()
        assert len(tree.tree_min) > 0
        assert len(tree.tree_max) > 0
        assert len(tree.tree_sum) > 0
        assert len(tree.tree_sum_sq) > 0
        assert tree.is_dirty is False

    def test_get_stats_empty(self):
        tree = SegmentTree()
        stats = tree.get_stats(1)
        assert stats is None

    def test_get_stats_single_value(self):
        tree = SegmentTree()
        tree.add_batch([5.0])
        stats = tree.get_stats(1)
        assert stats.min == 5.0
        assert stats.max == 5.0
        assert stats.last == 5.0
        assert stats.avg == 5.0
        assert stats.var == 0.0

    def test_get_stats_multiple_values(self):
        tree = SegmentTree()
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        tree.add_batch(values)

        stats = tree.get_stats(1)
        assert stats.min == 1.0
        assert stats.max == 5.0
        assert stats.last == 5.0
        assert stats.avg == 3.0
        assert pytest.approx(stats.var) == 2.0

    def test_get_stats_subset_of_values(self):
        tree = SegmentTree()
        values = [float(i) for i in range(1, 21)]  # 20 values
        tree.add_batch(values)

        # Test with k=1 (should use last 10 values)
        stats = tree.get_stats(1)
        assert stats.min == 11.0
        assert stats.max == 20.0
        assert stats.last == 20.0
        assert stats.avg == 15.5

        # Check variance calculation
        subset = [float(i) for i in range(11, 21)]
        expected_variance = np.var(subset)
        assert pytest.approx(stats.var) == expected_variance

    def test_build_tree_after_add(self):
        tree = SegmentTree()
        tree.add_batch([1.0, 2.0, 3.0])
        assert tree.is_dirty is True

        # Getting stats triggers tree build
        tree.get_stats(1)
        assert tree.is_dirty is False

        # Adding more data marks tree as dirty again
        tree.add_batch([4.0, 5.0])
        assert tree.is_dirty is True


class TestSymbolData:
    def test_init(self):
        symbol_data = SymbolData()
        assert isinstance(symbol_data.segment_tree, SegmentTree)
        assert symbol_data.stats_cache == {}

    def test_add_batch(self):
        symbol_data = SymbolData()
        symbol_data.add_batch([1.0, 2.0, 3.0])
        assert list(symbol_data.segment_tree.buffer) == [1.0, 2.0, 3.0]
        assert symbol_data.stats_cache == {}  # Cache should be cleared

    def test_get_stats(self):
        symbol_data = SymbolData()
        symbol_data.add_batch([1.0, 2.0, 3.0, 4.0, 5.0])

        # First call should calculate and cache
        stats1 = symbol_data.get_stats(1)
        assert stats1.min == 1.0
        assert stats1.max == 5.0
        assert len(symbol_data.stats_cache) == 1
        assert 1 in symbol_data.stats_cache

        # Second call should use cache
        stats2 = symbol_data.get_stats(1)
        assert stats2 == stats1

        # Different k should calculate new stats
        stats3 = symbol_data.get_stats(2)
        assert 2 in symbol_data.stats_cache
        assert stats3 != stats1

        # Adding new data should clear cache
        symbol_data.add_batch([6.0])
        assert symbol_data.stats_cache == {}

    def test_get_stats_no_data(self):
        symbol_data = SymbolData()
        with pytest.raises(HTTPException) as excinfo:
            symbol_data.get_stats(1)
        assert excinfo.value.status_code == 404
        assert "No data available" in excinfo.value.detail


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


# ======= API Integration Tests =======


class TestAPI:
    def test_add_batch_success(self):
        response = client.post(
            "/add_batch/", json={"symbol": "AAPL", "values": [1.0, 2.0, 3.0]}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Added 3 data points" in data["message"]
        assert "AAPL" in symbols_data

    def test_add_batch_invalid_symbol(self):
        response = client.post(
            "/add_batch/", json={"symbol": "", "values": [1.0, 2.0, 3.0]}
        )
        assert response.status_code == 422  # Validation error

    def test_add_batch_invalid_values(self):
        response = client.post("/add_batch/", json={"symbol": "AAPL", "values": []})
        assert response.status_code == 422  # Validation error

    def test_add_batch_too_many_symbols(self):
        # Add 10 different symbols first
        for i in range(10):
            client.post("/add_batch/", json={"symbol": f"SYM{i}", "values": [1.0]})

        # Try to add the 11th symbol
        response = client.post("/add_batch/", json={"symbol": "EXTRA", "values": [1.0]})
        assert response.status_code == 400
        assert "Maximum number of symbols" in response.json()["detail"]

    def test_get_stats_success(self):
        # Add data first
        client.post(
            "/add_batch/", json={"symbol": "AAPL", "values": [1.0, 2.0, 3.0, 4.0, 5.0]}
        )

        # Get stats
        response = client.get("/stats/?symbol=AAPL&k=1")
        assert response.status_code == 200
        data = response.json()
        assert data["min"] == 1.0
        assert data["max"] == 5.0
        assert data["last"] == 5.0
        assert data["avg"] == 3.0
        assert math.isclose(data["var"], 2.0, rel_tol=1e-9)

    def test_get_stats_invalid_k(self):
        client.post("/add_batch/", json={"symbol": "AAPL", "values": [1.0, 2.0, 3.0]})

        # Test k below range
        response = client.get("/stats/?symbol=AAPL&k=0")
        assert response.status_code == 400
        assert "k must be between 1 and 8" in response.json()["detail"]

        # Test k above range
        response = client.get("/stats/?symbol=AAPL&k=9")
        assert response.status_code == 400
        assert "k must be between 1 and 8" in response.json()["detail"]

    def test_get_stats_symbol_not_found(self):
        response = client.get("/stats/?symbol=UNKNOWN&k=1")
        assert response.status_code == 404
        assert "Symbol not found" in response.json()["detail"]

    def test_end_to_end_workflow(self):
        # Add initial batch
        client.post(
            "/add_batch/",
            json={"symbol": "AAPL", "values": [float(i) for i in range(1, 11)]},
        )

        # Check stats
        response1 = client.get("/stats/?symbol=AAPL&k=1")
        data1 = response1.json()
        assert data1["min"] == 1.0
        assert data1["max"] == 10.0
        assert data1["last"] == 10.0

        # Add more data
        client.post(
            "/add_batch/",
            json={"symbol": "AAPL", "values": [float(i) for i in range(11, 21)]},
        )

        # Check updated stats (k=1 should see only last 10 points)
        response2 = client.get("/stats/?symbol=AAPL&k=1")
        data2 = response2.json()
        assert data2["min"] == 11.0
        assert data2["max"] == 20.0
        assert data2["last"] == 20.0

        # Check with k=2 (should see all 20 points)
        response3 = client.get("/stats/?symbol=AAPL&k=2")
        data3 = response3.json()
        assert data3["min"] == 1.0
        assert data3["max"] == 20.0
        assert data3["last"] == 20.0

    def test_multiple_symbols(self):
        # Add data for AAPL
        client.post("/add_batch/", json={"symbol": "AAPL", "values": [1.0, 2.0, 3.0]})

        # Add data for GOOG
        client.post(
            "/add_batch/", json={"symbol": "GOOG", "values": [10.0, 20.0, 30.0]}
        )

        # Check AAPL stats
        response1 = client.get("/stats/?symbol=AAPL&k=1")
        data1 = response1.json()
        assert data1["min"] == 1.0
        assert data1["max"] == 3.0

        # Check GOOG stats
        response2 = client.get("/stats/?symbol=GOOG&k=1")
        data2 = response2.json()
        assert data2["min"] == 10.0
        assert data2["max"] == 30.0


# Performance test for large datasets
@pytest.mark.slow
class TestPerformance:
    def test_large_dataset(self):
        import time

        # Add a large batch of data
        symbol = "PERF"
        large_data = [float(i) for i in range(10000)]  # 10K data points

        client.post("/add_batch/", json={"symbol": symbol, "values": large_data})

        # Test with k=3 (1000 points)
        start = time.time()
        client.get(f"/stats/?symbol={symbol}&k=3")
        duration1 = time.time() - start

        # Test with k=4 (10000 points)
        start = time.time()
        client.get(f"/stats/?symbol={symbol}&k=4")
        duration2 = time.time() - start

        # For better than O(n) algorithm, the ratio of times should be
        # significantly less than the ratio of input sizes (10:1)
        # For O(log n): log(10000)/log(1000) ≈ 4/3
        assert (
            duration2 < duration1 * 5
        ), f"k=4 took {duration2}s, k=3 took {duration1}s"


class TestEdgeCases:
    def test_buffer_max_size(self):
        """Test that buffer respects maximum size"""
        tree = SegmentTree(max_size=5)
        tree.add_batch([1.0, 2.0, 3.0, 4.0, 5.0])
        tree.add_batch([6.0, 7.0])
        # Should only keep the most recent 5 values
        assert list(tree.buffer) == [3.0, 4.0, 5.0, 6.0, 7.0]

    def test_precision_with_floating_point(self):
        """Test handling of floating point precision"""
        tree = SegmentTree()
        tree.add_batch([1.1, 2.2, 3.3, 4.4, 5.5])
        stats = tree.get_stats(1)
        assert stats.min == 1.1
        assert stats.max == 5.5
        assert stats.last == 5.5
        assert pytest.approx(stats.avg) == 3.3
        assert pytest.approx(stats.var) == 2.42
