import asyncio
import os
import discord
import yt_dlp
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from .logger import logger

from .music_core import Track, YDL_OPTS_SEARCH
from .music_ui import SelectTrackView

load_dotenv()

def _make_spotify() -> spotipy.Spotify | None:
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None
    return spotipy.Spotify(auth_manager=SpotifyClientCredentials(
        client_id=client_id,
        client_secret=client_secret,
    ))


def _parse_spotify_url(url: str) -> tuple[str, str] | None:
    """Trả về (type, id) từ Spotify URL. type: track | album | playlist"""
    # https://open.spotify.com/track/xxx hoặc spotify:track:xxx
    import re
    # Match URL dạng open.spotify.com/track/xxx hoặc spotify:track:xxx
    m = re.search(r'(?:spotify\.com|spotify)[:/](?:intl-\w+/)?(track|album|playlist)[:/]([A-Za-z0-9]+)', url)
    if m:
        return m.group(1), m.group(2)
    return None


def _spotify_track_to_query(item: dict) -> str:
    name = item.get('name', '')
    artists = ', '.join(a['name'] for a in item.get('artists', []))
    return f"{name} {artists}"


def _spotify_track_to_meta(item: dict) -> dict:
    name = item.get('name', 'Unknown')
    artists = ', '.join(a['name'] for a in item.get('artists', []))
    images = item.get('album', {}).get('images', [])
    thumbnail = images[0]['url'] if images else None
    duration_ms = item.get('duration_ms', 0)
    url = item.get('external_urls', {}).get('spotify', '')
    return {
        'title': name,
        'author': artists,
        'thumbnail': thumbnail,
        'duration': duration_ms // 1000,
        'spotify_url': url,
        'query': f"{name} {artists}",
    }


class SpotifyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sp = _make_spotify()

    @app_commands.command(name="spotify", description="Phát nhạc từ Spotify (track, album, playlist)")
    @app_commands.describe(query="Từ khóa tìm kiếm hoặc link Spotify")
    async def spotify(self, interaction: discord.Interaction, query: str):
        await interaction.response.send_message(
            "⚠️ **Tính năng Spotify tạm dừng**\n\n"
            "Spotify API yêu cầu chủ bot phải có tài khoản Premium. "
            "Nếu bạn muốn sử dụng lệnh này, hãy cho mình dùng chung Premium nhé!\n\n"
            "Trong khi chờ, bạn có thể dùng `/play` với từ khóa hoặc link YouTube.",
            ephemeral=True,
        )

    # ─── Handlers ────────────────────────────────────────────────────────────

    async def _handle_search(self, interaction: discord.Interaction, vc, music_cog, query: str):
        """Tìm keyword trên Spotify, hiện top 10"""
        loop = asyncio.get_running_loop()
        def _search():
            logger.debug(f"[spotify._handle_search] searching: {query}")
            results = self.sp.search(q=query, type='track', limit=10)
            items = results.get('tracks', {}).get('items', [])
            logger.debug(f"[spotify._handle_search] found {len(items)} items")
            return [_spotify_track_to_meta(item) for item in items if item]

        metas = await loop.run_in_executor(None, _search)
        if not metas:
            await interaction.followup.send("❌ Không tìm thấy kết quả.", ephemeral=True)
            return

        logger.debug(f"[spotify._handle_search] metas={[m['title'] for m in metas[:3]]}")
        tracks = [Track(
            title=m['title'],
            author=m['author'],
            url=m['spotify_url'],
            stream_url='',
            thumbnail=m['thumbnail'],
            duration=m['duration'],
        ) for m in metas]

        view = SelectTrackView(music_cog, tracks, interaction.guild, vc, add_to_front=False)
        msg = await interaction.followup.send(
            content="🎵 Chọn bài hát Spotify bạn muốn phát:",
            view=view,
            ephemeral=True,
            wait=True,
        )
        view.message = msg

    async def _handle_track(self, interaction: discord.Interaction, vc, music_cog, track_id: str):
        """Phát 1 track Spotify"""
        loop = asyncio.get_running_loop()
        def _fetch():
            item = self.sp.track(track_id)
            return _spotify_track_to_meta(item)

        meta = await loop.run_in_executor(None, _fetch)
        track = await self._resolve_youtube(meta)

        player = music_cog.get_player(interaction.guild.id)
        player.queue.append(track)

        embed = discord.Embed(
            title="✅ Đã thêm vào hàng chờ",
            description=f"[{track.title}]({meta['spotify_url']})",
            color=discord.Color.green(),
        )
        if track.thumbnail:
            embed.set_thumbnail(url=track.thumbnail)
        embed.add_field(name="Tác giả", value=track.author)
        embed.add_field(name="Thời lượng", value=track.format_duration())
        await interaction.followup.send(embed=embed, ephemeral=True)

        if not vc.is_playing() and not vc.is_paused() and not player.current:
            next_track = player.queue.pop(0)
            await music_cog.play_track(interaction.guild, vc, next_track)

        await music_cog._send_ui(interaction)

    async def _handle_album(self, interaction: discord.Interaction, vc, music_cog, album_id: str):
        """Phát album Spotify"""
        loop = asyncio.get_running_loop()
        def _fetch():
            album = self.sp.album(album_id)
            items = album.get('tracks', {}).get('items', [])
            # album tracks không có album.images nên lấy từ album
            images = album.get('images', [])
            thumb = images[0]['url'] if images else None
            metas = []
            for item in items:
                if not item:
                    continue
                m = _spotify_track_to_meta(item)
                if not m['thumbnail']:
                    m['thumbnail'] = thumb
                metas.append(m)
            return album.get('name', 'Album'), len(items), thumb, metas

        al_name, al_count, al_thumb, metas = await loop.run_in_executor(None, _fetch)

        embed = discord.Embed(
            title="✅ Đã thêm album vào hàng chờ",
            description=f"**{al_name}**",
            color=discord.Color.green(),
        )
        if al_thumb:
            embed.set_thumbnail(url=al_thumb)
        embed.add_field(name="Số bài", value=str(al_count))
        embed.set_footer(text="Đang tìm kiếm trên YouTube...")
        await interaction.followup.send(embed=embed, ephemeral=True)

        # Resolve bài đầu tiên ngay, load background
        first_track = await self._resolve_youtube(metas[0])
        player = music_cog.get_player(interaction.guild.id)

        if not vc.is_playing() and not vc.is_paused() and not player.current:
            await music_cog.play_track(interaction.guild, vc, first_track)
        else:
            player.queue.append(first_track)

        await music_cog._send_ui(interaction)
        asyncio.create_task(self._load_metas_background(interaction.guild, music_cog, metas[1:]))

    async def _handle_playlist(self, interaction: discord.Interaction, vc, music_cog, playlist_id: str):
        """Phát playlist Spotify"""
        loop = asyncio.get_running_loop()
        def _fetch():
            logger.debug(f"[spotify._handle_playlist] fetching playlist: {playlist_id}")
            pl = self.sp.playlist(playlist_id)
            logger.debug(f"[spotify._handle_playlist] fetched: {pl.get('name', '?')}")
            items = pl.get('tracks', {}).get('items', [])
            images = pl.get('images', [])
            thumb = images[0]['url'] if images else None
            metas = []
            for item in items:
                track = item.get('track')
                if not track:
                    continue
                metas.append(_spotify_track_to_meta(track))
            return pl.get('name', 'Playlist'), len(metas), thumb, metas

        try:
            pl_name, pl_count, pl_thumb, metas = await asyncio.wait_for(
                loop.run_in_executor(None, _fetch), timeout=15
            )
        except asyncio.TimeoutError:
            logger.error(f"[spotify._handle_playlist] timeout fetching playlist")
            await interaction.followup.send("❌ Timeout khi tải playlist Spotify. Kiểm tra API credentials.", ephemeral=True)
            return
        except Exception as e:
            logger.error(f"[spotify._handle_playlist] error: {e}")
            await interaction.followup.send(f"❌ Lỗi khi tải playlist: `{e}`", ephemeral=True)
            return

        if not metas:
            await interaction.followup.send("❌ Playlist trống hoặc không thể tải.", ephemeral=True)
            return

        embed = discord.Embed(
            title="✅ Đã thêm playlist vào hàng chờ",
            description=f"**{pl_name}**",
            color=discord.Color.green(),
        )
        if pl_thumb:
            embed.set_thumbnail(url=pl_thumb)
        embed.add_field(name="Số bài", value=str(pl_count))
        embed.set_footer(text="Đang tìm kiếm trên YouTube...")
        await interaction.followup.send(embed=embed, ephemeral=True)

        first_track = await self._resolve_youtube(metas[0])
        player = music_cog.get_player(interaction.guild.id)

        if not vc.is_playing() and not vc.is_paused() and not player.current:
            await music_cog.play_track(interaction.guild, vc, first_track)
        else:
            player.queue.append(first_track)

        await music_cog._send_ui(interaction)
        asyncio.create_task(self._load_metas_background(interaction.guild, music_cog, metas[1:]))

    # ─── Helpers ─────────────────────────────────────────────────────────────

    async def _resolve_youtube(self, meta: dict) -> Track:
        """Tìm bài trên YouTube từ metadata Spotify, trả về Track với stream_url rỗng (fetch khi play)"""
        loop = asyncio.get_running_loop()
        def _search_yt():
            logger.debug(f"[spotify._resolve_youtube] searching: {meta['query']}")
            with yt_dlp.YoutubeDL(YDL_OPTS_SEARCH) as ydl:
                data = ydl.extract_info(f"ytsearch1:{meta['query']}", download=False)
                entries = data.get('entries', [data])
                e = entries[0] if entries else None
                if not e:
                    logger.warning(f"[spotify._resolve_youtube] no result for: {meta['query']}")
                    return None
                yt_url = e.get('webpage_url') or e.get('url', '')
                logger.debug(f"[spotify._resolve_youtube] found: {yt_url}")
                return Track(
                    title=meta['title'],
                    author=meta['author'],
                    url=yt_url,
                    stream_url='',
                    thumbnail=meta['thumbnail'] or e.get('thumbnail'),
                    duration=meta['duration'] or e.get('duration', 0),
                )
        return await loop.run_in_executor(None, _search_yt)

    async def _load_metas_background(self, guild: discord.Guild, music_cog, metas: list[dict]):
        """Load các bài còn lại trong background"""
        player = music_cog.get_player(guild.id)
        logger.debug(f"[spotify._load_metas_background] loading {len(metas)} tracks")
        for i, meta in enumerate(metas):
            try:
                track = await self._resolve_youtube(meta)
                if track:
                    player.queue.append(track)
                    logger.debug(f"[spotify._load_metas_background] added {i+1}/{len(metas)}: {track.title}")
            except Exception as e:
                logger.error(f"[spotify._load_metas_background error] {meta.get('title', '?')}: {e}")
        logger.debug(f"[spotify._load_metas_background] done, queue={len(player.queue)}")
        await music_cog._update_ui(guild)


async def setup(bot: commands.Bot):
    await bot.add_cog(SpotifyCog(bot))
