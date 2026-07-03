import asyncio
import discord
import yt_dlp
from discord import app_commands
from discord.ext import commands

from .music_core import (
    Track, MusicPlayer,
    YDL_OPTS_URL, YDL_OPTS_SINGLE,
    get_user_playlists, playlist_to_tracks,
    load_favorites,
)
from .music_ui import build_embed, SelectTrackView, PlaylistSelectView
from .music_player import MusicPlayerMixin


class MusicCog(MusicPlayerMixin, commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.players: dict[int, MusicPlayer] = {}

    def get_player(self, guild_id: int) -> MusicPlayer:
        if guild_id not in self.players:
            self.players[guild_id] = MusicPlayer()
        return self.players[guild_id]

    def remove_player(self, guild_id: int):
        self.players.pop(guild_id, None)

    # ─── Slash Commands ──────────────────────────────────────────────────────

    @app_commands.command(name="play", description="Phát nhạc từ YouTube (từ khóa hoặc URL)")
    @app_commands.describe(query="Từ khóa tìm kiếm hoặc URL YouTube")
    async def play(self, interaction: discord.Interaction, query: str):
        print(f"[play] query={query} | user={interaction.user}")
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ Bạn cần vào voice channel trước!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        vc = interaction.guild.voice_client
        if not vc:
            vc = await interaction.user.voice.channel.connect()
        elif vc.channel != interaction.user.voice.channel:
            await vc.move_to(interaction.user.voice.channel)
        is_url = query.startswith("http://") or query.startswith("https://")
        if is_url:
            await self._handle_url(interaction, vc, query, add_to_front=False)
        else:
            await self._handle_search(interaction, vc, query, add_to_front=False)

    @app_commands.command(name="play_next", description="Thêm bài vào đầu hàng chờ")
    @app_commands.describe(query="Từ khóa tìm kiếm hoặc URL YouTube")
    async def play_next(self, interaction: discord.Interaction, query: str):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ Bạn cần vào voice channel trước!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        vc = interaction.guild.voice_client
        if not vc:
            vc = await interaction.user.voice.channel.connect()
        elif vc.channel != interaction.user.voice.channel:
            await vc.move_to(interaction.user.voice.channel)
        is_url = query.startswith("http://") or query.startswith("https://")
        if is_url:
            await self._handle_url(interaction, vc, query, add_to_front=True)
        else:
            await self._handle_search(interaction, vc, query, add_to_front=True)

    @app_commands.command(name="queue", description="Xem hàng chờ hiện tại")
    async def queue(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild.id)
        if not player.current and not player.queue:
            await interaction.response.send_message("📋 Hàng chờ trống.", ephemeral=True)
            return
        embed = build_embed(player)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="skip", description="Bỏ qua bài hiện tại")
    async def skip(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if not vc or (not vc.is_playing() and not vc.is_paused()):
            await interaction.response.send_message("❌ Không có bài nào đang phát.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        player = self.get_player(interaction.guild.id)
        player.footer_msg = ''
        prev_loop = player.loop_mode
        if player.loop_mode == 1:
            player.loop_mode = 0
        vc.stop()
        player.loop_mode = prev_loop
        await interaction.followup.send("⏭️ Đã skip.", ephemeral=True)

    @app_commands.command(name="stop", description="Dừng nhạc, giữ bot trong channel")
    async def stop(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if not vc:
            await interaction.response.send_message("❌ Bot chưa ở trong voice channel.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        player = self.get_player(interaction.guild.id)
        if player.current:
            player.history.append(player.current)
            player.current = None
        player.history.extend(player.queue)
        player.queue.clear()
        player.footer_msg = '⏹️ Đã dừng phát nhạc.'
        if vc.is_playing() or vc.is_paused():
            player._skip_next_end += 1
            vc.stop()
        await self._update_ui(interaction.guild)
        await interaction.followup.send("⏹️ Đã dừng.", ephemeral=True)

    @app_commands.command(name="disconnect", description="Ngắt kết nối và xóa hàng chờ")
    async def disconnect(self, interaction: discord.Interaction):
        await self._quit(interaction)

    @app_commands.command(name="quit", description="Ngắt kết nối và xóa hàng chờ")
    async def quit(self, interaction: discord.Interaction):
        await self._quit(interaction)

    @app_commands.command(name="playlist", description="Xem và thêm playlist đã lưu vào queue")
    async def playlist(self, interaction: discord.Interaction):
        playlists = get_user_playlists(interaction.user.id)
        if not playlists:
            await interaction.response.send_message("📝 Bạn chưa lưu playlist nào.", ephemeral=True)
            return
        embed = discord.Embed(title="📜 Playlist đã lưu", color=discord.Color.blurple())
        options = []
        for name, data in playlists.items():
            tracks = playlist_to_tracks(data)
            display = name if name != '__current__' else '🔄 Current Session'
            embed.add_field(name=display, value=f"{len(tracks)} bài", inline=False)
            options.append(discord.SelectOption(label=display, value=name))
        view = PlaylistSelectView(self, options, interaction)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="favorite", description="Xem và thêm bài yêu thích vào queue")
    async def favorite(self, interaction: discord.Interaction):
        favs = load_favorites()
        user_favs = favs.get(str(interaction.user.id), [])
        if not user_favs:
            await interaction.response.send_message("❤️ Bạn chưa có bài yêu thích nào.", ephemeral=True)
            return
        tracks = [Track(
            title=f['title'], author=f['author'], url=f['url'],
            stream_url=f.get('stream_url', ''), thumbnail=f.get('thumbnail'),
            duration=f.get('duration', 0),
        ) for f in user_favs]
        embed = discord.Embed(title="❤️ Bài hát yêu thích", color=discord.Color.red())
        for i, t in enumerate(tracks[:10]):
            embed.add_field(name=f"{i+1}. {t.title[:50]}", value=f"{t.author} • {t.format_duration()}", inline=False)
        if len(tracks) > 10:
            embed.set_footer(text=f"... và {len(tracks) - 10} bài khác")
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        vc = interaction.guild.voice_client
        if not vc:
            vc = await interaction.user.voice.channel.connect()
        elif vc.channel != interaction.user.voice.channel:
            await vc.move_to(interaction.user.voice.channel)
        view = SelectTrackView(self, tracks, interaction.guild, vc, add_to_front=False)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()

    async def _quit(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if not vc:
            await interaction.response.send_message("❌ Bot chưa ở trong voice channel.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        self.remove_player(interaction.guild.id)
        await vc.disconnect()
        await interaction.followup.send("👋 Đã ngắt kết nối.", ephemeral=True)

    # ─── URL / Search handlers ────────────────────────────────────────────────

    async def _handle_search(self, interaction: discord.Interaction, vc: discord.VoiceClient,
                              query: str, add_to_front: bool):
        print(f"[_handle_search] query={query}")
        tracks = await self.search_tracks(query)
        print(f"[_handle_search] found {len(tracks)} tracks")
        if not tracks:
            await interaction.followup.send("❌ Không tìm thấy kết quả.", ephemeral=True)
            return
        view = SelectTrackView(self, tracks, interaction.guild, vc, add_to_front=add_to_front)
        msg = await interaction.followup.send(
            content="🔍 Chọn bài hát bạn muốn phát:",
            view=view, ephemeral=True, wait=True,
        )
        view.message = msg

    async def _handle_url(self, interaction: discord.Interaction, vc: discord.VoiceClient,
                           url: str, add_to_front: bool):
        player = self.get_player(interaction.guild.id)
        if "playlist" in url or "list=" in url:
            await self._handle_playlist(interaction, vc, url, add_to_front)
            return

        loop = asyncio.get_running_loop()
        def _fetch():
            with yt_dlp.YoutubeDL(YDL_OPTS_SINGLE) as ydl:
                data = ydl.extract_info(url, download=False)
                return Track.from_ydl(data)
        track = await loop.run_in_executor(None, _fetch)

        if add_to_front:
            player.queue.insert(0, track)
        else:
            player.queue.append(track)

        embed = discord.Embed(
            title="✅ Đã thêm vào hàng chờ",
            description=f"[{track.title}]({track.url})",
            color=discord.Color.green(),
        )
        if track.thumbnail:
            embed.set_thumbnail(url=track.thumbnail)
        embed.add_field(name="Tác giả", value=track.author)
        embed.add_field(name="Thời lượng", value=track.format_duration())
        await interaction.followup.send(embed=embed, ephemeral=True)

        if not vc.is_playing() and not vc.is_paused() and not player.current:
            next_track = player.queue.pop(0)
            await self.play_track(interaction.guild, vc, next_track)

        await self._send_ui(interaction)

    async def _handle_playlist(self, interaction: discord.Interaction, vc: discord.VoiceClient,
                                url: str, add_to_front: bool):
        player = self.get_player(interaction.guild.id)
        loop = asyncio.get_running_loop()

        def _fetch_first():
            opts = dict(YDL_OPTS_URL)
            opts['playlistend'] = 1
            opts['ignoreerrors'] = True
            with yt_dlp.YoutubeDL(opts) as ydl:
                data = ydl.extract_info(url, download=False)
                if not data:
                    return (None, 'Playlist', 0, None)
                entries = data.get('entries', [data])
                # Lọc bỏ entry None (video unavailable)
                entries = [e for e in entries if e]
                first = entries[0] if entries else None
                return (
                    first,
                    data.get('title', 'Playlist'),
                    data.get('playlist_count') or len(entries),
                    data.get('thumbnail'),
                )

        first_entry, pl_title, pl_count, pl_thumb = await loop.run_in_executor(None, _fetch_first)

        if not first_entry:
            await interaction.followup.send("❌ Không thể tải playlist.", ephemeral=True)
            return

        first_track = Track.from_ydl(first_entry)

        embed = discord.Embed(
            title="✅ Đã thêm playlist vào hàng chờ",
            description=f"**{pl_title}**",
            color=discord.Color.green(),
        )
        if pl_thumb:
            embed.set_thumbnail(url=pl_thumb)
        embed.add_field(name="Số bài", value=str(pl_count))
        embed.set_footer(text="Đang tải các bài còn lại...")
        await interaction.followup.send(embed=embed, ephemeral=True)

        if not vc.is_playing() and not vc.is_paused() and not player.current:
            await self.play_track(interaction.guild, vc, first_track)
        else:
            if add_to_front:
                player.queue.insert(0, first_track)
            else:
                player.queue.append(first_track)

        await self._send_ui(interaction)
        asyncio.create_task(self._load_playlist_background(interaction.guild, url, add_to_front))

    async def _load_playlist_background(self, guild: discord.Guild, url: str, add_to_front: bool):
        player = self.get_player(guild.id)
        loop = asyncio.get_running_loop()

        def _fetch_all():
            opts = dict(YDL_OPTS_URL)
            opts['ignoreerrors'] = True
            opts['extract_flat'] = 'in_playlist'
            with yt_dlp.YoutubeDL(opts) as ydl:
                data = ydl.extract_info(url, download=False)
                return data.get('entries', [data])

        try:
            entries = await loop.run_in_executor(None, _fetch_all)
            added = 0
            for e in entries[1:]:
                if not e:
                    continue
                track = Track(
                    title=e.get('title', 'Unknown'),
                    author=e.get('uploader') or e.get('channel', 'Unknown'),
                    url=e.get('webpage_url') or e.get('url') or url,
                    stream_url='',  # sẽ resolve khi phát
                    thumbnail=e.get('thumbnail') or e.get('thumbnails', [{}])[0].get('url') if e.get('thumbnails') else None,
                    duration=e.get('duration', 0) or 0,
                )
                if add_to_front:
                    player.queue.insert(0, track)
                else:
                    player.queue.append(track)
                added += 1
            print(f"[_load_playlist_background] Đã thêm {added}/{len(entries)-1} bài từ playlist")
            await self._update_ui(guild)
        except Exception as e:
            print(f"[_load_playlist_background error] {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(MusicCog(bot))
