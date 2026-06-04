import discord
from .music_core import Track, MusicPlayer, fmt_time, get_user_playlists, playlist_to_tracks


# ─── Embed builder ───────────────────────────────────────────────────────────
def build_embed(player: MusicPlayer) -> discord.Embed:
    if player.current:
        embed = discord.Embed(
            title="🎵 Đang phát",
            description=f"**[{player.current.title}]({player.current.url})**\n{player.current.author}",
            color=discord.Color.blurple(),
        )
        if player.current.thumbnail:
            embed.set_thumbnail(url=player.current.thumbnail)

        elapsed = player.elapsed()
        dur = player.current.duration
        if dur:
            pct = min(elapsed / dur, 1.0)
            filled = int(pct * 20)
            bar = '▬' * filled + '🔘' + '▬' * (20 - filled)
            embed.add_field(
                name="⏱️ Tiến độ",
                value=f"`{fmt_time(elapsed)}` {bar} `{player.current.format_duration()}`",
                inline=False,
            )
    else:
        embed = discord.Embed(
            title="🎵 Saiyan Music",
            description="Không có bài nào đang phát.",
            color=discord.Color.greyple(),
        )

    if player.history:
        recent = player.history[-3:][::-1]
        val = '\n'.join(f"`{i+1}.` [{t.title[:55]}]({t.url})" for i, t in enumerate(recent))
        embed.add_field(name="⏮️ Đã phát", value=val, inline=False)

    if player.queue:
        upcoming = player.queue[:3]
        val = '\n'.join(f"`{i+1}.` [{t.title[:55]}]({t.url})" for i, t in enumerate(upcoming))
        if len(player.queue) > 3:
            val += f"\n*... và {len(player.queue) - 3} bài khác*"
        embed.add_field(name="📋 Hàng chờ", value=val, inline=False)

    vol_str = "🔇 Muted" if player.muted else f"🔊 {int(player.volume * 100)}%"
    loop_str = ["🔁 Off", "🔂 Loop 1", "🔁 Loop All"][player.loop_mode]
    embed.add_field(name="Volume", value=vol_str, inline=True)
    embed.add_field(name="Loop", value=loop_str, inline=True)
    embed.add_field(name="Shuffle", value="🔀 On" if player.is_shuffled else "➡️ Off", inline=True)

    if player.footer_msg:
        embed.set_footer(text=player.footer_msg)

    return embed


# ─── Select Track View ───────────────────────────────────────────────────────
class TrackSelect(discord.ui.Select):
    def __init__(self, tracks: list[Track]):
        options = [
            discord.SelectOption(
                label=f"{i+1}. {t.title[:80]}",
                description=f"{t.author} • {t.format_duration()}"[:100],
                value=str(i),
            )
            for i, t in enumerate(tracks)
        ]
        super().__init__(
            placeholder="Chọn bài hát...",
            min_values=1,
            max_values=len(tracks),
            options=options,
        )
        self.tracks = tracks

    async def callback(self, interaction: discord.Interaction):
        await self.view.on_select(interaction, [self.tracks[int(i)] for i in self.values])


class SelectTrackView(discord.ui.View):
    def __init__(self, cog, tracks: list[Track], guild: discord.Guild,
                 voice_client: discord.VoiceClient, add_to_front: bool = False):
        super().__init__(timeout=60)
        self.cog = cog
        self.guild = guild
        self.voice_client = voice_client
        self.add_to_front = add_to_front
        self.message: discord.Message | None = None
        self.add_item(TrackSelect(tracks))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(content="⏰ Hết thời gian chọn bài.", view=self)
        except Exception:
            pass

    async def on_select(self, interaction: discord.Interaction, selected: list[Track]):
        await interaction.response.defer(ephemeral=True)
        self.stop()

        player = self.cog.get_player(self.guild.id)

        if self.add_to_front:
            for track in reversed(selected):
                player.queue.insert(0, track)
        else:
            player.queue.extend(selected)

        if len(selected) == 1:
            t = selected[0]
            embed = discord.Embed(
                title="✅ Đã thêm vào hàng chờ",
                description=f"[{t.title}]({t.url})",
                color=discord.Color.green(),
            )
            if t.thumbnail:
                embed.set_thumbnail(url=t.thumbnail)
            embed.add_field(name="Tác giả", value=t.author)
            embed.add_field(name="Thời lượng", value=t.format_duration())
        else:
            embed = discord.Embed(
                title=f"✅ Đã thêm {len(selected)} bài vào hàng chờ",
                color=discord.Color.green(),
            )
            for t in selected[:5]:
                embed.add_field(name=t.title[:50], value=f"{t.author} • {t.format_duration()}", inline=False)
            if len(selected) > 5:
                embed.set_footer(text=f"... và {len(selected) - 5} bài khác")

        await interaction.followup.send(embed=embed, ephemeral=True)
        print(f"[on_select] sent followup embed")

        try:
            await self.message.delete()
            print(f"[on_select] deleted message")
        except Exception as e:
            print(f"[on_select] delete error: {e}")

        # Gửi UI trước, play sau để tránh timeout interaction
        await self.cog._send_ui(interaction)
        print(f"[on_select] sent UI")

        if not self.voice_client.is_playing() and not self.voice_client.is_paused() and not player.current:
            next_track = player.queue.pop(0)
            print(f"[on_select] calling play_track: {next_track.title}")
            await self.cog.play_track(self.guild, self.voice_client, next_track)
            print(f"[on_select] play_track done")
            await self.cog._update_ui(self.guild)


# ─── Playlist Select View ─────────────────────────────────────────────────────
class PlaylistSelectView(discord.ui.View):
    def __init__(self, cog, options: list[discord.SelectOption], interaction: discord.Interaction):
        super().__init__(timeout=60)
        self.cog = cog
        self.interaction = interaction
        select = discord.ui.Select(
            placeholder="Chọn playlist muốn phát...",
            options=options,
        )
        select.callback = self._on_select
        self.add_item(select)

    async def _on_select(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        name = interaction.data['values'][0]

        playlists = get_user_playlists(interaction.user.id)
        if name not in playlists:
            await interaction.followup.send("❌ Playlist không tồn tại.", ephemeral=True)
            return

        tracks = playlist_to_tracks(playlists[name])
        if not tracks:
            await interaction.followup.send("❌ Playlist trống.", ephemeral=True)
            return

        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.followup.send("❌ Bạn cần vào voice channel trước!", ephemeral=True)
            return

        vc = interaction.guild.voice_client
        if not vc:
            vc = await interaction.user.voice.channel.connect()
        elif vc.channel != interaction.user.voice.channel:
            await vc.move_to(interaction.user.voice.channel)

        player = self.cog.get_player(interaction.guild.id)
        player.queue.extend(tracks)

        display = name if name != '__current__' else '🔄 Current Session'
        embed = discord.Embed(
            title="✅ Đã thêm playlist vào hàng chờ",
            description=f"**{display}**",
            color=discord.Color.green(),
        )
        embed.add_field(name="Số bài", value=str(len(tracks)))
        await interaction.followup.send(embed=embed, ephemeral=True)

        if not vc.is_playing() and not vc.is_paused() and not player.current:
            next_track = player.queue.pop(0)
            await self.cog.play_track(interaction.guild, vc, next_track)

        await self.cog._send_ui(interaction)
        self.stop()
