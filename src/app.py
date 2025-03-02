from fastapi import FastAPI, HTTPException

from src.segment_tree import SymbolData
from src.schemas import BatchRequest

app = FastAPI(title="High-Frequency Trading Statistics API")


# In-memory storage - limited to 10 symbols as per requirements
symbols_data = {}


@app.post("/add_batch/")
async def add_batch(request: BatchRequest):
    symbol = request.symbol
    values = request.values

    # Check number of symbols
    if symbol not in symbols_data and len(symbols_data) >= 10:
        raise HTTPException(
            status_code=400, detail="Maximum number of symbols (10) reached"
        )

    if symbol not in symbols_data:
        symbols_data[symbol] = SymbolData()

    symbols_data[symbol].add_batch(values)

    return {
        "status": "success",
        "message": f"Added {len(values)} data points for {symbol}",
    }


@app.get("/stats/")
async def get_stats(symbol: str, k: int):
    if k < 1 or k > 8:
        raise HTTPException(status_code=400, detail="k must be between 1 and 8")

    if symbol not in symbols_data:
        raise HTTPException(status_code=404, detail="Symbol not found")

    return symbols_data[symbol].get_stats(k)
