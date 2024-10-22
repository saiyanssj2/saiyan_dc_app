import discord

def setup(bot):
    # Tạo lệnh toàn cầu (global slash command)
    @bot.tree.command(name="voice", description="voice")
    async def voice(interaction: discord.Interaction):
        # Kiểm tra xem người dùng có đang ở trong kênh thoại không
        if not interaction.user.voice:
            await interaction.response.send_message("Bạn cần ở trong một kênh thoại để sử dụng lệnh này!")
            return

        voice_channel = interaction.user.voice.channel

        # Kết nối bot với kênh thoại
        if not interaction.guild.voice_client:
            await interaction.response.send_message(f"Đang tham gia kênh {voice_channel.name}...")
            voice_client = await voice_channel.connect()
        else:
            voice_client = interaction.guild.voice_client

        # Phát âm thanh
        audio_source = discord.FFmpegPCMAudio(r'''E:\Adobe\z.mp3''')  # Đường dẫn tới file âm thanh
        if not voice_client.is_playing():
            voice_client.play(audio_source, after=lambda e: print(f'Hoàn thành phát âm thanh: {e}'))
            await interaction.response.send_message("Đang phát âm thanh!")
        else:
            await interaction.response.send_message("Đã có âm thanh đang phát!")
