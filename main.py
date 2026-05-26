import discord
import os
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

class SaiyanBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.load_extension("cogs.music_cog")
        await self.tree.sync()
        print("✅ Đã đồng bộ Slash Commands!")

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
