import discord
from discord import ui
"""
⏯️▶️⏸⏹⏮⏪⬅️➡️⏩⏭🔁🔂🔄🔀🔊🔉❤️💖💔🛑🚫❌✅❎↻⟳⇆
#️⃣0️⃣1️⃣2️⃣3️⃣4️⃣5️⃣6️⃣7️⃣8️⃣9️⃣🇻🇳
"""

class AudioPlayer(discord.ui.View):
    def __init__(self, music_queue, voice_client, interaction, bot):
        super().__init__()
        self.music_queue = music_queue
        self.voice_client = voice_client
        self.interaction = interaction
        self.bot = bot
    
    @ui.button(emoji="⏩")
    async def next_button(self, button: ui.Button, interaction: discord.Interaction):
        self.voice_client.stop()