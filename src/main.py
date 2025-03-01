from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from collections import deque
import math

app = FastAPI(title="High-Frequency Trading Statistics API")


# Data models
class BatchRequest(BaseModel):
    symbol: str
    values: List[float] = Field(..., min_items=1, max_items=10000)

    @field_validator("symbol")
    @classmethod
    def symbol_must_be_valid(cls, v: str) -> str:
        if not v or len(v) > 20:  # Arbitrary reasonable limit
            raise ValueError("Symbol must be non-empty and not exceed 20 characters")
        return v


class StatsResponse(BaseModel):
    min: float
    max: float
    last: float
    avg: float
    var: float


# Efficient data structure using segment tree for O(log n) statistical queries
class SegmentTree:
    def __init__(self, max_size=10**8):
        self.max_size = max_size
        self.buffer = deque(maxlen=max_size)
        self.tree_min = []
        self.tree_max = []
        self.tree_sum = []
        self.tree_sum_sq = []
        self.last_val = None
        self.is_dirty = True  # Flag to indicate if the tree needs to be rebuilt

    def _build_tree(self):
        n = len(self.buffer)
        if n == 0:
            self.tree_min = []
            self.tree_max = []
            self.tree_sum = []
            self.tree_sum_sq = []
            return

        # Compute the size of the segment tree
        x = math.ceil(math.log2(n))
        max_size = 2 * (2**x) - 1

        # Initialize the segment tree arrays
        self.tree_min = [float("inf")] * max_size
        self.tree_max = [float("-inf")] * max_size
        self.tree_sum = [0] * max_size
        self.tree_sum_sq = [0] * max_size

        # Build the segment tree
        buffer_list = list(self.buffer)
        self._build_tree_util(buffer_list, 0, n - 1, 0)
        self.is_dirty = False

    def _build_tree_util(self, buffer_list, ss, se, si):
        if ss == se:
            # Leaf node
            val = buffer_list[ss]
            self.tree_min[si] = val
            self.tree_max[si] = val
            self.tree_sum[si] = val
            self.tree_sum_sq[si] = val**2
            return

        # Non-leaf node
        mid = (ss + se) // 2
        self._build_tree_util(buffer_list, ss, mid, 2 * si + 1)
        self._build_tree_util(buffer_list, mid + 1, se, 2 * si + 2)

        # Combine the results of the children
        self.tree_min[si] = min(self.tree_min[2 * si + 1], self.tree_min[2 * si + 2])
        self.tree_max[si] = max(self.tree_max[2 * si + 1], self.tree_max[2 * si + 2])
        self.tree_sum[si] = self.tree_sum[2 * si + 1] + self.tree_sum[2 * si + 2]
        self.tree_sum_sq[si] = (
            self.tree_sum_sq[2 * si + 1] + self.tree_sum_sq[2 * si + 2]
        )

    def add_batch(self, values: List[float]):
        for value in values:
            self.buffer.append(value)
            self.last_val = value
        self.is_dirty = True  # Mark tree as dirty when new data is added

    def _query_min(self, ss, se, qs, qe, si):
        if qs <= ss and qe >= se:
            # Total overlap
            return self.tree_min[si]

        if se < qs or ss > qe:
            # No overlap
            return float("inf")

        # Partial overlap
        mid = (ss + se) // 2
        return min(
            self._query_min(ss, mid, qs, qe, 2 * si + 1),
            self._query_min(mid + 1, se, qs, qe, 2 * si + 2),
        )

    def _query_max(self, ss, se, qs, qe, si):
        if qs <= ss and qe >= se:
            # Total overlap
            return self.tree_max[si]

        if se < qs or ss > qe:
            # No overlap
            return float("-inf")

        # Partial overlap
        mid = (ss + se) // 2
        return max(
            self._query_max(ss, mid, qs, qe, 2 * si + 1),
            self._query_max(mid + 1, se, qs, qe, 2 * si + 2),
        )

    def _query_sum(self, ss, se, qs, qe, si):
        if qs <= ss and qe >= se:
            # Total overlap
            return self.tree_sum[si]

        if se < qs or ss > qe:
            # No overlap
            return 0

        # Partial overlap
        mid = (ss + se) // 2
        return self._query_sum(ss, mid, qs, qe, 2 * si + 1) + self._query_sum(
            ss + 1, se, qs, qe, 2 * si + 2
        )

    def _query_sum_sq(self, ss, se, qs, qe, si):
        if qs <= ss and qe >= se:
            # Total overlap
            return self.tree_sum_sq[si]

        if se < qs or ss > qe:
            # No overlap
            return 0

        # Partial overlap
        mid = (ss + se) // 2
        return self._query_sum_sq(ss, mid, qs, qe, 2 * si + 1) + self._query_sum_sq(
            mid + 1, se, qs, qe, 2 * si + 2
        )

    def get_stats(self, k: int) -> Optional[StatsResponse]:
        n = len(self.buffer)
        if n == 0:
            return None

        # If the tree is dirty, rebuild it
        if self.is_dirty:
            self._build_tree()

        points_needed = min(10**k, n)
        qs = n - points_needed
        qe = n - 1

        min_val = self._query_min(0, n - 1, qs, qe, 0)
        max_val = self._query_max(0, n - 1, qs, qe, 0)
        sum_val = self._query_sum(0, n - 1, qs, qe, 0)
        sum_sq_val = self._query_sum_sq(0, n - 1, qs, qe, 0)

        avg_val = sum_val / points_needed
        var_val = (sum_sq_val / points_needed) - (avg_val**2)

        return StatsResponse(
            min=min_val, max=max_val, last=self.last_val, avg=avg_val, var=var_val
        )


# Symbol data management
class SymbolData:
    def __init__(self):
        self.segment_tree = SegmentTree()
        self.stats_cache = {}  # Cache for different k values

    def add_batch(self, values: List[float]):
        self.segment_tree.add_batch(values)
        # Clear the cache as it's no longer valid
        self.stats_cache = {}

    def get_stats(self, k: int) -> StatsResponse:
        if k in self.stats_cache:
            return self.stats_cache[k]

        stats = self.segment_tree.get_stats(k)
        if stats is None:
            raise HTTPException(
                status_code=404, detail="No data available for this symbol"
            )

        # Cache the results
        self.stats_cache[k] = stats

        return stats


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
