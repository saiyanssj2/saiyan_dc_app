import discord
import os
import sys
import asyncio
import logging
from discord.ext import commands
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

load_dotenv()

# ─── Logging setup ───────────────────────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_LOG_DIR = os.path.join(_BASE_DIR, 'logs')
os.makedirs(_LOG_DIR, exist_ok=True)

# File handler - ghi DEBUG trở lên, flush real-time
class FlushFileHandler(logging.FileHandler):
    def emit(self, record):
        super().emit(record)
        self.stream.flush()
        os.fsync(self.stream.fileno())

file_handler = FlushFileHandler(os.path.join(_LOG_DIR, 'bot.log'), encoding='utf-8', mode='w')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))

# Console handler - chỉ hiện ERROR trở lên
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.ERROR)
console_handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))

logger = logging.getLogger('saiyan')
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Giảm noise từ discord.py và yt-dlp
logging.getLogger('discord').setLevel(logging.WARNING)
logging.getLogger('discord.http').setLevel(logging.WARNING)
logging.getLogger('yt_dlp').setLevel(logging.WARNING)

class SaiyanBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        logger.info("[setup] loading music_cog...")
        await self.load_extension("cogs.music_cog")
        logger.info("[setup] loading local_cog...")
        await self.load_extension("cogs.local_cog")
        logger.info("[setup] loading search_cog...")
        await self.load_extension("cogs.search_cog")
        logger.info("[setup] loading spotify_cog...")
        await self.load_extension("cogs.spotify_cog")
        logger.info("[setup] loading lol_cog...")
        await self.load_extension("cogs.lol_cog")
        logger.info("[setup] syncing commands...")
        synced = await self.tree.sync()
        logger.info(f"✅ Đã đồng bộ {len(synced)} Slash Commands: {[c.name for c in synced]}")

bot = SaiyanBot()

@bot.event
async def on_ready():
    logger.info(f"---")
    logger.info(f"Logged in as: {bot.user}")
    logger.info(f"ID: {bot.user.id}")
    logger.info(f"---")

async def main():
    async with bot:
        await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot đang tắt...")
