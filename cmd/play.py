import re
import discord
import asyncio
from discord import app_commands
from yt_dlp import YoutubeDL
from concurrent.futures import ThreadPoolExecutor
from lib import dc_nextsong, dc_queue

# Cấu hình YoutubeDL
ydl_opts = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'quiet': True,
    "default_search": "ytsearch"
}

music_queues = {}
executor = ThreadPoolExecutor()

def setup(bot):
    @bot.tree.command(name="p", description="Play music")
    @app_commands.describe(query="Enter song name or link")
    async def play(interaction: discord.Interaction, query: str):
        await test(interaction, bot, query)

async def test(interaction, bot, query):
    await interaction.response.defer()
    print(query)
    user = interaction.user
    if user.voice:
        channel = user.voice.channel

        if channel.id not in music_queues:
            music_queues[channel.id] = dc_queue.MusicQueue()

        music_queue = music_queues[channel.id]
        loop = asyncio.get_event_loop()

        data = await loop.run_in_executor(executor, lambda: YoutubeDL(ydl_opts).extract_info(query, download=False))
        if "entries" in data:
            entries = [{"title": i["title"], "url": i["url"]} for i in data["entries"] if i["uploader_id"] is not None][:300]
            if re.match(r'^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+$', entries[0]['url']):
                async def fetch_song(entry):
                    return await loop.run_in_executor(executor, lambda: YoutubeDL(ydl_opts).extract_info(entry['url'], download=False))
                datas = await asyncio.gather(*(fetch_song(entry) for entry in entries))
                for i in datas:
                    music_queue.add((i['title'], i['url']))
            else:
                for i in entries:
                    music_queue.add((i['title'], i['url']))
        else:
            music_queue.add((data['title'], data['url']))

        voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
        if not voice_client:
            voice_client = await channel.connect()
            await dc_nextsong.play_next(voice_client, music_queue, interaction, bot)
        else:
            await interaction.followup.send(f"Queued! {len(music_queue.queue)} bài!")
    else:
        await interaction.followup.send("Join vào 1 voice chat đi thằng ngoo!")
