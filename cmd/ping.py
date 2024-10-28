import discord

def setup(bot):
    # Tạo lệnh toàn cầu (global slash command)
    @bot.tree.command(name="ping", description="Ping là Ping")
    async def ping(interaction: discord.Interaction):
        latency_ms = bot.latency * 1000  # Đo độ trễ của bot
        await interaction.response.send_message(f"Pong! {latency_ms:.0f} ms")
