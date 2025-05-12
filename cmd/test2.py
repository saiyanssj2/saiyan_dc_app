from discord import Interaction
from bot import bot

@bot.tree.command(name="ping", description="Kiểm tra trạng thái bot")
async def ping(interaction: Interaction):
    await interaction.response.defer()
    await interaction.followup.send("Pong! 🏓")