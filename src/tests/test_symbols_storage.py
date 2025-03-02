from src.segment_tree import SymbolData
from src.symbols_storage import SymbolsStorage


async def test_clear_symbols():
    symbols_data = SymbolsStorage()
    # Add some data
    await symbols_data.set("AAPL", SymbolData())
    await symbols_data.set("GOOGL", SymbolData())

    # Verify data is present
    assert await symbols_data.count() == 2

    # Clear the data
    await symbols_data.clear()

    # Verify data is cleared
    assert await symbols_data.count() == 0
    assert not await symbols_data.contains("AAPL")
    assert not await symbols_data.contains("GOOGL")
