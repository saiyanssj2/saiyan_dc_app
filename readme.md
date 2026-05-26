# Saiyan DC Bot - Music Bot

Discord music bot dùng yt-dlp + FFmpeg (không cần Lavalink).

## Setup local

1. Cài FFmpeg: https://ffmpeg.org/download.html (thêm vào PATH)
2. Tạo file `.env`:
   ```
   DISCORD_TOKEN=<your_token>
   ```
3. Cài dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Chạy bot:
   ```
   python main.py
   ```

## Deploy (Render / Fly.io)

Dùng Dockerfile đã có sẵn. Set env var `DISCORD_TOKEN` trên platform.

## Commands

- `/play <search>` - Phát nhạc từ YouTube hoặc URL
- `/skip` - Bỏ qua bài hiện tại
- `/queue` - Xem hàng chờ
- `/stop` - Dừng nhạc và ngắt kết nối

## UI Buttons

Sau khi `/play`, bot hiện panel điều khiển với: ⏮️ ⏸️ ⏭️ 🔀 🔁 ⏹️
