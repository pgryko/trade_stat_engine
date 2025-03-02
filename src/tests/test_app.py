import pytest
import math
from fastapi.testclient import TestClient

from src.app import app, symbols_data

# Create a test client
client = TestClient(app)


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
