import os
from dotenv import load_dotenv
from bot import bot
import cmd.test2

load_dotenv()

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()  # Đồng bộ lệnh slash
        print(f"Đã đồng bộ {len(synced)} lệnh slash.")
    except Exception as e:
        print(f"Lỗi đồng bộ lệnh: {e}")

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
bot.run(DISCORD_TOKEN)