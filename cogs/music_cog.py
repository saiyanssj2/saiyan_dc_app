import asyncio
import random
import discord
import wavelink
import os
from discord import app_commands
from discord.ext import commands

class MusicControlView(discord.ui.View):
	def __init__(self, player: wavelink.Player):
		super().__init__(timeout=None)
		self.player = player
		if not hasattr(self.player, 'history'):
			self.player.history = []
		if not hasattr(self.player, 'is_shuffled'): self.player.is_shuffled = False

	async def update_view(self, interaction: discord.Interaction):
		print("===========MusicControlView.update_view===========")
		if not self.player.current:
			embed = discord.Embed(title="🎶 Hàng chờ trống", color=discord.Color.red())
			for child in self.children:
				child.disabled = True
			return await interaction.response.edit_message(embed=embed, view=self)

		# 1. Xử lý "Đang phát"
		current_track = self.player.current
		embed = discord.Embed(color=discord.Color.green())
		embed.title = f" đang phát: {current_track.title}"
		embed.set_thumbnail(url=current_track.artwork)

		# 2. Xử lý "Sẽ phát" (Queue) - Lấy tối đa 5 bài tiếp theo
		upcoming = []
		# vc.queue là một iterable, chúng ta convert sang list để lấy các phần tử đầu
		queue_list = list(self.player.queue)
		for i, track in enumerate(queue_list[:5]):
			upcoming.append(f"{i+1}. {track.title}")
		
		queue_str = "\n".join(upcoming) if upcoming else "Không có bài nào tiếp theo"

		# 3. Xử lý "Đã phát" (History) - Lấy 3 bài gần nhất
		history_str = "\n".join(self.player.history[-3:]) if self.player.history else "Chưa có lịch sử"

		# Thêm các Field vào Embed
		embed.add_field(name="⏮️", value=history_str, inline=False)
		embed.add_field(name="▶️", value=f"[{current_track.title}]({current_track.uri})", inline=False)
		embed.add_field(name="⏭️", value=queue_str, inline=False)

		# 1. Nút Loop
		loop_modes = {
			wavelink.QueueMode.normal: ("🔁 Loop: Off", discord.ButtonStyle.gray),
			wavelink.QueueMode.loop: ("🔂 Loop: One", discord.ButtonStyle.green),
			wavelink.QueueMode.loop_all: ("🔁 Loop: All", discord.ButtonStyle.blurple),
		}
		mode_text, mode_style = loop_modes.get(self.player.queue.mode, ("Loop", discord.ButtonStyle.gray))
		self.loop_button.label = mode_text
		self.loop_button.style = mode_style

		# 2. Nút Shuffle
		self.shuffle_button.style = discord.ButtonStyle.green if self.player.is_shuffled else discord.ButtonStyle.gray

		# Cập nhật trạng thái nút
		self.pause_resume.label = "▶️" if self.player.paused else "⏸️"
		
		await interaction.response.edit_message(embed=embed, view=self)

	@discord.ui.button(label="⏮️", style=discord.ButtonStyle.gray)
	async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
		print("===========MusicControlView.previous===========")
		if not self.player.history:
			return await interaction.response.send_message("❌ Không có bài hát trước đó!", ephemeral=True)
		
		# Lấy bài cuối cùng trong lịch sử
		prev_track_title = self.player.history.pop() 
		# Tìm kiếm và phát lại (Hoặc nếu bạn lưu object Track thì tốt hơn)
		results = await wavelink.Playable.search(prev_track_title)
		if results:
			track = results[0]
			# Đưa bài hiện tại ngược lại vào hàng chờ nếu muốn
			await self.player.play(track)
			await self.update_view(interaction)

	@discord.ui.button(label="⏸️", style=discord.ButtonStyle.blurple)
	async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
		print("===========MusicControlView.pause_resume===========")
		await self.player.pause(not self.player.paused)
		await self.update_view(interaction)

	@discord.ui.button(label="⏭️", style=discord.ButtonStyle.gray)
	async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
		print("===========MusicControlView.skip===========")
		await self.player.skip()
		# Đợi 1 chút để Wavelink cập nhật trạng thái player.current mới
		await asyncio.sleep(0.5) 
		await self.update_view(interaction)

	@discord.ui.button(label="🔀 Shuffle", style=discord.ButtonStyle.gray)
	async def shuffle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
		print("===========MusicControlView.shuffle_button===========")
		self.player.is_shuffled = not self.player.is_shuffled
		if self.player.is_shuffled:
			random.shuffle(self.player.queue._queue) # Trộn hàng chờ
		await self.update_view(interaction)
	
	@discord.ui.button(label="🔁 Loop: Off", style=discord.ButtonStyle.gray)
	async def loop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
		print("===========MusicControlView.loop_button===========")
		# Xoay vòng chế độ: Off -> One -> All -> Off
		if self.player.queue.mode == wavelink.QueueMode.normal:
			self.player.queue.mode = wavelink.QueueMode.loop
		elif self.player.queue.mode == wavelink.QueueMode.loop:
			self.player.queue.mode = wavelink.QueueMode.loop_all
		else:
			self.player.queue.mode = wavelink.QueueMode.normal
		
		await self.update_view(interaction)

	@discord.ui.button(label="⏹️", style=discord.ButtonStyle.red)
	async def stop(self, interaction: discord.Interaction, button: discord.ui.button):
		print("===========MusicControlView.stop===========")
		try:
			# 1. Phản hồi ngay lập tức để Discord không báo lỗi timeout
			await interaction.response.defer(ephemeral=True) 
			
			# 2. Thực hiện dừng nhạc và ngắt kết nối
			if self.player:
				self.player.queue.clear() # Xóa hàng chờ
				await self.player.disconnect() # Ngắt kết nối voice
			
			# 3. Cập nhật lại tin nhắn gốc (Xóa các nút bấm để tránh bấm nhầm lần nữa)
			embed = discord.Embed(
				title="⏹️ Đã dừng nhạc", 
				description="Bot đã ngắt kết nối và xóa hàng chờ.", 
				color=discord.Color.red()
			)
			await interaction.edit_original_response(embed=embed, view=None)
			
		except Exception as e:
			print(f"Lỗi khi nhấn Stop: {e}")
			# Nếu có lỗi, thông báo cho người dùng qua followup vì đã defer ở trên
			await interaction.followup.send("❌ Có lỗi khi cố gắng dừng nhạc!", ephemeral=True)

class Music(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		# Tạo task để kết nối Lavalink ngay khi Cog được nạp
		bot.loop.create_task(self.connect_nodes())

	async def connect_nodes(self):
		"""Kết nối tới Lavalink bằng thông số từ file .env"""
		print("===========Music.connect_nodes===========")
		await self.bot.wait_until_ready() # Đợi bot sẵn sàng mới kết nối node

		# Lấy thông tin từ file .env
		host = os.getenv("LAVALINK_HOST", "127.0.0.1")
		port = int(os.getenv("LAVALINK_PORT", 2333))
		password = os.getenv("LAVALINK_PASSWORD", "youshallnotpass")
		
		# Cấu hình Node (Sử dụng URI định dạng: http://host:port)
		node = wavelink.Node(
			uri=f"http://{host}:{port}", 
			password=password,
		)
		
		try:
			await wavelink.Pool.connect(nodes=[node], client=self.bot)
			print(f"📡 Đã gửi yêu cầu kết nối tới Lavalink tại {host}:{port}")
		except Exception as e:
			print(f"❌ Lỗi kết nối Lavalink: {e}")

	@commands.Cog.listener()
	async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
		print(f"✅ Lavalink Node {payload.node.identifier} đã sẵn sàng!")

	@commands.Cog.listener()
	async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
		print("===========Music.on_wavelink_track_end===========")
		player = payload.player
		if not player:
			return

		# Lưu bài vừa kết thúc vào lịch sử
		if not hasattr(player, 'history'):
			player.history = []
		player.history.append(payload.track.title)

		# Giới hạn lịch sử chỉ giữ 10 bài cho đỡ tốn RAM
		if len(player.history) > 10:
			player.history.pop(0)

		# Nếu còn bài trong hàng chờ, phát bài tiếp theo
		if not player.queue.is_empty:
			next_track = player.queue.get()
			await player.play(next_track)
			# Lưu ý: Bạn có thể lưu trữ tin nhắn giao diện vào biến để update tại đây
		else:
			# Nếu hết bài, có thể gửi thông báo hoặc để im (View sẽ tự update khi người dùng bấm nút)
			print("Hàng chờ đã hết.")

	@app_commands.command(name="play", description="Phát nhạc từ YouTube, Spotify hoặc URL")
	async def play(self, interaction: discord.Interaction, search: str):
		print("===========Music.play===========")
		await interaction.response.defer()
		try:
			if not interaction.user.voice:
				return await interaction.followup.send("❌ Bạn cần vào Voice Channel trước!")

			vc: wavelink.Player = interaction.guild.voice_client or \
								await interaction.user.voice.channel.connect(cls=wavelink.Player)

			# Tìm kiếm bài hát/playlist
			results = await wavelink.Playable.search(search)
			if not results:
				return await interaction.followup.send("❌ Không tìm thấy kết quả nào!")

			# KIỂM TRA NẾU LÀ PLAYLIST
			if isinstance(results, wavelink.Playlist):
				# Thêm toàn bộ bài hát trong playlist vào hàng chờ
				added = await vc.queue.put_wait(results)
				display_name = f"Playlist: {results.name} ({added} bài)"
				track_for_embed = results.tracks[0] # Lấy bài đầu để hiện thumbnail
			else:
				# Nếu là bài đơn lẻ
				track = results[0]
				await vc.queue.put_wait(track)
				display_name = track.title
				track_for_embed = track

			# Nếu bot chưa phát nhạc thì bắt đầu phát bài đầu tiên trong hàng chờ
			if not vc.playing:
				await vc.play(vc.queue.get())

			# Giao diện thông báo
			embed = discord.Embed(
				title="🎶 Đã thêm vào hàng chờ",
				description=f"**{display_name}**",
				color=discord.Color.green()
			)
			if hasattr(track_for_embed, 'artwork'):
				embed.set_thumbnail(url=track_for_embed.artwork)
			
			await interaction.followup.send(embed=embed, view=MusicControlView(vc))

		except Exception as e:
			print(f"🔴 LỖI TẠI LỆNH PLAY: {e}")
			await interaction.followup.send(f"Có lỗi xảy ra: {e}")

	@app_commands.command(name="local", description="Phát nhạc từ thư mục local_musics trên server")
	async def local(self, interaction: discord.Interaction, filename: str):
		print("===========Music.local===========")
		"""Cách 2: Quét thư mục trên Server"""
		path = f"./local_musics/{filename}"
		if not os.path.exists(path):
			return await interaction.response.send_message(f"❌ Không tìm thấy file `{filename}` trong thư mục local_musics!")

		# Lavalink hỗ trợ phát file local nếu đã bật 'local: true' trong application.yml
		await self.play(interaction, path)

	@app_commands.command(name="upload", description="Phát file nhạc bạn gửi lên")
	async def upload(self, interaction: discord.Interaction, file: discord.Attachment):
		print("===========Music.upload===========")
		"""Cách 1: User upload file trực tiếp"""
		if not file.content_type or "audio" not in file.content_type:
			return await interaction.response.send_message("❌ Vui lòng gửi một file âm thanh!")
		
		await self.play(interaction, file.url)

async def setup(bot):
	await bot.add_cog(Music(bot))