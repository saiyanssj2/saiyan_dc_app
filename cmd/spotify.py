import os
import discord
import asyncio
from dotenv import load_dotenv
from discord import app_commands
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import cmd.play
from bot import bot

# Load biến môi trường từ file .env
load_dotenv()
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=CLIENT_ID,
                                               client_secret=CLIENT_SECRET,
                                               redirect_uri='http://localhost:8888/callback',
                                               scope="playlist-read-private"))


@bot.tree.command(name="s", description="Phát nhạc từ Spotify")
@app_commands.describe(key="URL Spotify")
async def spotify(interaction: discord.Interaction, key: str):
    id = key.split("/")[-1].split("?")[0]
    tracks = []
    if key.split("/")[-2].split("?")[0] == 'playlist':
        data = sp.playlist(id)
        tracks.extend({"query": track['track']['name'] + " " + " ".join([artist['name'] for artist in track['track']['artists']])} for track in data['tracks']['items'])
    else:
        data = sp.track(id)
        tracks.append({"query": data['name'] + " " + " ".join([artist['name'] for artist in data['artists']])})

    if tracks:
        await interaction.response.defer()
        tasks = [cmd.play.test(interaction, bot, track['query'], mess=False) for track in tracks]
        await asyncio.gather(*tasks)
        if len(tracks) == 1:
            await interaction.followup.send(f"Đã thêm {tracks[0]['query']} vào hàng đợi!")
        else:
            await interaction.followup.send(f"Đã thêm {len(tracks)} bài Spotify vào hàng đợi!")