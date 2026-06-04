import asyncio
import discord
import yt_dlp
from discord import app_commands
from discord.ext import commands

from .music_core import Track, YDL_OPTS_SEARCH, YDL_OPTS_SINGLE
from .music_ui import SelectTrackView


YDL_OPTS_GENERIC = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'source_address': '0.0.0.0',
    'noplaylist': False,
    'extractor_args': {'generic': {'impersonate': True}},
}


class SearchCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="search", description="Tìm nhạc từ keyword hoặc link bất kỳ")
    @app_commands.describe(query="Từ khóa hoặc URL (YouTube, SoundCloud, v.v.)")
    async def search(self, interaction: discord.Interaction, query: str):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ Bạn cần vào voice channel trước!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        music_cog = self.bot.cogs.get('MusicCog')
        if not music_cog:
            await interaction.followup.send("❌ MusicCog chưa được load.", ephemeral=True)
            return

        vc = interaction.guild.voice_client
        if not vc:
            vc = await interaction.user.voice.channel.connect()
        elif vc.channel != interaction.user.voice.channel:
            await vc.move_to(interaction.user.voice.channel)

        is_url = query.startswith("http://") or query.startswith("https://")

        if is_url:
            await self._handle_url(interaction, vc, music_cog, query)
        else:
            await self._handle_keyword(interaction, vc, music_cog, query)

    async def _handle_keyword(self, interaction: discord.Interaction, vc: discord.VoiceClient,
                               music_cog, query: str):
        """Tìm keyword qua yt-dlp (YouTube search), hiện dropdown top 10"""
        loop = asyncio.get_running_loop()
        def _search():
            with yt_dlp.YoutubeDL(YDL_OPTS_SEARCH) as ydl:
                data = ydl.extract_info(query, download=False)
                entries = data.get('entries', [data])
                results = []
                for e in entries[:10]:
                    if not e:
                        continue
                    results.append(Track(
                        title=e.get('title', 'Unknown'),
                        author=e.get('uploader') or e.get('channel', 'Unknown'),
                        url=e.get('webpage_url', ''),
                        stream_url='',
                        thumbnail=e.get('thumbnail'),
                        duration=e.get('duration', 0),
                    ))
                return results

        tracks = await loop.run_in_executor(None, _search)
        if not tracks:
            await interaction.followup.send("❌ Không tìm thấy kết quả.", ephemeral=True)
            return

        view = SelectTrackView(music_cog, tracks, interaction.guild, vc, add_to_front=False)
        msg = await interaction.followup.send(
            content="🔍 Chọn bài hát bạn muốn phát:",
            view=view,
            ephemeral=True,
            wait=True,
        )
        view.message = msg

    async def _handle_url(self, interaction: discord.Interaction, vc: discord.VoiceClient,
                           music_cog, url: str):
        """Quét link bất kỳ, lấy danh sách audio để user chọn"""
        loop = asyncio.get_running_loop()
        def _fetch():
            with yt_dlp.YoutubeDL(YDL_OPTS_GENERIC) as ydl:
                data = ydl.extract_info(url, download=False)
                entries = data.get('entries', [data])
                results = []
                for e in entries[:25]:
                    if not e:
                        continue
                    results.append(Track(
                        title=e.get('title', 'Unknown'),
                        author=e.get('uploader') or e.get('channel', 'Unknown'),
                        url=e.get('webpage_url', '') or url,
                        stream_url=e.get('url', ''),
                        thumbnail=e.get('thumbnail'),
                        duration=e.get('duration', 0),
                    ))
                return results

        try:
            tracks = await loop.run_in_executor(None, _fetch)
        except Exception as e:
            await interaction.followup.send(f"❌ Không thể tải link: `{e}`", ephemeral=True)
            return

        if not tracks:
            await interaction.followup.send("❌ Không tìm thấy audio nào từ link này.", ephemeral=True)
            return

        # Nếu chỉ có 1 kết quả thì phát luôn
        if len(tracks) == 1:
            player = music_cog.get_player(interaction.guild.id)
            player.queue.append(tracks[0])
            embed = discord.Embed(
                title="✅ Đã thêm vào hàng chờ",
                description=f"[{tracks[0].title}]({tracks[0].url})",
                color=discord.Color.green(),
            )
            if tracks[0].thumbnail:
                embed.set_thumbnail(url=tracks[0].thumbnail)
            embed.add_field(name="Tác giả", value=tracks[0].author)
            embed.add_field(name="Thời lượng", value=tracks[0].format_duration())
            await interaction.followup.send(embed=embed, ephemeral=True)

            if not vc.is_playing() and not vc.is_paused() and not player.current:
                next_track = player.queue.pop(0)
                await music_cog.play_track(interaction.guild, vc, next_track)

            await music_cog._send_ui(interaction)
            return

        # Nhiều kết quả → dropdown
        view = SelectTrackView(music_cog, tracks, interaction.guild, vc, add_to_front=False)
        msg = await interaction.followup.send(
            content=f"🔍 Tìm thấy {len(tracks)} kết quả. Chọn bài muốn phát:",
            view=view,
            ephemeral=True,
            wait=True,
        )
        view.message = msg


async def setup(bot: commands.Bot):
    await bot.add_cog(SearchCog(bot))
