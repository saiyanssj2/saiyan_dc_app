# Kiến trúc

## Stack

- **discord.py** - Discord API wrapper
- **yt-dlp** - Tải/stream audio từ YouTube
- **FFmpeg** - Encode/decode audio stream
- **PyNaCl** - Mã hóa voice connection
- **spotipy** - Spotify API (lấy metadata, stream từ YouTube)

## Cấu trúc thư mục

```
saiyan_dc_app/
├── cogs/
│   ├── music_core.py     # Track, MusicPlayer, favorites/playlist helpers
│   ├── music_player.py   # Play logic, seek, queue management, UI helpers
│   ├── music_ui.py       # Embed builder, SelectTrackView, PlaylistSelectView
│   ├── music_controls.py # MusicControlView (tất cả buttons)
│   ├── music_cog.py      # Slash commands + URL/search handlers
│   ├── local_cog.py      # /local - phát file/folder local
│   ├── search_cog.py     # /search - tìm keyword hoặc link bất kỳ
│   └── spotify_cog.py    # /spotify - tìm nhạc Spotify
├── data/
│   ├── favorites.json    # Bài yêu thích theo user
│   └── playlists.json    # Playlist đã lưu theo user
├── docs/
│   ├── SETUP.md          # Hướng dẫn setup & deploy
│   ├── ARCHITECTURE.md   # File này
│   └── REQUIREMENTS.md   # Yêu cầu & quyết định kỹ thuật
├── ffmpeg/               # FFmpeg binary (local)
├── main.py               # Entry point, khởi tạo bot
├── requirements.txt      # Python dependencies
├── Dockerfile            # Deploy container
├── .env.example          # Template env vars
├── .gitignore
└── readme.md
```

## Flow phát nhạc

```
User /play → yt-dlp search (extract_flat) → dropdown top 10 → user chọn
→ fetch stream URL → FFmpegPCMAudio → PCMVolumeTransformer → Discord Voice
```

1. User gọi `/play <query>`
2. `yt-dlp` search với `extract_flat` → trả về metadata nhanh (~1.8s)
3. Hiện dropdown top 10 để user chọn
4. Khi user chọn → fetch stream URL thực sự
5. Tạo `FFmpegPCMAudio` → wrap `PCMVolumeTransformer`
6. discord.py phát audio vào voice channel
7. Khi bài kết thúc → `after_play` callback → `_on_track_end` → phát bài tiếp

## Flow Spotify

```
User /spotify → Spotify API (metadata) → yt-dlp ytsearch1 → YouTube stream URL → Discord Voice
```

## Quản lý state

- Mỗi guild có 1 `MusicPlayer` instance (lưu trong `dict[guild_id, MusicPlayer]`)
- `MusicPlayer` giữ:
  - `history` - đã phát (LIFO)
  - `current` - đang phát (luôn 1 bài)
  - `queue` - sẽ phát
  - `loop_mode` (0=off, 1=one, 2=all), `is_shuffled`
  - `volume`, `muted`, `muted_volume`
  - `seek_offset`, `start_time`, `pause_time`, `is_paused`
  - `_skip_next_end` - counter để chặn `_on_track_end` khi stop/seek/previous
  - `stopped` - flag dừng hẳn
  - `idle_task` - auto disconnect sau 5 phút
  - `control_message` - reference tới message UI chính

## UI

- `MusicControlView` là persistent UI buttons (timeout=None)
- Edit in-place khi có thay đổi, gửi lại khi cần (xóa cũ trước)
- Button layout:
  - Row 0: ⏮️ ⏪ ⏸️/▶️ ⏩ ⏭️
  - Row 1: 🔀 🔁 ❤️/🤍 ⏹️ 🧹
  - Row 2: 🔇 🔉 🔊 📜 ⬇️

## Xử lý seek

- FFmpegPCMAudio không hỗ trợ seek trực tiếp
- Cách: restart FFmpeg với `-ss <offset>` khi seek
- Dùng `_skip_next_end` counter để chặn `after_play` cũ trigger `_on_track_end`
- Delay ~1s khi seek là chấp nhận được

## So sánh với Lavalink

| | Lavalink | yt-dlp + FFmpeg |
|--|----------|-----------------|
| Process | 2 (Java + Python) | 1 (Python) |
| RAM | ~512MB+ | ~128-256MB |
| Dependencies | Java 17+, Lavalink.jar | FFmpeg |
| Deploy | Phức tạp | 1 Dockerfile |
| Scale | Tốt (>10 guilds) | OK (~5-10 guilds đồng thời) |
| Spotify | Plugin riêng | metadata → YouTube stream |
