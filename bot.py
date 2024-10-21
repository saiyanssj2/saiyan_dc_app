import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
import cmd.ping as ping

# Load biến môi trường từ file .env
load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = os.getenv('GUILD_ID')

import discord
from discord.ext import commands

# Tạo bot với intent
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    # Đồng bộ global commands
    await bot.tree.sync()  # Đăng ký lệnh toàn cầu
    print("Global commands synced!")

ping.setup(bot)
# # Tạo một lệnh toàn cầu (global slash command)
# @bot.tree.command(name="ping", description="Ping command to check the bot's latency")
# async def ping(interaction: discord.Interaction):
#     latency_ms = bot.latency * 1000
#     await interaction.response.send_message(f"Pong! {latency_ms:.0f} ms")

# Khởi động bot
bot.run(DISCORD_TOKEN)
