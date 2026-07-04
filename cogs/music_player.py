import asyncio
import time
import discord
import yt_dlp

from .logger import logger
from .music_core import (
    Track, MusicPlayer,
    YDL_OPTS_SEARCH, YDL_OPTS_SINGLE,
    make_ffmpeg_opts,
)
from .music_ui import build_embed
from .music_controls import MusicControlView


class MusicPlayerMixin:
    """Mixin chứa play logic, seek, queue management - dùng chung cho MusicCog"""

    # ─── yt-dlp helpers ──────────────────────────────────────────────────────

    async def search_tracks(self, query: str) -> list[Track]:
        loop = asyncio.get_running_loop()
        def _search():
            logger.info(f"[search_tracks] start yt-dlp search: {query}")
            try:
                with yt_dlp.YoutubeDL(YDL_OPTS_SEARCH) as ydl:
                    data = ydl.extract_info(query, download=False)
                    logger.info(f"[search_tracks] yt-dlp done, entries={len(data.get('entries', []))}")
                    entries = data.get('entries', [data])
                    results = []
                    for e in entries[:10]:
                        if not e:
                            continue
                        results.append(Track(
                            title=e.get('title', 'Unknown'),
                            author=e.get('uploader') or e.get('channel', 'Unknown'),
                            url=e.get('webpage_url') or e.get('url', ''),
                            stream_url='',
                            thumbnail=e.get('thumbnail'),
                            duration=e.get('duration', 0),
                        ))
                    return results
            except Exception as e:
                logger.error(f"[search_tracks error] {e}")
                return []
        return await loop.run_in_executor(None, _search)

    async def fetch_stream(self, track: Track) -> Track:
        loop = asyncio.get_running_loop()
        def _fetch():
            try:
                with yt_dlp.YoutubeDL(YDL_OPTS_SINGLE) as ydl:
                    data = ydl.extract_info(track.url, download=False)
                    track.stream_url = data.get('url', '')
                    logger.info(f"[fetch_stream] {track.title} → {track.stream_url[:60]}...")
                    return track
            except Exception as e:
                logger.error(f"[fetch_stream error] {e}")
                raise
        return await loop.run_in_executor(None, _fetch)

    # ─── Play logic ──────────────────────────────────────────────────────────

    async def play_track(self, guild: discord.Guild, voice_client: discord.VoiceClient, track: Track):
        player = self.get_player(guild.id)
        logger.info(f"[play_track] {track.title} | stream_url={'set' if track.stream_url else 'empty'}")
        logger.debug(f"[play_track] vc.is_connected={voice_client.is_connected()} | vc.is_playing={voice_client.is_playing()} | vc.channel={voice_client.channel}")

        if not track.stream_url:
            track = await self.fetch_stream(track)

        if not track.stream_url:
            logger.warning(f"[play_track] Không lấy được stream_url, bỏ qua bài này")
            await self._on_track_end(guild, voice_client)
            return

        # Luôn fetch stream mới để tránh URL hết hạn
        try:
            track = await self.fetch_stream(track)
        except Exception as e:
            logger.warning(f"[play_track] fetch_stream failed: {e}, dùng stream_url cũ")

        player.current = track
        player.seek_offset = 0.0
        player.start_time = time.time()
        player.pause_time = 0.0
        player.stopped = False

        is_local = not track.stream_url.startswith('http')
        logger.debug(f"[play_track] starting FFmpeg | is_local={is_local} | stream_url={track.stream_url[:80]}...")
        source = discord.FFmpegPCMAudio(track.stream_url, **make_ffmpeg_opts(is_local=is_local))
        source = discord.PCMVolumeTransformer(source, volume=0.0 if player.muted else player.volume)

        def after_play(error):
            if error:
                logger.error(f"[after_play error] {error}")
                logger.error(f"[after_play] track={track.title} | stream_url={track.stream_url[:60] if track.stream_url else 'empty'}")
            else:
                logger.info(f"[after_play] track ended: {track.title}")
            asyncio.run_coroutine_threadsafe(self._on_track_end(guild, voice_client), self.bot.loop)

        if voice_client.is_playing() or voice_client.is_paused():
            player._skip_next_end += 1
            voice_client.stop()

        voice_client.play(source, after=after_play)
        logger.info(f"[play_track] playing: {track.title} | is_playing={voice_client.is_playing()}")

    async def _on_track_end(self, guild: discord.Guild, voice_client: discord.VoiceClient):
        player = self.get_player(guild.id)
        logger.info(f"[_on_track_end] skip_next={player._skip_next_end} | current={player.current.title if player.current else 'none'} | queue={len(player.queue)}")

        if player._skip_next_end > 0:
            player._skip_next_end -= 1
            return

        if player.stopped:
            player.stopped = False
            return

        if player.loop_mode == 1:
            if player.current:
                await self.play_track(guild, voice_client, player.current)
                await self._update_ui(guild)
            return

        if player.current:
            player.history.append(player.current)
            player.current = None

        if player.loop_mode == 2 and not player.queue:
            player.queue = list(player.history)
            player.history = []

        if player.queue:
            next_track = player.queue.pop(0)
            await self.play_track(guild, voice_client, next_track)
            await self._update_ui(guild)
        else:
            player.footer_msg = '⏹️ Hết bài hát trong hàng chờ.'
            await self._update_ui(guild)
            self._schedule_idle_disconnect(guild, voice_client)

    def _schedule_idle_disconnect(self, guild: discord.Guild, voice_client: discord.VoiceClient):
        player = self.get_player(guild.id)
        if player.idle_task:
            player.idle_task.cancel()

        async def _disconnect_after():
            await asyncio.sleep(300)
            if voice_client.is_connected() and not voice_client.is_playing():
                await voice_client.disconnect()
                self.remove_player(guild.id)

        player.idle_task = asyncio.create_task(_disconnect_after())

    async def _seek(self, guild: discord.Guild, voice_client: discord.VoiceClient, seconds: float):
        player = self.get_player(guild.id)
        if not player.current:
            logger.warning(f"[seek] Không có bài đang phát")
            return

        elapsed = player.elapsed()
        new_offset = max(0.0, elapsed + seconds)
        logger.info(f"[seek] elapsed={elapsed:.1f}s | offset={seconds:+}s | new_offset={new_offset:.1f}s | duration={player.current.duration}")

        if player.current.duration and new_offset >= player.current.duration:
            logger.info(f"[seek] Vượt quá duration, bỏ qua")
            return

        if not player.current.stream_url:
            player.current = await self.fetch_stream(player.current)

        player.seek_offset = new_offset
        player.start_time = time.time()
        player.pause_time = 0.0

        is_local = not player.current.stream_url.startswith('http')
        source = discord.FFmpegPCMAudio(player.current.stream_url, **make_ffmpeg_opts(seek=new_offset, is_local=is_local))
        source = discord.PCMVolumeTransformer(source, volume=0.0 if player.muted else player.volume)

        def after_seek(error):
            if error:
                logger.error(f"[seek error] {error}")
            asyncio.run_coroutine_threadsafe(self._on_track_end(guild, voice_client), self.bot.loop)

        player._skip_next_end += 1
        voice_client.stop()
        voice_client.play(source, after=after_seek)

    # ─── UI helpers ──────────────────────────────────────────────────────────

    async def _update_ui(self, guild: discord.Guild, user_id: int = None):
        player = self.get_player(guild.id)
        if not player.control_message:
            return
        try:
            embed = build_embed(player)
            view = MusicControlView(self, guild, user_id=user_id)
            await player.control_message.edit(embed=embed, view=view)
            # Xóa footer sau 5s
            if player.footer_msg:
                async def _clear_footer():
                    await asyncio.sleep(5)
                    player.footer_msg = ''
                    try:
                        embed2 = build_embed(player)
                        await player.control_message.edit(embed=embed2, view=view)
                    except Exception:
                        pass
                asyncio.create_task(_clear_footer())
        except Exception as e:
            logger.error(f"[_update_ui error] {e}")

    async def _send_ui(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild.id)
        if player.control_message:
            try:
                await player.control_message.delete()
            except Exception:
                pass
        embed = build_embed(player)
        view = MusicControlView(self, interaction.guild, user_id=interaction.user.id)
        msg = await interaction.channel.send(embed=embed, view=view)
        player.control_message = msg
