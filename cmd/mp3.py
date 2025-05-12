import discord
import requests
from bs4 import BeautifulSoup
from bot import bot
class AudioPlayer(discord.ui.View):
    def __init__(self, audio_links, audio_descriptions, voice_client, page=0):
        super().__init__(timeout=None)
        self.audio_links = audio_links
        self.audio_descriptions = audio_descriptions
        self.voice_client = voice_client
        self.page = page
        self.page_size = 10
        self.total_pages = (len(self.audio_descriptions) + self.page_size - 1) // self.page_size

        self.create_buttons()

        stop_button = discord.ui.Button(label="Stop", style=discord.ButtonStyle.danger)
        stop_button.callback = self.stop_audio
        self.add_item(stop_button)

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
            play_button = discord.ui.Button(label="Play", style=discord.ButtonStyle.success)
            play_button.callback = self.play_button(i)  # Gán callback cho nút với số thứ tự tương ứng
            description = f"{i+1}. {self.audio_descriptions[i][:50] + '...' if len(self.audio_descriptions[i]) > 50 else self.audio_descriptions[i]}"  # Thêm mô tả cho thoại
            self.add_item(play_button)
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

@bot.tree.command(name="mp3", description="Cho tao cái link chứa file mp3")
async def mp3(interaction: discord.Interaction, link: str):
    voice_channel = interaction.user.voice.channel

    if voice_channel is not None:
        # Kiểm tra xem bot đã kết nối chưa
        voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)

        if voice_client is None:
            # Kết nối đến kênh thoại nếu chưa có kết nối
            voice_client = await voice_channel.connect()

        try:
            await interaction.response.defer()
            audio_url = link
            response = requests.get(audio_url)
            soup = BeautifulSoup(response.content, "html.parser")
            audio_buttons = soup.find_all("audio", class_="ext-audiobutton")

            if audio_buttons:
                audio_links = []
                audio_descriptions = []
                dialogue_set = set()

                for audio in audio_buttons:
                    source = audio.find("source")
                    if source and source.has_attr('src'):
                        description_tag = audio.find_next("i")
                        description = description_tag.text.strip() if description_tag else "Không có hội thoại."

                        # Loại bỏ đoạn thoại trùng lặp
                        if description not in dialogue_set:
                            audio_links.append(source['src'])
                            audio_descriptions.append(description)
                            dialogue_set.add(description)

                if audio_links:
                    voice_client.play(discord.FFmpegPCMAudio(audio_links[0]))
                    # Tạo một view chứa các nút phát âm thanh và nút stop
                    view = AudioPlayer(audio_links, audio_descriptions, voice_client)
                    # Gửi message kèm các nút
                    await interaction.followup.send(
                        f"Có {len(audio_links)} âm thanh cho link **{link}**. Chọn nút để phát:",
                        view=view
                    )
                else:
                    await interaction.followup.send("Không tìm thấy âm thanh cho link.")
            else:
                await interaction.followup.send("Không tìm thấy âm thanh cho link.")
        except Exception as e:
            print(f"Có lỗi xảy ra khi xử lý lệnh /mp3: {str(e)}")
            await interaction.followup.send("Có lỗi xảy ra trong quá trình xử lý lệnh.")
    else:
        await interaction.response.send_message("Bạn cần ở trong một kênh thoại để phát âm thanh.")
