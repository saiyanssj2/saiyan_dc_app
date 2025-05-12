import os
from dotenv import load_dotenv
from bot import bot
from cmd import *

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    # Đồng bộ global commands
    await bot.tree.sync()
    print("Global commands synced!")

bot.run(DISCORD_TOKEN)
