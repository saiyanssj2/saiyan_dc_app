import discord
import os
import sys
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

load_dotenv()

class SaiyanBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        print("[setup] loading music_cog...")
        await self.load_extension("cogs.music_cog")
        print("[setup] loading local_cog...")
        await self.load_extension("cogs.local_cog")
        print("[setup] loading search_cog...")
        await self.load_extension("cogs.search_cog")
        print("[setup] loading spotify_cog...")
        await self.load_extension("cogs.spotify_cog")
        print("[setup] loading lol_cog...")
        await self.load_extension("cogs.lol_cog")
        print("[setup] syncing commands...")
        synced = await self.tree.sync()
        print(f"✅ Đã đồng bộ {len(synced)} Slash Commands: {[c.name for c in synced]}")

bot = SaiyanBot()

@bot.event
async def on_ready():
    print(f"---")
    print(f"Logged in as: {bot.user}")
    print(f"ID: {bot.user.id}")
    print(f"---")

async def main():
    async with bot:
        await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot đang tắt...")
