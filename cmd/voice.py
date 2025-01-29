import os
import discord
import asyncio

# Đường dẫn đến thư mục chứa các tệp âm thanh
AUDIO_FOLDER = r'E:/Adobe'

def list_audio_files(folder_path):
    # Lấy danh sách các tệp âm thanh từ thư mục
    return [f for f in os.listdir(folder_path) if f.endswith(('.mp3', '.wav'))]

def setup(bot):
    @bot.tree.command(name="voice", description="Phát nhạc local thôi, file hoặc folder đều dc")
    async def voice(interaction: discord.Interaction, folder: str = None, file: str = None):
        if interaction.user.voice is not None:
            # Kiểm tra xem bot đã kết nối chưa
            voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)

            if voice_client is None:
                voice_channel = interaction.user.voice.channel
                # Kết nối đến kênh thoại nếu chưa có kết nối
                voice_client = await voice_channel.connect()

            if voice_client.is_playing():
                await interaction.response.send_message("Đang hát dở")
            else:
                if folder is not None:
                    # Tạo đường dẫn đầy đủ tới thư mục
                    folder_path = os.path.join(AUDIO_FOLDER, folder)

                    if os.path.isdir(folder_path):
                        folder_audio_files = list_audio_files(folder_path)

                        if folder_audio_files:
                            # Gửi phản hồi khi bắt đầu phát âm thanh từ thư mục
                            await interaction.response.send_message(f"Đang phát âm thanh từ thư mục: {folder}")

                            for file_to_play in folder_audio_files:
                                audio_source = discord.FFmpegPCMAudio(os.path.join(folder_path, file_to_play))
                                voice_client.play(audio_source)
                                # Đợi cho đến khi âm thanh hoàn thành
                                while voice_client.is_playing():
                                    await asyncio.sleep(1)
                        else:
                            await interaction.response.send_message(f"Không có tệp âm thanh nào trong thư mục '{folder}'.")
                    else:
                        await interaction.response.send_message(f"Không tìm thấy thư mục '{folder}'.")
                elif file is not None:
                    # Nếu có tham số file, phát tệp âm thanh tương ứng
                    audio_files = list_audio_files(AUDIO_FOLDER)
                    matching_files = [f for f in audio_files if f.lower().startswith(file.lower())]

                    if matching_files:
                        file_to_play = matching_files[0]  # Lấy tệp đầu tiên khớp
                        audio_source = discord.FFmpegPCMAudio(os.path.join(AUDIO_FOLDER, file_to_play))

                        # Gửi phản hồi khi bắt đầu phát âm thanh
                        await interaction.response.send_message(f"Đang phát âm thanh: {file_to_play}")
                        voice_client.play(audio_source)

                    else:
                        await interaction.response.send_message(f"Không tìm thấy tệp nào bắt đầu bằng '{file}'.")
                else:
                    await interaction.response.send_message("Bạn cần chỉ định một tên file hoặc tên thư mục để phát âm thanh.")
        else:
            await interaction.response.send_message("Bạn cần ở trong một kênh thoại để phát âm thanh.")
