import discord
import asyncio
from discord import app_commands
from yt_dlp import YoutubeDL
from collections import deque
from concurrent.futures import ThreadPoolExecutor

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

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -filter:a "volume=0.25"'
}

# Khởi tạo hàng đợi cho âm thanh
class MusicQueue:
    def __init__(self):
        self.queue = deque()
        self.title = ""
        self.url = ""
        self.is_playing = False

    def add(self, item):
        self.queue.append(item)

    def get_next(self):
        if self.queue:
            next_song = self.queue.popleft()
            self.title, self.url = next_song
            return next_song
        return None

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
                music_queues[channel.id] = MusicQueue()

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
                await play_next(voice_client, music_queue)
                await interaction.followup.send(f"Now playing: {music_queue.title}")
            else:
                await interaction.followup.send(f"Queued:")
        else:
            await interaction.followup.send("Bạn cần tham gia kênh voice để phát nhạc.")

    async def play_next(voice_client, music_queue):
        # Kiểm tra xem có bài nào trong hàng đợi không
        next_song = music_queue.get_next()
        if next_song:
            title, url = next_song
            music_queue.is_playing = True
            print(f'Now playing: {title}')
            
            # Phát nhạc và xử lý callback khi nhạc kết thúc
            def on_song_end(error):
                # Nếu có lỗi, in ra lỗi
                if error:
                    print(f'Error: {error}')
                # Sử dụng asyncio để lên lịch cho bài hát tiếp theo sau khi kết thúc
                future = asyncio.run_coroutine_threadsafe(play_next(voice_client, music_queue), bot.loop)
                try:
                    future.result()
                except Exception as e:
                    print(f"Error scheduling next song: {e}")
            audio_source = discord.FFmpegPCMAudio(url, **ffmpeg_options)
            voice_client.play(audio_source, after=on_song_end)
        else:
            music_queue.is_playing = False
            # Ngắt kết nối nếu không còn bài hát
            await voice_client.disconnect()