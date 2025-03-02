import pytest

from src.app import symbols_data


# Clear global symbols_data before each test
@pytest.fixture(autouse=True)
def clear_symbols_data():
    symbols_data.clear()
    yield
