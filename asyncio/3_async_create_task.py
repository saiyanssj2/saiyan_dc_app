import asyncio

async def nested():
    return 42

async def main():
    task = asyncio.create_task(nested())

    print(await task)

asyncio.run(main())
