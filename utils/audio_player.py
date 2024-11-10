import discord
from discord import ui
from utils import dc_nextsong
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
        await dc_nextsong.start_music(self.voice_client, self.music_queue, self.interaction, self.bot)

    def create(self):
        next_song_button = discord.ui.Button(label="Next", style=discord.ButtonStyle.secondary)
        next_song_button.callback = self.next_song()
    async def next_song(self):
        self.voice_client.stop()
        await dc_nextsong.start_music(self.voice_client, self.music_queue, self.interaction, self.bot)