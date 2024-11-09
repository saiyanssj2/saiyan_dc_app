import os
import discord
from dotenv import load_dotenv
from discord import app_commands
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import cmd.play

# Load biến môi trường từ file .env
load_dotenv()
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=CLIENT_ID,
                                               client_secret=CLIENT_SECRET,
                                               redirect_uri='http://localhost:8888/callback',
                                               scope="playlist-read-private"))

def setup(bot):
    @bot.tree.command(name="s", description="Phát nhạc từ Spotify")
    @app_commands.describe(key="URL Spotify")
    async def spotify(interaction: discord.Interaction, key: str):
        id = key.split("/")[-1].split("?")[0]
        if key.split("/")[-2].split("?")[0] == 'playlist':
            data = sp.playlist(id)
            tracks = [{"title": track['track']['name'], "url": track['track']['external_urls']['spotify']} for track in data['tracks']['items']]
        else:
            data = sp.track(id)
            tracks = {"title": data['name'], "url": data['external_urls']['spotify']}

        if tracks:
            for track in tracks:
                await cmd.play.test(interaction, bot, track['title'])