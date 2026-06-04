import random
import time
import discord
from .music_core import MusicPlayer, toggle_favorite, save_player_playlist, delete_player_playlist, get_user_playlists


class MusicControlView(discord.ui.View):
    def __init__(self, cog, guild: discord.Guild, user_id: int = None):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild = guild
        player = cog.get_player(guild.id)
        for item in self.children:
            if hasattr(item, 'custom_id') and item.custom_id == 'btn_pause_resume':
                item.emoji = '▶️' if player.is_paused else '⏸️'
            if user_id and hasattr(item, 'emoji') and str(item.emoji) in ('❤️', '🤍'):
                item.emoji = '❤️' if player.is_favorited(user_id) else '🤍'

    def _vc(self) -> discord.VoiceClient | None:
        return self.guild.voice_client

    def _player(self) -> MusicPlayer:
        return self.cog.get_player(self.guild.id)

    # Row 0: ⏮️ ⏪ ⏸️/▶️ ⏩ ⏭️
    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.secondary, row=0)
    async def btn_previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        player = self._player()
        vc = self._vc()
        if not vc:
            return
        if not player.history:
            player.footer_msg = '⏮️ Không có bài trước đó.'
            await self.cog._update_ui(self.guild)
            return
        if player.current:
            player.queue.insert(0, player.current)
            player.current = None
        prev = player.history.pop()
        player.footer_msg = ''
        await self.cog.play_track(self.guild, vc, prev)
        await self.cog._update_ui(self.guild)

    @discord.ui.button(emoji="⏪", style=discord.ButtonStyle.secondary, row=0)
    async def btn_rewind(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        vc = self._vc()
        if vc:
            await self.cog._seek(self.guild, vc, -10)
            await self.cog._update_ui(self.guild)

    @discord.ui.button(emoji="⏸️", style=discord.ButtonStyle.primary, row=0, custom_id="btn_pause_resume")
    async def btn_pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        vc = self._vc()
        player = self._player()
        if not vc:
            return
        if vc.is_playing():
            vc.pause()
            player.pause_time = time.time()
            player.is_paused = True
            button.emoji = "▶️"
            await self.cog._update_ui(self.guild)
        elif vc.is_paused():
            vc.resume()
            if player.pause_time:
                player.start_time += time.time() - player.pause_time
                player.pause_time = 0.0
            player.is_paused = False
            button.emoji = "⏸️"
            await self.cog._update_ui(self.guild)
        elif not vc.is_playing() and not vc.is_paused() and player.history:
            track = player.history.pop()
            player.is_paused = False
            await self.cog.play_track(self.guild, vc, track)
            await self.cog._update_ui(self.guild)

    @discord.ui.button(emoji="⏩", style=discord.ButtonStyle.secondary, row=0)
    async def btn_forward(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        vc = self._vc()
        if vc:
            await self.cog._seek(self.guild, vc, 10)
            await self.cog._update_ui(self.guild)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary, row=0)
    async def btn_skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        player = self._player()
        vc = self._vc()
        if not vc:
            return
        player.footer_msg = ''
        prev_loop = player.loop_mode
        if player.loop_mode == 1:
            player.loop_mode = 0
        if vc.is_playing() or vc.is_paused():
            vc.stop()
        player.loop_mode = prev_loop

    # Row 1: 🔀 🔁 ❤️/🤍 ⏹️ 🧹
    @discord.ui.button(emoji="🔀", style=discord.ButtonStyle.secondary, row=1)
    async def btn_shuffle(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        player = self._player()
        random.shuffle(player.queue)
        player.is_shuffled = not player.is_shuffled
        player.footer_msg = '🔀 Đã xáo trộn hàng chờ.' if player.is_shuffled else '🔀 Đã tắt shuffle.'
        await self.cog._update_ui(self.guild)

    @discord.ui.button(emoji="🔁", style=discord.ButtonStyle.secondary, row=1)
    async def btn_loop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        player = self._player()
        player.loop_mode = (player.loop_mode + 1) % 3
        labels = ['🔁 Loop: Off', '🔂 Loop: One', '🔁 Loop: All']
        player.footer_msg = labels[player.loop_mode]
        await self.cog._update_ui(self.guild)

    @discord.ui.button(emoji="❤️", style=discord.ButtonStyle.secondary, row=1)
    async def btn_favorite(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        player = self._player()
        if not player.current:
            return
        added = toggle_favorite(interaction.user.id, player.current)
        button.emoji = "❤️" if added else "🤍"
        player.footer_msg = f"{'❤️ Đã thêm vào' if added else '🤍 Đã xóa khỏi'} danh sách yêu thích."
        await self.cog._update_ui(self.guild, user_id=interaction.user.id)

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, row=1)
    async def btn_stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        player = self._player()
        vc = self._vc()
        if not vc:
            return
        if player.current:
            player.history.append(player.current)
            player.current = None
        player.history.extend(player.queue)
        player.queue.clear()
        player.footer_msg = '⏹️ Đã dừng phát nhạc.'
        player.pause_time = 0.0
        player.is_paused = False
        if vc.is_playing() or vc.is_paused():
            player._skip_next_end += 1
            vc.stop()
        await self.cog._update_ui(self.guild)

    @discord.ui.button(emoji="🧹", style=discord.ButtonStyle.danger, row=1)
    async def btn_clear(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        player = self._player()
        vc = self._vc()
        player.history.clear()
        player.queue.clear()
        if player.current:
            player.history.append(player.current)
            player.current = None
        player.pause_time = 0.0
        player.is_paused = False
        player.footer_msg = '🧹 Đã xóa toàn bộ danh sách.'
        if vc and (vc.is_playing() or vc.is_paused()):
            player._skip_next_end += 1
            vc.stop()
        await self.cog._update_ui(self.guild)

    # Row 2: 🔇 🔉 🔊 📜 ⬇️
    @discord.ui.button(emoji="🔇", style=discord.ButtonStyle.secondary, row=2)
    async def btn_mute(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        player = self._player()
        vc = self._vc()
        if player.muted:
            player.muted = False
            player.volume = player.muted_volume
            button.emoji = "🔇"
            player.footer_msg = f"🔊 Unmuted: {int(player.volume * 100)}%"
        else:
            player.muted_volume = player.volume
            player.muted = True
            button.emoji = "🔊"
            player.footer_msg = "🔇 Muted"
        if vc and vc.source:
            vc.source.volume = 0.0 if player.muted else player.volume
        await self.cog._update_ui(self.guild)

    @discord.ui.button(emoji="🔉", style=discord.ButtonStyle.secondary, row=2)
    async def btn_vol_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        player = self._player()
        vc = self._vc()
        player.volume = max(0.1, round(player.volume - 0.1, 1))
        if vc and vc.source:
            vc.source.volume = 0.0 if player.muted else player.volume
        player.footer_msg = f"🔉 Volume: {int(player.volume * 100)}%"
        await self.cog._update_ui(self.guild)

    @discord.ui.button(emoji="🔊", style=discord.ButtonStyle.secondary, row=2)
    async def btn_vol_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        player = self._player()
        vc = self._vc()
        player.volume = min(3.0, round(player.volume + 0.1, 1))
        if vc and vc.source:
            vc.source.volume = 0.0 if player.muted else player.volume
        player.footer_msg = f"🔊 Volume: {int(player.volume * 100)}%"
        await self.cog._update_ui(self.guild)

    @discord.ui.button(emoji="📜", style=discord.ButtonStyle.secondary, row=2)
    async def btn_save_playlist(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self._player()
        if not player.current and not player.queue and not player.history:
            await interaction.response.send_message("❌ Không có bài nào để lưu.", ephemeral=True)
            return
        user_playlists = get_user_playlists(interaction.user.id)
        is_saved = '__current__' in user_playlists
        if is_saved:
            delete_player_playlist(interaction.user.id, '__current__')
            button.emoji = "📜"
            player.footer_msg = "🗑️ Đã xóa playlist đã lưu."
        else:
            save_player_playlist(interaction.user.id, '__current__', player)
            button.emoji = "🗑️"
            player.footer_msg = "📜 Đã lưu playlist hiện tại."
        await interaction.response.defer()
        await self.cog._update_ui(self.guild)

    @discord.ui.button(emoji="⬇️", style=discord.ButtonStyle.secondary, row=2)
    async def btn_download(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"[btn_download] called by {interaction.user}")
        player = self._player()
        if not player.current:
            await interaction.response.send_message("Không có bài nào đang phát.", ephemeral=True)
            return
        url = player.current.url
        is_local = not url.startswith('http')
        if is_local:
            import os
            if not os.path.exists(url):
                await interaction.response.send_message("❌ File không tồn tại.", ephemeral=True)
                return
            size_mb = os.path.getsize(url) / 1024 / 1024
            if size_mb > 24:
                await interaction.response.send_message(f"❌ File quá lớn ({size_mb:.1f}MB), giới hạn 25MB.", ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send(
                f"🎵 **{player.current.title}**",
                file=discord.File(url),
                ephemeral=True,
            )
        else:
            from urllib.parse import quote
            cobalt_url = f"https://dogdish.co.za/#q={quote(url, safe='')}"
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="⏬️ Tải xuống", url=cobalt_url, style=discord.ButtonStyle.link))
            await interaction.response.send_message(
                f"🎵 **{player.current.title}**",
                view=view,
                ephemeral=True,
            )
        print(f"[btn_download] sent")
