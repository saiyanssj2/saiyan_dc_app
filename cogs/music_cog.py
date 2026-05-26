import asyncio
import random
import discord
import yt_dlp
from discord import app_commands
from discord.ext import commands

YDL_OPTS = {
    'format': 'bestaudio/best',
    'noplaylist': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
}

FFMPEG_OPTS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}


class Track:
    def __init__(self, title: str, url: str, stream_url: str, thumbnail: str = None, duration: int = 0):
        self.title = title
        self.url = url
        self.stream_url = stream_url
        self.thumbnail = thumbnail
        self.duration = duration


class MusicPlayer:
    """Quản lý state nhạc cho mỗi guild"""
    def __init__(self):
        self.queue: list[Track] = []
        self.history: list[str] = []
        self.current: Track | None = None
        self.loop_mode = 0  # 0=off, 1=one, 2=all
        self.is_shuffled = False


class MusicControlView(discord.ui.View):
    def __init__(self, cog: 'Music', guild_id: int):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild_id = guild_id

    def get_player(self) -> MusicPlayer:
        return self.cog.players.get(self.guild_id)

    def build_embed(self) -> discord.Embed:
        player = self.get_player()
        if not player or not player.current:
            return discord.Embed(title="🎶 Hàng chờ trống", color=discord.Color.red())

        embed = discord.Embed(color=discord.Color.green())
        embed.title = f"🎵 Đang phát: {player.current.title}"
        if player.current.thumbnail:
            embed.set_thumbnail(url=player.current.thumbnail)

        # Queue
        upcoming = [f"{i+1}. {t.title}" for i, t in enumerate(player.queue[:5])]
        queue_str = "\n".join(upcoming) if upcoming else "Không có bài nào tiếp theo"

        # History
        history_str = "\n".join(player.history[-3:]) if player.history else "Chưa có lịch sử"

        embed.add_field(name="⏮️ Đã phát", value=history_str, inline=False)
        embed.add_field(name="⏭️ Sắp phát", value=queue_str, inline=False)

        # Update button states
        loop_labels = {0: "🔁 Loop: Off", 1: "🔂 Loop: One", 2: "🔁 Loop: All"}
        loop_styles = {0: discord.ButtonStyle.gray, 1: discord.ButtonStyle.green, 2: discord.ButtonStyle.blurple}
        self.loop_button.label = loop_labels[player.loop_mode]
        self.loop_button.style = loop_styles[player.loop_mode]
        self.shuffle_button.style = discord.ButtonStyle.green if player.is_shuffled else discord.ButtonStyle.gray

        vc = self.cog.bot.get_guild(self.guild_id).voice_client
        if vc:
            self.pause_resume.label = "▶️" if vc.is_paused() else "⏸️"

        return embed

    @discord.ui.button(label="⏮️", style=discord.ButtonStyle.gray)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self.get_player()
        if not player or not player.history:
            return await interaction.response.send_message("❌ Không có bài trước đó!", ephemeral=True)

        prev_title = player.history.pop()
        track = await self.cog.search_track(prev_title)
        if track:
            vc = interaction.guild.voice_client
            if vc:
                player.current = track
                vc.stop()
                await asyncio.sleep(0.3)
                vc.play(discord.FFmpegPCMAudio(track.stream_url, **FFMPEG_OPTS),
                        after=lambda e: self.cog.play_next(interaction.guild))
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="⏸️", style=discord.ButtonStyle.blurple)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc:
            if vc.is_paused():
                vc.resume()
            else:
                vc.pause()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="⏭️", style=discord.ButtonStyle.gray)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.stop()
        await asyncio.sleep(0.5)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="🔀 Shuffle", style=discord.ButtonStyle.gray)
    async def shuffle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self.get_player()
        if player:
            player.is_shuffled = not player.is_shuffled
            if player.is_shuffled:
                random.shuffle(player.queue)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="🔁 Loop: Off", style=discord.ButtonStyle.gray)
    async def loop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self.get_player()
        if player:
            player.loop_mode = (player.loop_mode + 1) % 3
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="⏹️", style=discord.ButtonStyle.red)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        player = self.get_player()
        if player:
            player.queue.clear()
            player.current = None
        vc = interaction.guild.voice_client
        if vc:
            vc.stop()
            await vc.disconnect()
        embed = discord.Embed(title="⏹️ Đã dừng nhạc", description="Bot đã ngắt kết nối.", color=discord.Color.red())
        await interaction.edit_original_response(embed=embed, view=None)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players: dict[int, MusicPlayer] = {}

    def get_player(self, guild_id: int) -> MusicPlayer:
        if guild_id not in self.players:
            self.players[guild_id] = MusicPlayer()
        return self.players[guild_id]

    async def search_track(self, query: str) -> Track | None:
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            data = await loop.run_in_executor(None, lambda: ydl.extract_info(query, download=False))

        if not data:
            return None

        # Nếu là playlist, lấy bài đầu
        if 'entries' in data:
            entries = list(data['entries'])
            if not entries:
                return None
            data = entries[0]

        return Track(
            title=data.get('title', 'Unknown'),
            url=data.get('webpage_url', ''),
            stream_url=data.get('url', ''),
            thumbnail=data.get('thumbnail'),
            duration=data.get('duration', 0),
        )

    async def search_tracks(self, query: str) -> list[Track]:
        """Tìm nhiều bài (playlist support)"""
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            data = await loop.run_in_executor(None, lambda: ydl.extract_info(query, download=False))

        if not data:
            return []

        tracks = []
        if 'entries' in data:
            for entry in data['entries']:
                if entry:
                    tracks.append(Track(
                        title=entry.get('title', 'Unknown'),
                        url=entry.get('webpage_url', ''),
                        stream_url=entry.get('url', ''),
                        thumbnail=entry.get('thumbnail'),
                        duration=entry.get('duration', 0),
                    ))
        else:
            tracks.append(Track(
                title=data.get('title', 'Unknown'),
                url=data.get('webpage_url', ''),
                stream_url=data.get('url', ''),
                thumbnail=data.get('thumbnail'),
                duration=data.get('duration', 0),
            ))
        return tracks

    def play_next(self, guild: discord.Guild):
        """Callback khi bài hát kết thúc - phát bài tiếp theo"""
        player = self.get_player(guild.id)
        vc = guild.voice_client

        if not vc:
            return

        # Lưu history
        if player.current:
            player.history.append(player.current.title)
            if len(player.history) > 10:
                player.history.pop(0)

        # Loop one
        if player.loop_mode == 1 and player.current:
            vc.play(discord.FFmpegPCMAudio(player.current.stream_url, **FFMPEG_OPTS),
                    after=lambda e: self.play_next(guild))
            return

        # Loop all - đưa bài vừa phát về cuối queue
        if player.loop_mode == 2 and player.current:
            player.queue.append(player.current)

        # Phát bài tiếp
        if player.queue:
            next_track = player.queue.pop(0)
            player.current = next_track
            vc.play(discord.FFmpegPCMAudio(next_track.stream_url, **FFMPEG_OPTS),
                    after=lambda e: self.play_next(guild))
        else:
            player.current = None

    @app_commands.command(name="play", description="Phát nhạc từ YouTube hoặc URL")
    async def play(self, interaction: discord.Interaction, search: str):
        await interaction.response.defer()

        if not interaction.user.voice:
            return await interaction.followup.send("❌ Bạn cần vào Voice Channel trước!")

        vc = interaction.guild.voice_client
        if not vc:
            vc = await interaction.user.voice.channel.connect()

        player = self.get_player(interaction.guild.id)
        tracks = await self.search_tracks(search)

        if not tracks:
            return await interaction.followup.send("❌ Không tìm thấy kết quả!")

        # Thêm vào queue
        for t in tracks:
            player.queue.append(t)

        display_name = tracks[0].title if len(tracks) == 1 else f"Playlist ({len(tracks)} bài)"

        # Nếu chưa phát thì bắt đầu
        if not vc.is_playing() and not vc.is_paused():
            next_track = player.queue.pop(0)
            player.current = next_track
            vc.play(discord.FFmpegPCMAudio(next_track.stream_url, **FFMPEG_OPTS),
                    after=lambda e: self.play_next(interaction.guild))

        embed = discord.Embed(
            title="🎶 Đã thêm vào hàng chờ",
            description=f"**{display_name}**",
            color=discord.Color.green()
        )
        if tracks[0].thumbnail:
            embed.set_thumbnail(url=tracks[0].thumbnail)

        view = MusicControlView(self, interaction.guild.id)
        await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(name="skip", description="Bỏ qua bài hiện tại")
    async def skip(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.stop()
            await interaction.response.send_message("⏭️ Đã skip!")
        else:
            await interaction.response.send_message("❌ Không có bài nào đang phát!", ephemeral=True)

    @app_commands.command(name="queue", description="Xem hàng chờ")
    async def queue(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild.id)
        if not player.current and not player.queue:
            return await interaction.response.send_message("❌ Hàng chờ trống!", ephemeral=True)

        embed = discord.Embed(title="📋 Hàng chờ", color=discord.Color.blurple())
        if player.current:
            embed.add_field(name="🎵 Đang phát", value=player.current.title, inline=False)

        if player.queue:
            queue_list = "\n".join([f"{i+1}. {t.title}" for i, t in enumerate(player.queue[:10])])
            if len(player.queue) > 10:
                queue_list += f"\n... và {len(player.queue) - 10} bài nữa"
            embed.add_field(name="⏭️ Tiếp theo", value=queue_list, inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="stop", description="Dừng nhạc và ngắt kết nối")
    async def stop(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild.id)
        player.queue.clear()
        player.current = None
        vc = interaction.guild.voice_client
        if vc:
            vc.stop()
            await vc.disconnect()
        await interaction.response.send_message("⏹️ Đã dừng nhạc!")


async def setup(bot):
    await bot.add_cog(Music(bot))
