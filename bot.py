import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
from importlib import import_module

# Load biến môi trường từ file .env
load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = os.getenv('GUILD_ID')

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

# Sử dụng cmd
# Thư mục chứa các lệnh cmd
cmd_folder = './cmd'
# Lấy tất cả các file .py trong thư mục cmd và import chúng
for filename in os.listdir(cmd_folder):
    if filename.endswith('.py') and filename != '__init__.py':
        module_name = filename[:-3]
        module = import_module(f'cmd.{module_name}')
        # Gọi setup cho từng module nếu có
        if hasattr(module, 'setup'):
            module.setup(bot)

# Khởi động bot
bot.run(DISCORD_TOKEN)
