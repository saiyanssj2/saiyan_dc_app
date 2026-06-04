# Hướng dẫn Setup & Deploy

## Setup local

1. Cài FFmpeg: https://ffmpeg.org/download.html (thêm vào PATH) -> https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
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

## Deploy free (Render)

1. Push code lên GitHub
2. Tạo tài khoản Render: https://render.com
3. New → Web Service → connect repo
4. Environment: Docker
5. Thêm env var: `DISCORD_TOKEN`
6. Deploy

## Deploy free (Fly.io)

1. Cài flyctl: https://fly.io/docs/hands-on/install-flyctl/
2. ```
   fly launch
   fly secrets set DISCORD_TOKEN=<your_token>
   fly deploy
   ```

## Env vars

| Biến | Mô tả |
|------|--------|
| `DISCORD_TOKEN` | Token bot từ Discord Developer Portal |

## Yêu cầu Discord Bot

- Bật **Message Content Intent** trong Developer Portal → Bot → Privileged Gateway Intents
- Bot cần permission: Connect, Speak, Send Messages, Embed Links
