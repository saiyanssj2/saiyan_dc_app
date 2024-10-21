import asyncio
import random

async def fetch_data(api_name):
    print(f"Đang gọi API: {api_name}")
    # Giả lập thời gian gọi API
    await asyncio.sleep(random.uniform(1, 3))  # Chờ một khoảng thời gian ngẫu nhiên từ 1 đến 3 giây
    print(f"Đã nhận dữ liệu từ {api_name}")

async def main():
    # Gọi nhiều API đồng thời
    await asyncio.gather(
        fetch_data("API 1"),
        fetch_data("API 2"),
        fetch_data("API 3"),
    )

# Chạy chương trình
asyncio.run(main())
