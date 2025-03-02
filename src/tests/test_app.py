import pytest
import math
from httpx import AsyncClient, ASGITransport
import pytest_asyncio
from src.app import app, symbols_data

# Create a test client
# client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_symbols_data():
    symbols_data.clear()
    yield


@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.mark.asyncio
class TestAPI:
    async def test_add_batch_success(self, async_client):
        response = await async_client.post(
            "/add_batch/", json={"symbol": "AAPL", "values": [1.0, 2.0, 3.0]}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Added 3 data points" in data["message"]
        assert await symbols_data.contains("AAPL")

    async def test_add_batch_invalid_symbol(self, async_client):
        response = await async_client.post(
            "/add_batch/", json={"symbol": "", "values": [1.0, 2.0, 3.0]}
        )
        assert response.status_code == 422  # Validation error

    async def test_add_batch_too_many_symbols(self, async_client):
        # Add 10 different symbols first
        for i in range(10):
            await async_client.post(
                "/add_batch/", json={"symbol": f"SYM{i}", "values": [1.0]}
            )

        # Try to add the 11th symbol
        response = await async_client.post(
            "/add_batch/", json={"symbol": "EXTRA", "values": [1.0]}
        )
        assert response.status_code == 400
        assert "Maximum number of symbols" in response.json()["detail"]

    async def test_get_stats_success(self, async_client):
        # Add data first
        await async_client.post(
            "/add_batch/", json={"symbol": "AAPL", "values": [1.0, 2.0, 3.0, 4.0, 5.0]}
        )

        # Get stats
        response = await async_client.get("/stats/?symbol=AAPL&k=1")
        assert response.status_code == 200
        data = response.json()
        assert data["min"] == 1.0
        assert data["max"] == 5.0
        assert data["last"] == 5.0
        assert data["avg"] == 3.0
        assert math.isclose(data["var"], 2.0, rel_tol=1e-9)

    async def test_get_stats_invalid_k(self, async_client):
        await async_client.post(
            "/add_batch/", json={"symbol": "AAPL", "values": [1.0, 2.0, 3.0]}
        )

        # Test k below range
        response = await async_client.get("/stats/?symbol=AAPL&k=0")
        assert response.status_code == 400
        assert "k must be between 1 and 8" in response.json()["detail"]

        # Test k above range
        response = await async_client.get("/stats/?symbol=AAPL&k=9")
        assert response.status_code == 400
        assert "k must be between 1 and 8" in response.json()["detail"]

    async def test_get_stats_symbol_not_found(self, async_client):
        response = await async_client.get("/stats/?symbol=UNKNOWN&k=1")
        assert response.status_code == 404
        assert "Symbol not found" in response.json()["detail"]

    async def test_end_to_end_workflow(self, async_client):
        # Add initial batch
        await async_client.post(
            "/add_batch/",
            json={"symbol": "AAPL", "values": [float(i) for i in range(1, 11)]},
        )

        # Check stats
        response1 = await async_client.get("/stats/?symbol=AAPL&k=1")
        data1 = response1.json()
        assert data1["min"] == 1.0
        assert data1["max"] == 10.0
        assert data1["last"] == 10.0

        # Add more data
        await async_client.post(
            "/add_batch/",
            json={"symbol": "AAPL", "values": [float(i) for i in range(11, 21)]},
        )

        # Check updated stats (k=1 should see only last 10 points)
        response2 = await async_client.get("/stats/?symbol=AAPL&k=1")
        data2 = response2.json()
        assert data2["min"] == 11.0
        assert data2["max"] == 20.0
        assert data2["last"] == 20.0

        # Check with k=2 (should see all 20 points)
        response3 = await async_client.get("/stats/?symbol=AAPL&k=2")
        data3 = response3.json()
        assert data3["min"] == 1.0
        assert data3["max"] == 20.0
        assert data3["last"] == 20.0

    async def test_multiple_symbols(self, async_client):
        # Add data for AAPL
        await async_client.post(
            "/add_batch/", json={"symbol": "AAPL", "values": [1.0, 2.0, 3.0]}
        )

        # Add data for GOOG
        await async_client.post(
            "/add_batch/", json={"symbol": "GOOG", "values": [10.0, 20.0, 30.0]}
        )

        # Check AAPL stats
        response1 = await async_client.get("/stats/?symbol=AAPL&k=1")
        data1 = response1.json()
        assert data1["min"] == 1.0
        assert data1["max"] == 3.0

        # Check GOOG stats
        response2 = await async_client.get("/stats/?symbol=GOOG&k=1")
        data2 = response2.json()
        assert data2["min"] == 10.0
        assert data2["max"] == 30.0


# Performance test for large datasets
@pytest.mark.slow
@pytest.mark.asyncio
class TestPerformance:
    async def test_large_dataset(self, async_client):
        import time

        # Add a large batch of data
        symbol = "PERF"
        large_data = [float(i) for i in range(10000)]  # 10K data points

        await async_client.post(
            "/add_batch/", json={"symbol": symbol, "values": large_data}
        )

        # Test with k=3 (1000 points)
        start = time.time()
        await async_client.get(f"/stats/?symbol={symbol}&k=3")
        duration1 = time.time() - start

        # Test with k=4 (10000 points)
        start = time.time()
        await async_client.get(f"/stats/?symbol={symbol}&k=4")
        duration2 = time.time() - start

        # For better than O(n) algorithm, the ratio of times should be
        # significantly less than the ratio of input sizes (10:1)
        # For O(log n): log(10000)/log(1000) ≈ 4/3
        assert (
            duration2 < duration1 * 5
        ), f"k=4 took {duration2}s, k=3 took {duration1}s"
