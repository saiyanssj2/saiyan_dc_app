import discord

def setup(bot):
    # Lệnh để bot rời khỏi kênh thoại
    @bot.tree.command(name="leave", description="Make the bot leave the voice channel")
    async def leave(interaction: discord.Interaction):
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("Đã rời khỏi kênh thoại!")
        else:
            await interaction.response.send_message("Bot không ở trong kênh thoại!")