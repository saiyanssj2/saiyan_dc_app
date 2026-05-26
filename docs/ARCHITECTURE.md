# Kiến trúc

## Stack

- **discord.py** - Discord API wrapper
- **yt-dlp** - Tải/stream audio từ YouTube
- **FFmpeg** - Encode/decode audio stream
- **PyNaCl** - Mã hóa voice connection

## Cấu trúc thư mục

```
saiyan_dc_app/
├── cogs/
│   └── music_cog.py    # Toàn bộ logic nhạc + UI buttons
├── docs/
│   ├── SETUP.md        # Hướng dẫn setup & deploy
│   ├── ARCHITECTURE.md # File này
│   └── REQUIREMENTS.md # Yêu cầu & quyết định kỹ thuật
├── main.py             # Entry point, khởi tạo bot
├── requirements.txt    # Python dependencies
├── Dockerfile          # Deploy container
├── .env.example        # Template env vars
├── .gitignore
└── readme.md
```

## Flow phát nhạc

```
User /play → yt-dlp search → lấy stream URL → FFmpegPCMAudio → Discord Voice
```

1. User gọi `/play <query>`
2. `yt-dlp` tìm kiếm trên YouTube, trả về stream URL
3. Tạo `FFmpegPCMAudio` source từ stream URL
4. discord.py phát audio vào voice channel
5. Khi bài kết thúc → callback `play_next()` tự phát bài tiếp

## Quản lý state

- Mỗi guild có 1 `MusicPlayer` instance (lưu trong `dict[guild_id, MusicPlayer]`)
- `MusicPlayer` giữ: queue, history, current track, loop mode, shuffle state
- `MusicControlView` là persistent UI buttons, reference tới cog để truy cập player

## So sánh với Lavalink (phiên bản cũ)

| | Lavalink | yt-dlp + FFmpeg |
|--|----------|-----------------|
| Process | 2 (Java + Python) | 1 (Python) |
| RAM | ~512MB+ | ~128-256MB |
| Dependencies | Java 17+, Lavalink.jar | FFmpeg |
| Deploy | Phức tạp | 1 Dockerfile |
| Scale | Tốt (>10 guilds) | OK (~5-10 guilds đồng thời) |
| Spotify | Plugin riêng | Không (chỉ YouTube) |
