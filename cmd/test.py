import discord
import asyncio
from discord import app_commands
from yt_dlp import YoutubeDL
from concurrent.futures import ThreadPoolExecutor
from lib import dc_nextsong, dc_queue

# Cấu hình YoutubeDL
ydl_opts = {
    'format': 'bestaudio/best',
    'extractaudio': True,  # Chỉ lấy âm thanh
    'audioformat': 'mp3',  # Định dạng âm thanh
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',  # Tên file
    'quiet': True,  # Tắt chế độ thông báo
    "default_search": "ytsearch",
    "extract_flat": "in_playlist"
}

music_queues = {}  # Tạo một dictionary để lưu hàng đợi cho mỗi kênh
executor = ThreadPoolExecutor()

def setup(bot):
    @bot.tree.command(name="play", description="Phát nhạc từ YouTube")
    @app_commands.describe(key="URL video YouTube hoặc từ khóa tìm kiếm")
    async def play(interaction: discord.Interaction, key: str):
        await interaction.response.defer()  # Đợi cho lệnh hoàn tất

        user = interaction.user
        if user.voice:
            channel = user.voice.channel

            # Tạo hàng đợi nếu chưa có
            if channel.id not in music_queues:
                music_queues[channel.id] = dc_queue.MusicQueue()

            music_queue = music_queues[channel.id]
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(executor, lambda: YoutubeDL(ydl_opts).extract_info(key, download=False))

            songs = []
            if "entries" in data:
                # lấy ra từng link của video
                entries = [{"title": i["title"], "url": i["url"]} for i in data["entries"] if i["uploader_id"] is not None][:300]
                async def fetch_song(entry):
                    return await loop.run_in_executor(executor, lambda: YoutubeDL(ydl_opts).extract_info(entry['url'], download=False))
                data = await asyncio.gather(*(fetch_song(entry) for entry in entries))
                for info in data:
                    songs.append({"title": info["title"], "url": info["url"]})
            else:
                songs.append(data)

            for song in songs:
                music_queue.add((song['title'], song['url']))

            # Kết nối kênh voice nếu bot chưa có mặt
            voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
            if not voice_client:
                voice_client = await channel.connect()
                await dc_nextsong.play_next(voice_client, music_queue, interaction)
            else:
                await interaction.followup.send(f"Queued!")
        else:
            await interaction.followup.send("Bạn cần tham gia kênh voice để phát nhạc.")

    