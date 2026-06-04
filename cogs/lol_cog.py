import asyncio
import discord
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup
from discord import app_commands
from discord.ext import commands

from .music_core import Track

DDRAGON_VERSIONS = "https://ddragon.leagueoflegends.com/api/versions.json"
DDRAGON_CHAMPIONS = "https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json"
FANDOM_AUDIO = "https://leagueoflegends.fandom.com/wiki/{champion}/LoL/Audio"

_champion_cache: dict[str, str] = {}


async def _fetch_champions() -> dict[str, str]:
    global _champion_cache
    if _champion_cache:
        return _champion_cache
    loop = asyncio.get_running_loop()
    def _fetch():
        r1 = cffi_requests.get(DDRAGON_VERSIONS, impersonate="chrome120")
        version = r1.json()[0]
        r2 = cffi_requests.get(DDRAGON_CHAMPIONS.format(version=version), impersonate="chrome120")
        data = r2.json()
        return {v['name']: k for k, v in data['data'].items()}
    _champion_cache = await loop.run_in_executor(None, _fetch)
    return _champion_cache


async def _scrape_audio(champion_id: str) -> list[dict]:
    """Scrape audio với category từ heading"""
    loop = asyncio.get_running_loop()
    def _fetch():
        url = FANDOM_AUDIO.format(champion=champion_id)
        r = cffi_requests.get(url, impersonate="chrome120")
        soup = BeautifulSoup(r.content, "html.parser")

        results = []
        dialogue_set = set()
        current_category = "Other"

        for tag in soup.find_all(['h2', 'h3', 'h4', 'audio']):
            if tag.name in ('h2', 'h3', 'h4'):
                current_category = tag.get_text(strip=True).replace('[]', '').strip()
            elif tag.name == 'audio' and 'ext-audiobutton' in tag.get('class', []):
                src_tag = tag.find("source")
                if not src_tag or not src_tag.has_attr('src'):
                    continue
                src = src_tag['src']
                desc_tag = tag.find_next("i")
                label = desc_tag.text.strip() if desc_tag else ""
                if not label:
                    label = src.split("/")[-1].split(".ogg")[0].replace("_", " ")
                if label in dialogue_set:
                    continue
                dialogue_set.add(label)
                results.append({
                    'title': label,
                    'url': src,
                    'category': current_category,
                })
        return results
    return await loop.run_in_executor(None, _fetch)


# ─── Audio Page View ─────────────────────────────────────────────────────────
class AudioPageView(discord.ui.View):
    PAGE_SIZE = 20

    def __init__(self, cog, audios: list[dict], champion: str,
                 guild: discord.Guild, vc: discord.VoiceClient, page: int = 0):
        super().__init__(timeout=120)
        self.cog = cog
        self.audios = audios
        self.champion = champion
        self.guild = guild
        self.vc = vc
        self.page = page
        self.total_pages = (len(audios) + self.PAGE_SIZE - 1) // self.PAGE_SIZE
        self._build_buttons()

    def _build_buttons(self):
        self.clear_items()
        start = self.page * self.PAGE_SIZE
        end = min(start + self.PAGE_SIZE, len(self.audios))

        for i in range(start, end):
            audio = self.audios[i]
            btn = discord.ui.Button(
                label=f"{i+1}. {audio['title'][:40]}",
                style=discord.ButtonStyle.secondary,
                row=(i - start) // 5,
            )
            btn.callback = self._make_play_callback(audio)
            self.add_item(btn)

        if self.page > 0:
            prev_btn = discord.ui.Button(label="◀ Trước", style=discord.ButtonStyle.primary, row=4)
            prev_btn.callback = self._prev_page
            self.add_item(prev_btn)

        if self.page < self.total_pages - 1:
            next_btn = discord.ui.Button(label="Tiếp ▶", style=discord.ButtonStyle.primary, row=4)
            next_btn.callback = self._next_page
            self.add_item(next_btn)

    def _make_play_callback(self, audio: dict):
        async def callback(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            music_cog = self.cog
            player = music_cog.get_player(self.guild.id)
            track = Track(
                title=audio['title'][:80],
                author=f"LoL - {self.champion}",
                url=audio['url'],
                stream_url=audio['url'],
                thumbnail=None,
                duration=0,
            )
            player.queue.insert(0, track)
            if not self.vc.is_playing() and not self.vc.is_paused() and not player.current:
                next_track = player.queue.pop(0)
                await music_cog.play_track(self.guild, self.vc, next_track)
        return callback

    async def _prev_page(self, interaction: discord.Interaction):
        self.page -= 1
        self._build_buttons()
        await interaction.response.edit_message(embed=self._build_embed(), view=self)

    async def _next_page(self, interaction: discord.Interaction):
        self.page += 1
        self._build_buttons()
        await interaction.response.edit_message(embed=self._build_embed(), view=self)

    def _build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"🎮 {self.champion} - Âm thanh LoL",
            description=f"Trang {self.page + 1}/{self.total_pages} • {len(self.audios)} âm thanh",
            color=discord.Color.gold(),
        )
        return embed


# ─── Category Select View ─────────────────────────────────────────────────────
class CategorySelectView(discord.ui.View):
    def __init__(self, cog, audios: list[dict], champion: str,
                 guild: discord.Guild, vc: discord.VoiceClient):
        super().__init__(timeout=60)
        self.cog = cog
        self.audios = audios
        self.champion = champion
        self.guild = guild
        self.vc = vc

        # Lấy danh sách category unique
        categories = list(dict.fromkeys(a['category'] for a in audios))
        options = [
            discord.SelectOption(label=cat[:100], value=cat[:100])
            for cat in categories[:25]
        ]
        select = discord.ui.Select(
            placeholder="Chọn category...",
            options=options,
        )
        select.callback = self._on_select
        self.add_item(select)

    async def _on_select(self, interaction: discord.Interaction):
        category = interaction.data['values'][0]
        filtered = [a for a in self.audios if a['category'] == category]
        view = AudioPageView(self.cog, filtered, self.champion, self.guild, self.vc)
        await interaction.response.edit_message(
            embed=view._build_embed(),
            view=view,
        )


# ─── Cog ─────────────────────────────────────────────────────────────────────
class LolCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="lol", description="Phát âm thanh League of Legends")
    @app_commands.describe(champion="Tên champion", voice="Lọc theo từ khóa (tùy chọn)")
    async def lol(self, interaction: discord.Interaction, champion: str, voice: str = None):
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

        champions = await _fetch_champions()
        print(f"[lol] champions loaded: {len(champions)}")
        champion_id = champions.get(champion)
        if not champion_id:
            lower = champion.lower()
            for name, cid in champions.items():
                if name.lower() == lower:
                    champion_id = cid
                    break
        if not champion_id:
            await interaction.followup.send(f"❌ Không tìm thấy champion `{champion}`.", ephemeral=True)
            return

        try:
            audios = await _scrape_audio(champion_id)
            print(f"[lol] {champion} → {len(audios)} audios")
        except Exception as e:
            await interaction.followup.send(f"❌ Không thể tải danh sách âm thanh: `{e}`", ephemeral=True)
            return

        if not audios:
            await interaction.followup.send(f"❌ Không tìm thấy âm thanh nào cho {champion}.", ephemeral=True)
            return

        # Lọc theo voice nếu có
        if voice:
            filtered = [a for a in audios if voice.lower() in a['title'].lower()]
            if not filtered:
                await interaction.followup.send(f"❌ Không tìm thấy âm thanh nào chứa `{voice}`.", ephemeral=True)
                return
            audios = filtered
            # Nếu đã filter thì hiện thẳng AudioPageView
            view = AudioPageView(music_cog, audios, champion, interaction.guild, vc)
            await interaction.followup.send(embed=view._build_embed(), view=view, ephemeral=True)
        else:
            # Hiện CategorySelectView để chọn category trước
            view = CategorySelectView(music_cog, audios, champion, interaction.guild, vc)
            embed = discord.Embed(
                title=f"🎮 {champion} - Âm thanh LoL",
                description=f"{len(audios)} âm thanh • Chọn category:",
                color=discord.Color.gold(),
            )
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @lol.autocomplete('champion')
    async def champion_autocomplete(self, interaction: discord.Interaction, current: str):
        try:
            champions = await _fetch_champions()
        except Exception:
            return []
        matches = [
            app_commands.Choice(name=name, value=name)
            for name in sorted(champions.keys())
            if current.lower() in name.lower()
        ]
        return matches[:25]


async def setup(bot: commands.Bot):
    await bot.add_cog(LolCog(bot))
