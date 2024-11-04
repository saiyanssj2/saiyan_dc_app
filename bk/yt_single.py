import discord
import asyncio
from discord import app_commands
from yt_dlp import YoutubeDL
from collections import deque

# Cấu hình YoutubeDL
ydl_opts = {
    'format': 'bestaudio/best',
    'extractaudio': True,  # Chỉ lấy âm thanh
    'audioformat': 'mp3',  # Định dạng âm thanh
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',  # Tên file
    'quiet': True,  # Tắt chế độ thông báo
}

# Khởi tạo hàng đợi cho âm thanh
class MusicQueue:
    def __init__(self):
        self.queue = deque()
        self.is_playing = False

    def add(self, item):
        self.queue.append(item)

    def get_next(self):
        if self.queue:
            return self.queue.popleft()
        return None

music_queues = {}  # Tạo một dictionary để lưu hàng đợi cho mỗi kênh

def setup(bot):
    @bot.tree.command(name="play", description="Phát nhạc từ YouTube")
    @app_commands.describe(url="URL video YouTube hoặc từ khóa tìm kiếm")
    async def play(interaction: discord.Interaction, url: str):
        await interaction.response.defer()  # Đợi cho lệnh hoàn tất

        user = interaction.user
        if user.voice:
            channel = user.voice.channel

            # Tạo hàng đợi nếu chưa có
            if channel.id not in music_queues:
                music_queues[channel.id] = MusicQueue()

            music_queue = music_queues[channel.id]

            # Lấy thông tin âm thanh từ YouTube
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                url2 = info['url']  # Lấy URL stream

            # Thêm bài hát vào hàng đợi
            music_queue.add((url2, info['title']))

            # Kết nối kênh voice nếu bot chưa có mặt
            if not discord.utils.get(bot.voice_clients, guild=interaction.guild):
                voice_client = await channel.connect()
                await play_next(voice_client, music_queue)
                await interaction.followup.send(f"Đang phát nhạc từ: {info['title']}")
            else:
                await interaction.followup.send(f"Đã thêm vào hàng đợi: {info['title']}")
        else:
            await interaction.followup.send("Bạn cần tham gia kênh voice để phát nhạc.")

    async def play_next(voice_client, music_queue):
        # Kiểm tra xem có bài nào trong hàng đợi không
        next_song = music_queue.get_next()
        if next_song:
            url, title = next_song
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

            voice_client.play(discord.FFmpegPCMAudio(url), after=on_song_end)
        else:
            music_queue.is_playing = False
            # Ngắt kết nối nếu không còn bài hát
            await voice_client.disconnect()