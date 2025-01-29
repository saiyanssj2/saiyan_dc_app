# Coroutine được khai báo bằng cú pháp async/await là cách được ưa chuộng để viết các ứng dụng asyncio.
import asyncio

async def main():
    print('Hello ...')
    await asyncio.sleep(1)
    print('... World!')

asyncio.run(main())