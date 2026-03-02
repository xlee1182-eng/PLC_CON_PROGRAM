import asyncio

async def backoff_retry(retry_count):
    delay = min(2 ** retry_count, 30)
    await asyncio.sleep(delay)
    