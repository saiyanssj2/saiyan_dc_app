import discord
from discord import app_commands
from utils import dc_queue

music_queues = {}
def setup(bot):
    @bot.tree.command(name="p", description="Play music")
    @app_commands.describe(query="Enter song name or link")
    async def play(interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        voice = interaction.user.voice
        if voice:
            id = voice.channel.id

            if id not in music_queues:
                music_queues[id] = dc_queue.MusicQueue()

            music_queue = music_queues[id]
        else:
            await interaction.followup.send("chưa join")