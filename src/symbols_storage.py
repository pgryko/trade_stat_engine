from threading import Lock

from starlette.concurrency import run_in_threadpool


class SymbolsStorage:
    def __init__(self):
        self.data = {}
        self.lock = Lock()

    async def get(self, symbol):
        return self.data.get(symbol)

    async def set(self, symbol, value):
        # Acquire lock
        await run_in_threadpool(self.lock.acquire)
        try:
            self.data[symbol] = value
        finally:
            self.lock.release()

    async def contains(self, symbol):
        return symbol in self.data

    async def count(self):
        return len(self.data)

    async def clear(self):
        # Acquire lock
        await run_in_threadpool(self.lock.acquire)
        try:
            self.data.clear()
        finally:
            self.lock.release()
