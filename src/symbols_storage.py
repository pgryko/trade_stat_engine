import asyncio


class SymbolsStorage:
    def __init__(self):
        self.data = {}
        self.lock = asyncio.Lock()

    async def get(self, symbol):
        # Acquire lock for consistent reads
        async with self.lock:
            return self.data.get(symbol)

    async def set(self, symbol, value):
        async with self.lock:
            self.data[symbol] = value

    async def contains(self, symbol):
        async with self.lock:
            return symbol in self.data

    async def count(self):
        async with self.lock:
            return len(self.data)

    async def clear(self):
        async with self.lock:
            self.data.clear()

    async def check_and_add_symbol(self, symbol, create_value_fn):
        """
        Atomically check if adding a symbol would exceed limits,
        and add it if allowed.

        Returns: (symbol_data, is_new)
        """
        async with self.lock:
            # Check if symbol exists
            symbol_data = self.data.get(symbol)
            if symbol_data:
                return symbol_data, False

            # Check symbol limit
            if len(self.data) >= 10:
                return None, False

            # Add new symbol
            symbol_data = create_value_fn()
            self.data[symbol] = symbol_data
            return symbol_data, True
