import os
import discord
import asyncio
from dotenv import load_dotenv
from discord import app_commands
from concurrent.futures import ThreadPoolExecutor
from spotdl import Spotdl
from lib import dc_nextsong, dc_queue

music_queues = {}
executor = ThreadPoolExecutor()
# Load biến môi trường từ file .env
load_dotenv()
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
spotdl = Spotdl(CLIENT_ID,CLIENT_SECRET)

def setup(bot):
    @bot.tree.command(name="s", description="Phát nhạc từ Spotify")
    @app_commands.describe(key="URL hoặc từ khóa Spotify")
    async def spotify(interaction: discord.Interaction, key: str):
        await interaction.response.defer()

        user = interaction.user
        if user.voice:
            channel = user.voice.channel
            if channel.id not in music_queues:
                music_queues[channel.id] = dc_queue.MusicQueue()

            music_queue = music_queues[channel.id]
            loop = asyncio.get_event_loop()

            # Sử dụng spotdl để tìm URL phát nhạc từ Spotify
            async def fetch_spotify_data(key):
                return await loop.run_in_executor(executor, lambda: spotdl.search(key))

            songs = []
            spotify_url = await fetch_spotify_data(key)
            if spotify_url:
                # song = {"title": spotify_url['name'], "url": spotify_url['url']}
                # music_queue.add((song['title'], song['url']))
                for track in spotify_url:
                    songs.append({"title": track['name'], "url": track['url']})
                
                # Kết nối voice client và phát nhạc nếu chưa có
                voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
                if not voice_client:
                    voice_client = await channel.connect()
                    await dc_nextsong.play_next(voice_client, music_queue, interaction)
                else:
                    await interaction.followup.send(f"Queued!")
            else:
                await interaction.followup.send("Không tìm thấy bài hát trên Spotify.")
        else:
            await interaction.followup.send("Bạn cần tham gia kênh voice để phát nhạc.")