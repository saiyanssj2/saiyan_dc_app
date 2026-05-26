# Yêu cầu & Quyết định kỹ thuật

## Mục tiêu

- Deploy free trên hosting miễn phí (Render / Fly.io)
- Nhẹ, ít dependency, dễ maintain
- UI xịn sò (embed + buttons)
- Có thể kiếm tiền sau này (premium features)

## Quyết định: Bỏ Lavalink, dùng yt-dlp + FFmpeg

**Lý do:**
- Lavalink cần Java + ~512MB RAM → không chạy được trên free tier
- Cần quản lý 2 process → phức tạp khi deploy
- YouTube plugin của Lavalink hay bị block, phải update liên tục
- yt-dlp chỉ cần 1 process Python + FFmpeg, nhẹ, deploy 1 Dockerfile là xong

**Trade-off chấp nhận:**
- Không scale tốt bằng Lavalink (giới hạn ~5-10 voice channels đồng thời)
- Không hỗ trợ Spotify trực tiếp (chỉ YouTube)
- CPU usage cao hơn do FFmpeg chạy cùng process

## Roadmap kiếm tiền (Premium features)

### Free tier
- `/play`, `/skip`, `/queue`, `/stop`
- UI buttons (pause, skip, shuffle, loop)
- Queue tối đa 20 bài

### Premium tier (Patreon/Ko-fi)
- Queue không giới hạn
- 24/7 mode (bot không tự disconnect)
- Audio filters (bass boost, nightcore, slowed)
- Spotify/SoundCloud support (parse URL → search YouTube)
- Priority queue (bài premium user luôn phát trước)

## Khi nào quay lại Lavalink

- Khi bot phục vụ >50 guilds đồng thời
- Khi có revenue đủ trả VPS ($3-5/tháng)
- Dùng Oracle Cloud Free Tier (4 ARM cores, 24GB RAM) để host Lavalink miễn phí
