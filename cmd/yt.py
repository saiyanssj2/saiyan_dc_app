import discord
import yt_dlp
import asyncio
from bot import bot

# Thêm các cờ reconnect để giảm thiểu lỗi ngắt nhạc
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -filter:a "volume=0.25"'
}

class YouTubePlayer(discord.ui.View):
    def __init__(self, songs, voice_client):
        super().__init__(timeout=None)
        # self.bot = bot
        self.songs = songs
        self.voice_client = voice_client
        self.current_song_index = 0
        self.page_size = 5
        self.current_page = 0
        self.total_pages = (len(self.songs) + self.page_size - 1) // self.page_size
        self.loop_mode = 0  # 0: No loop, 1: Loop one, 2: Loop all
        self.is_playing = False

        # Cập nhật nút phát và điều hướng
        self.update_page_buttons()
        self.create_navigation_buttons()

    def update_page_buttons(self):
        self.clear_items()
        start = self.current_page * self.page_size
        end = min(start + self.page_size, len(self.songs))
        for i in range(start, end):
            play_button = discord.ui.Button(label="▶️", style=discord.ButtonStyle.success)
            play_button.callback = self.create_play_callback(i)
            self.add_item(play_button)

    def create_play_callback(self, index):
        async def play_callback(interaction: discord.Interaction):
            if self.voice_client.is_playing():
                self.voice_client.stop()
            await self.play_song(index, interaction)
        return play_callback

    async def play_song(self, index, interaction):
        self.current_song_index = index
        audio_source = discord.FFmpegPCMAudio(self.songs[index]['url'], **ffmpeg_options)
        self.is_playing = True
        # self.voice_client.play(audio_source, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_song(index+1, interaction), self.bot.loop))
        self.voice_client.play(audio_source)
        # print(self.bot)
        await self.send_now_playing(interaction)

    async def send_now_playing(self, interaction):
        embed = discord.Embed(title="Đang phát", description=self.songs[self.current_song_index]['title'], color=0x00ff00)
        
        # Kiểm tra nếu phản hồi đã được gửi
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=embed, view=self)
        else:
            # Nếu đã phản hồi, dùng followup để gửi tin nhắn mới
            await interaction.followup.send(embed=embed, view=self)

    async def song_end_callback(self, interaction):
        if self.loop_mode == 1:
            await self.play_song(self.current_song_index, interaction)
        elif self.loop_mode == 2 and self.current_song_index == len(self.songs) - 1:
            self.current_song_index = 0
            await self.play_song(self.current_song_index, interaction)
        elif self.current_song_index < len(self.songs) - 1:
            self.current_song_index += 1
            await self.play_song(self.current_song_index, interaction)

    async def stop_audio(self, interaction):
        if self.voice_client.is_playing():
            self.voice_client.stop()
            await interaction.response.send_message("Đã dừng phát nhạc.")

    async def pause_audio(self, interaction):
        if self.voice_client.is_playing():
            self.voice_client.pause()
            await interaction.response.send_message("Đã tạm dừng phát nhạc.")

    async def resume_audio(self, interaction):
        if self.voice_client.is_paused():
            self.voice_client.resume()
            await interaction.response.send_message("Đã tiếp tục phát nhạc.")

    async def next_song(self, interaction: discord.Interaction):
        if self.current_song_index < len(self.songs) - 1:
            self.current_song_index += 1
            await self.play_song(self.current_song_index, interaction)
        else:
            await interaction.response.send_message("Đã đến bài hát cuối cùng.")

    async def previous_song(self, interaction):
        if self.current_song_index > 0:
            self.current_song_index -= 1
            await self.play_song(self.current_song_index, interaction)
        else:
            await interaction.response.send_message("Đây là bài hát đầu tiên.")

    async def next_page(self, interaction):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_page_buttons()
            self.create_navigation_buttons()
            await interaction.response.edit_message(view=self)

    async def previous_page(self, interaction):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_page_buttons()
            self.create_navigation_buttons()
            await interaction.response.edit_message(view=self)

    async def toggle_loop(self, interaction):
        self.loop_mode = (self.loop_mode + 1) % 3
        modes = ["Tắt lặp", "Lặp 1 bài", "Lặp tất cả"]
        await interaction.response.send_message(f"Chế độ lặp: {modes[self.loop_mode]}")
        self.update_button_states()

    def create_navigation_buttons(self):
        stop_button = discord.ui.Button(label="Stop", style=discord.ButtonStyle.danger)
        stop_button.callback = self.stop_audio

        pause_button = discord.ui.Button(label="Pause", style=discord.ButtonStyle.secondary)
        pause_button.callback = self.pause_audio

        resume_button = discord.ui.Button(label="Resume", style=discord.ButtonStyle.secondary)
        resume_button.callback = self.resume_audio

        prev_song_button = discord.ui.Button(label="Previous", style=discord.ButtonStyle.secondary)
        prev_song_button.callback = self.previous_song

        next_song_button = discord.ui.Button(label="Next", style=discord.ButtonStyle.secondary)
        next_song_button.callback = self.next_song

        self.add_item(stop_button)
        self.add_item(pause_button)
        self.add_item(resume_button)
        self.add_item(prev_song_button)
        self.add_item(next_song_button)

        # Nút điều hướng trang
        if self.current_page > 0:
            prev_page_button = discord.ui.Button(label="<< Previous Page", style=discord.ButtonStyle.secondary)
            prev_page_button.callback = self.previous_page
            self.add_item(prev_page_button)

        if self.current_page < self.total_pages - 1:
            next_page_button = discord.ui.Button(label="Next Page >>", style=discord.ButtonStyle.secondary)
            next_page_button.callback = self.next_page
            self.add_item(next_page_button)

@bot.tree.command(name="yt", description="Đưa tao cái link zutube")
async def yt(interaction: discord.Interaction, link: str):
    # Kiểm tra user
    if interaction.user.voice is None:
        await interaction.response.send_message("Bạn cần ở trong kênh thoại để phát nhạc.")
        return
    # Join vào kênh user
    voice_channel = interaction.user.voice.channel
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if voice_client is None:
        voice_client = await voice_channel.connect()

    await interaction.response.defer()

    async def load_playlist():
        ytdl_opts = {
                        "format": "bestaudio/best",
                        "quiet": True,
                        "noplaylist": False,
                        "default_search": "ytsearch",
                        "extract_flat": "in_playlist"
                    }
        with yt_dlp.YoutubeDL(ytdl_opts) as ytdl:
            data = ytdl.extract_info(link, download=False)

        if "entries" in data:
            songs = [{"title": entry["title"], "url": entry["url"]} for entry in data["entries"] if entry.get("channel_id")]
        else:
            songs = [{"title": data["title"], "url": data["url"]}]

        if not hasattr(bot, 'current_player_view'):
            view = YouTubePlayer(songs, voice_client)
            await view.play_song(0, interaction)
            bot.current_player_view = view
        else:
            bot.current_player_view.songs += songs
            await bot.current_player_view.send_now_playing(interaction)

    # Khởi chạy load_playlist không đồng bộ
    asyncio.create_task(load_playlist())
