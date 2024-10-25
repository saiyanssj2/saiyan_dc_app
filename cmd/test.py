import discord
from discord.ext import commands
import yt_dlp

class YouTubePlayer(discord.ui.View):
    def __init__(self, songs, voice_client):
        super().__init__(timeout=None)
        self.songs = songs
        self.voice_client = voice_client
        self.current_song_index = 0
        self.page_size = 5
        self.current_page = 0
        self.total_pages = (len(self.songs) + self.page_size - 1) // self.page_size

        # Tạo các nút cho trang đầu tiên
        self.update_page_buttons()
        self.create_navigation_buttons()

    def update_page_buttons(self):
        self.clear_items()
        start = self.current_page * self.page_size
        end = min(start + self.page_size, len(self.songs))
        for i in range(start, end):
            play_button = discord.ui.Button(label=self.songs[i]['title'], style=discord.ButtonStyle.success)
            play_button.callback = self.create_play_callback(i)
            self.add_item(play_button)

    def create_play_callback(self, index):
        async def play_callback(interaction: discord.Interaction):
            if not self.voice_client.is_playing():
                self.play_song(index)
                await interaction.response.send_message(f"Đang phát: {self.songs[index]['title']}")
            else:
                await interaction.response.send_message("Bot đang phát bài khác.")
        return play_callback
        
    def create_play_callback(self, index):
        async def play_callback(interaction: discord.Interaction):
            # Nếu bot đang phát nhạc, dừng bài hát hiện tại trước khi phát bài mới
            if self.voice_client.is_playing():
                self.voice_client.stop()
            
            # Phát bài hát được chọn
            self.play_song(index)
            await interaction.response.send_message(f"Đang phát: {self.songs[index]['title']}")
            
        return play_callback


    def play_song(self, index):
        self.current_song_index = index
        self.voice_client.play(discord.FFmpegPCMAudio(self.songs[index]['url']))

    async def stop_audio(self, interaction: discord.Interaction):
        if self.voice_client.is_playing():
            self.voice_client.stop()
            await interaction.response.send_message("Đã dừng phát nhạc.")
        else:
            await interaction.response.send_message("Không có bài hát nào đang phát.")

    async def pause_audio(self, interaction: discord.Interaction):
        if self.voice_client.is_playing():
            self.voice_client.pause()
            await interaction.response.send_message("Đã tạm dừng phát nhạc.")
        else:
            await interaction.response.send_message("Không có nhạc nào để dừng.")

    async def resume_audio(self, interaction: discord.Interaction):
        if self.voice_client.is_paused():
            self.voice_client.resume()
            await interaction.response.send_message("Đã tiếp tục phát nhạc.")
        else:
            await interaction.response.send_message("Không có nhạc nào để tiếp tục.")

    async def next_song(self, interaction: discord.Interaction):
        if self.current_song_index < len(self.songs) - 1:
            self.current_song_index += 1
            self.play_song(self.current_song_index)
            await interaction.response.send_message(f"Đang phát: {self.songs[self.current_song_index]['title']}")
        else:
            await interaction.response.send_message("Đã đến bài hát cuối cùng.")

    async def previous_song(self, interaction: discord.Interaction):
        if self.current_song_index > 0:
            self.current_song_index -= 1
            self.play_song(self.current_song_index)
            await interaction.response.send_message(f"Đang phát: {self.songs[self.current_song_index]['title']}")
        else:
            await interaction.response.send_message("Đây là bài hát đầu tiên.")

    async def next_page(self, interaction: discord.Interaction):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_page_buttons()
            self.create_navigation_buttons()
            await interaction.response.edit_message(view=self)

    async def previous_page(self, interaction: discord.Interaction):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_page_buttons()
            self.create_navigation_buttons()
            await interaction.response.edit_message(view=self)

    def create_navigation_buttons(self):
        # Thêm các nút điều khiển phát nhạc
        stop_button = discord.ui.Button(label="Stop", style=discord.ButtonStyle.danger)
        stop_button.callback = self.stop_audio
        self.add_item(stop_button)

        pause_button = discord.ui.Button(label="Pause", style=discord.ButtonStyle.secondary)
        pause_button.callback = self.pause_audio
        self.add_item(pause_button)

        resume_button = discord.ui.Button(label="Resume", style=discord.ButtonStyle.secondary)
        resume_button.callback = self.resume_audio
        self.add_item(resume_button)

        previous_song_button = discord.ui.Button(label="Previous Song", style=discord.ButtonStyle.secondary)
        previous_song_button.callback = self.previous_song
        self.add_item(previous_song_button)

        next_song_button = discord.ui.Button(label="Next Song", style=discord.ButtonStyle.secondary)
        next_song_button.callback = self.next_song
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


def setup(bot):
    @bot.tree.command(name="yt")
    async def yt(interaction: discord.Interaction, link: str):
        voice_channel = interaction.user.voice.channel
        if voice_channel is None:
            await interaction.response.send_message("Bạn cần ở trong kênh thoại để phát nhạc.")
            return

        voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
        if voice_client is None:
            voice_client = await voice_channel.connect()

        await interaction.response.defer()

        ytdl_opts = {"format": "bestaudio/best", "quiet": True, "extract_flat": True}
        with yt_dlp.YoutubeDL(ytdl_opts) as ytdl:
            data = ytdl.extract_info(link, download=False)

        if "entries" in data:
            
            # Lọc chỉ các video có URL hợp lệ
            new_songs = [{"title": entry["title"], "url": entry["url"]} for entry in data["entries"] if entry.get("url")]

            # Kiểm tra nếu đã có view phát nhạc trước đó
            if hasattr(bot, "current_player_view") and bot.current_player_view.voice_client == voice_client:
                # Append danh sách mới vào danh sách hiện tại
                bot.current_player_view.songs.extend(new_songs)
                # Cập nhật giao diện để hiển thị danh sách mới
                await interaction.followup.send("Đã thêm danh sách mới vào hàng chờ:")
                await interaction.edit_original_response(view=bot.current_player_view)
            else:
                # Phát video đầu tiên
                first_entry = data["entries"][0]
                if first_entry.get("url"):
                    first_song = {"title": first_entry["title"], "url": first_entry["url"]}
                    view = YouTubePlayer([first_song], voice_client)
                    bot.current_player_view = view
                    await interaction.followup.send(f"Đang phát: {first_song['title']}", view=view)
                # Nếu không có view trước đó, tạo mới
                bot.current_player_view = YouTubePlayer(new_songs, voice_client)
                await interaction.followup.send("Danh sách phát nhạc:", view=bot.current_player_view)
        else:
            await interaction.followup.send("Không tìm thấy danh sách phát nhạc.")