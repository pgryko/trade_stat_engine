from fastapi import FastAPI, HTTPException

from src.segment_tree import SymbolData
from src.schemas import BatchRequest

from src.symbols_storage import SymbolsStorage


def create_app():
    app = FastAPI(title="High-Frequency Trading Statistics API")

    # In-memory storage - limited to 10 symbols as per requirements
    app.state.symbols_data = SymbolsStorage()

    @app.post("/add_batch/")
    async def add_batch(request: BatchRequest):
        symbol = request.symbol
        values = request.values
        # Check number of symbols
        if (
            not await app.state.symbols_data.contains(symbol)
            and await app.state.symbols_data.count() >= 10
        ):
            raise HTTPException(
                status_code=400, detail="Maximum number of symbols (10) reached"
            )
        symbol_data = await app.state.symbols_data.get(symbol)
        if not symbol_data:
            symbol_data = SymbolData()
            await app.state.symbols_data.set(symbol, symbol_data)
        symbol_data.add_batch(values)
        return {
            "status": "success",
            "message": f"Added {len(values)} data points for {symbol}",
        }

    @app.get("/stats/")
    async def get_stats(symbol: str, k: int):
        """
        Get statistics for a symbol

        Parameters:
        - symbol: The trading symbol to get statistics for
        - k: The window size for calculating statistics (1-8)
        """
        if k < 1 or k > 8:
            raise HTTPException(status_code=400, detail="k must be between 1 and 8")
        symbol_data = await app.state.symbols_data.get(symbol)
        if not symbol_data:
            raise HTTPException(status_code=404, detail="Symbol not found")
        return symbol_data.get_stats(k)

    return app
