import discord

class AudioPlayer(discord.ui.View):
    def __init__(self, audio_links, audio_descriptions, voice_client, page=0):
        super().__init__(timeout=None)
        self.audio_links = audio_links
        self.audio_descriptions = audio_descriptions
        self.voice_client = voice_client
        self.page = page
        self.page_size = 10  # Giới hạn mỗi trang hiển thị 10 nút
        self.total_pages = (len(self.audio_descriptions) + self.page_size - 1) // self.page_size

        # Tạo các nút cho trang hiện tại
        self.create_buttons()

        # Thêm nút "Stop" để dừng âm thanh
        stop_button = discord.ui.Button(label="Stop", style=discord.ButtonStyle.danger)
        stop_button.callback = self.stop_audio
        self.add_item(stop_button)

        # Nút điều hướng trang
        if self.page > 0:
            prev_button = discord.ui.Button(label="<< Previous", style=discord.ButtonStyle.secondary)
            prev_button.callback = self.previous_page
            self.add_item(prev_button)

        if self.page < self.total_pages - 1:
            next_button = discord.ui.Button(label="Next >>", style=discord.ButtonStyle.secondary)
            next_button.callback = self.next_page
            self.add_item(next_button)

    def create_buttons(self):
        start = self.page * self.page_size
        end = min(start + self.page_size, len(self.audio_descriptions))
        for i in range(start, end):
            # Tạo description kèm nút Play song song
            play_button = discord.ui.Button(label="Play", style=discord.ButtonStyle.success)
            play_button.callback = self.play_button(i)  # Gán callback cho nút với số thứ tự tương ứng
            description = f"{i+1}. {self.audio_descriptions[i][:50] + '...' if len(self.audio_descriptions[i]) > 50 else self.audio_descriptions[i]}"  # Thêm mô tả cho thoại
            self.add_item(play_button)
            # Tạo dòng mô tả song song với nút Play
            self.add_item(discord.ui.Button(label=description, style=discord.ButtonStyle.secondary, disabled=True))

    def play_button(self, index):
        async def callback(interaction: discord.Interaction):
            if not self.voice_client.is_playing():
                # Phát file audio tương ứng với chỉ số
                self.voice_client.play(discord.FFmpegPCMAudio(self.audio_links[index]))
                await interaction.response.send_message(f"Đang phát âm thanh: {self.audio_descriptions[index]}")
            else:
                await interaction.response.send_message("Bot đang phát âm thanh khác.")
        return callback

    async def stop_audio(self, interaction: discord.Interaction):
        if self.voice_client.is_playing():
            self.voice_client.stop()  # Dừng âm thanh hiện tại
            await interaction.response.send_message("Âm thanh đã được dừng.")
        else:
            await interaction.response.send_message("Không có âm thanh nào đang phát.")

    async def previous_page(self, interaction: discord.Interaction):
        # Chuyển sang trang trước
        view = AudioPlayer(self.audio_links, self.audio_descriptions, self.voice_client, page=self.page - 1)
        await interaction.response.edit_message(view=view)

    async def next_page(self, interaction: discord.Interaction):
        # Chuyển sang trang sau
        view = AudioPlayer(self.audio_links, self.audio_descriptions, self.voice_client, page=self.page + 1)
        await interaction.response.edit_message(view=view)