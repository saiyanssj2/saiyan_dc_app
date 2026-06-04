import os
import discord
from discord import app_commands
from discord.ext import commands

from .music_core import Track
from .music_ui import SelectTrackView, build_embed

AUDIO_EXTS = {'.mp3', '.flac', '.wav', '.ogg', '.m4a', '.aac', '.opus', '.wma'}


def scan_audio_files(path: str) -> list[str]:
    """Quét file audio trong folder hoặc trả về file đơn nếu là file"""
    if os.path.isfile(path):
        if os.path.splitext(path)[1].lower() in AUDIO_EXTS:
            return [path]
        return []
    results = []
    for root, _, files in os.walk(path):
        for f in sorted(files):
            if os.path.splitext(f)[1].lower() in AUDIO_EXTS:
                results.append(os.path.join(root, f))
    return results


def make_local_track(filepath: str) -> Track:
    name = os.path.splitext(os.path.basename(filepath))[0]
    return Track(
        title=name,
        author='Local',
        url=filepath,
        stream_url=filepath,
        thumbnail=None,
        duration=0,
    )


class LocalCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="local", description="Phát nhạc từ file/folder trong máy")
    @app_commands.describe(path="Đường dẫn tuyệt đối đến file hoặc folder chứa nhạc")
    async def local(self, interaction: discord.Interaction, path: str):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ Bạn cần vào voice channel trước!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        if not os.path.exists(path):
            await interaction.followup.send("❌ Đường dẫn không tồn tại.", ephemeral=True)
            return

        files = scan_audio_files(path)
        if not files:
            await interaction.followup.send("❌ Không tìm thấy file audio nào.", ephemeral=True)
            return

        vc = interaction.guild.voice_client
        if not vc:
            vc = await interaction.user.voice.channel.connect()
        elif vc.channel != interaction.user.voice.channel:
            await vc.move_to(interaction.user.voice.channel)

        # Lấy cog music để dùng chung player
        music_cog = self.bot.cogs.get('MusicCog')
        if not music_cog:
            await interaction.followup.send("❌ MusicCog chưa được load.", ephemeral=True)
            return

        # Nếu là 1 file thì phát luôn
        if len(files) == 1:
            track = make_local_track(files[0])
            player = music_cog.get_player(interaction.guild.id)
            player.queue.append(track)

            embed = discord.Embed(
                title="✅ Đã thêm vào hàng chờ",
                description=track.title,
                color=discord.Color.green(),
            )
            embed.add_field(name="Nguồn", value="📁 Local")
            await interaction.followup.send(embed=embed, ephemeral=True)

            if not vc.is_playing() and not vc.is_paused() and not player.current:
                next_track = player.queue.pop(0)
                await music_cog.play_track(interaction.guild, vc, next_track)

            await music_cog._send_ui(interaction)
            return

        # Nhiều file → hiện dropdown (tối đa 25 do Discord giới hạn)
        tracks = [make_local_track(f) for f in files[:25]]
        view = SelectTrackView(music_cog, tracks, interaction.guild, vc, add_to_front=False)
        msg = await interaction.followup.send(
            content=f"📁 Tìm thấy {len(files)} file. Chọn bài muốn phát:",
            view=view,
            ephemeral=True,
            wait=True,
        )
        view.message = msg


async def setup(bot: commands.Bot):
    await bot.add_cog(LocalCog(bot))
