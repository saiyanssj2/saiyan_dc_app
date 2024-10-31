import asyncio

async def a():
    i = 1
    while True:
        print(i)
        i+=1

async def b():
    for i in range(5, 10):
        await asyncio.sleep(1)
        print(i)

async def main():
    await a()

asyncio.create_task(main())
asyncio.run_coroutine_threadsafe(b, asyncio.get_event_loop())