from threading import Lock

from starlette.concurrency import run_in_threadpool


class SymbolsStorage:
    def __init__(self):
        self.data = {}
        self.lock = Lock()

    async def get(self, symbol):
        # Acquire lock for consistent reads
        await run_in_threadpool(self.lock.acquire)
        try:
            return self.data.get(symbol)
        finally:
            self.lock.release()

    async def set(self, symbol, value):
        # Acquire lock
        await run_in_threadpool(self.lock.acquire)
        try:
            self.data[symbol] = value
        finally:
            self.lock.release()

    async def contains(self, symbol):
        # Acquire lock for consistent reads
        await run_in_threadpool(self.lock.acquire)
        try:
            return symbol in self.data
        finally:
            self.lock.release()

    async def count(self):
        # Acquire lock for consistent reads
        await run_in_threadpool(self.lock.acquire)
        try:
            return len(self.data)
        finally:
            self.lock.release()

    async def clear(self):
        # Acquire lock
        await run_in_threadpool(self.lock.acquire)
        try:
            self.data.clear()
        finally:
            self.lock.release()
