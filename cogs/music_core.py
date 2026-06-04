import asyncio
import json
import os
import time
import discord

# ─── FFmpeg path ─────────────────────────────────────────────────────────────
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FFMPEG_PATH = os.path.join(_BASE, "ffmpeg", "ffmpeg-8.1.1-essentials_build", "bin", "ffmpeg.exe")
if not os.path.exists(FFMPEG_PATH):
    FFMPEG_PATH = "ffmpeg"

FAVORITES_PATH = os.path.join(_BASE, "data", "favorites.json")
PLAYLISTS_PATH = os.path.join(_BASE, "data", "playlists.json")
_COOKIES_PATH = os.path.join(_BASE, "cookies.txt")
_COOKIES_OPTS = {'cookiefile': _COOKIES_PATH} if os.path.exists(_COOKIES_PATH) else {}

# ─── yt-dlp options ──────────────────────────────────────────────────────────
YDL_OPTS_SEARCH = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch10',
    'noplaylist': True,
    'source_address': '0.0.0.0',
    'extract_flat': 'in_playlist',
    **_COOKIES_OPTS,
}

YDL_OPTS_URL = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'source_address': '0.0.0.0',
    'noplaylist': False,
    **_COOKIES_OPTS,
}

YDL_OPTS_SINGLE = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'source_address': '0.0.0.0',
    'noplaylist': True,
    **_COOKIES_OPTS,
}

def make_ffmpeg_opts(seek: float = 0, is_local: bool = False) -> dict:
    if is_local:
        before = ''
        if seek > 0:
            before = f'-ss {seek}'
    else:
        before = '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
        if seek > 0:
            before += f' -ss {seek}'
    return {'executable': FFMPEG_PATH, 'before_options': before, 'options': '-vn'}


# ─── Track ───────────────────────────────────────────────────────────────────
class Track:
    def __init__(self, title: str, author: str, url: str, stream_url: str,
                 thumbnail: str = None, duration: int = 0):
        self.title = title
        self.author = author
        self.url = url
        self.stream_url = stream_url
        self.thumbnail = thumbnail
        self.duration = duration

    def to_dict(self) -> dict:
        return {
            'title': self.title,
            'author': self.author,
            'url': self.url,
            'stream_url': self.stream_url,
            'thumbnail': self.thumbnail,
            'duration': self.duration,
        }

    @staticmethod
    def from_ydl(data: dict) -> 'Track':
        return Track(
            title=data.get('title', 'Unknown'),
            author=data.get('uploader') or data.get('channel', 'Unknown'),
            url=data.get('webpage_url', ''),
            stream_url=data.get('url', ''),
            thumbnail=data.get('thumbnail'),
            duration=data.get('duration', 0),
        )

    def format_duration(self) -> str:
        if not self.duration:
            return '?:??'
        m, s = divmod(int(self.duration), 60)
        h, m = divmod(m, 60)
        return f'{h}:{m:02d}:{s:02d}' if h else f'{m}:{s:02d}'


# ─── MusicPlayer ─────────────────────────────────────────────────────────────
class MusicPlayer:
    def __init__(self):
        self.history: list[Track] = []
        self.current: Track | None = None
        self.queue: list[Track] = []

        self.loop_mode = 0      # 0=off, 1=one, 2=all
        self.is_shuffled = False
        self.volume = 1.0
        self.muted = False
        self.muted_volume = 1.0

        self.seek_offset: float = 0.0
        self.start_time: float = 0.0
        self.pause_time: float = 0.0
        self.is_paused: bool = False

        self.idle_task: asyncio.Task | None = None
        self.footer_msg: str = ''
        self.control_message: discord.Message | None = None
        self.stopped: bool = False
        self._skip_next_end: int = 0  # số lần cần bỏ qua _on_track_end

    def elapsed(self) -> float:
        if not self.start_time:
            return self.seek_offset
        if self.pause_time:
            return self.seek_offset + (self.pause_time - self.start_time)
        return self.seek_offset + (time.time() - self.start_time)

    def is_favorited(self, user_id: int) -> bool:
        favs = load_favorites()
        key = str(user_id)
        if key not in favs or not self.current:
            return False
        return any(f['url'] == self.current.url for f in favs[key])


# ─── Favorites helpers ────────────────────────────────────────────────────────
def load_favorites() -> dict:
    try:
        with open(FAVORITES_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_favorites(data: dict):
    with open(FAVORITES_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def toggle_favorite(user_id: int, track: Track) -> bool:
    """Trả về True nếu vừa thêm, False nếu vừa xóa"""
    favs = load_favorites()
    key = str(user_id)
    if key not in favs:
        favs[key] = []
    existing = next((i for i, f in enumerate(favs[key]) if f['url'] == track.url), None)
    if existing is not None:
        favs[key].pop(existing)
        save_favorites(favs)
        return False
    favs[key].append(track.to_dict())
    save_favorites(favs)
    return True


# ─── Playlist helpers ──────────────────────────────────────────────────────────
def load_playlists() -> dict:
    try:
        with open(PLAYLISTS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_playlists(data: dict):
    with open(PLAYLISTS_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_player_playlist(user_id: int, name: str, player: 'MusicPlayer') -> None:
    """Lưu 3 queue hiện tại của player theo user"""
    playlists = load_playlists()
    key = str(user_id)
    if key not in playlists:
        playlists[key] = {}
    playlists[key][name] = {
        'history': [t.to_dict() for t in player.history],
        'current': player.current.to_dict() if player.current else None,
        'queue': [t.to_dict() for t in player.queue],
    }
    save_playlists(playlists)

def delete_player_playlist(user_id: int, name: str) -> bool:
    """Xóa playlist, trả về True nếu xóa được"""
    playlists = load_playlists()
    key = str(user_id)
    if key not in playlists or name not in playlists[key]:
        return False
    del playlists[key][name]
    save_playlists(playlists)
    return True

def get_user_playlists(user_id: int) -> dict:
    playlists = load_playlists()
    return playlists.get(str(user_id), {})

def playlist_to_tracks(data: dict) -> list['Track']:
    """Chuyển data playlist thành list Track (history + current + queue)"""
    tracks = []
    for t in data.get('history', []):
        tracks.append(Track(**{k: t[k] for k in ('title','author','url','stream_url','thumbnail','duration')}))
    if data.get('current'):
        t = data['current']
        tracks.append(Track(**{k: t[k] for k in ('title','author','url','stream_url','thumbnail','duration')}))
    for t in data.get('queue', []):
        tracks.append(Track(**{k: t[k] for k in ('title','author','url','stream_url','thumbnail','duration')}))
    return tracks


# ─── Time formatter ──────────────────────────────────────────────────────────
def fmt_time(seconds: float) -> str:
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f'{h}:{m:02d}:{s:02d}' if h else f'{m}:{s:02d}'
