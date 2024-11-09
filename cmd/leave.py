import discord

def setup(bot):
    # Lệnh để bot rời khỏi kênh thoại
    @bot.tree.command(name="leave", description="Make the bot leave the voice channel")
    async def leave(interaction: discord.Interaction):
        if interaction.guild.voice_client:
            await interaction.response.send_message("Đã cook!")
            await interaction.guild.voice_client.disconnect()
        else:
            await interaction.response.send_message("Bot không ở trong kênh thoại!")