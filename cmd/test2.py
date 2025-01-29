import discord
from functools import wraps

# Tạo decorator để kiểm tra người dùng đã tham gia voice channel
def require_voice_channel(func):
    @wraps(func)
    async def wrapper(interaction, *args, **kwargs):
        # Kiểm tra xem người dùng có đang trong voice channel không
        voice = interaction.user.voice
        if voice:
            # Nếu có, tiếp tục gọi hàm được trang trí
            return await func(interaction, *args, **kwargs)
        else:
            # Nếu không, gửi tin nhắn thông báo
            await interaction.followup.send("Bạn chưa tham gia vào voice channel.")
    return wrapper

# Sử dụng decorator để trang trí các hàm cần kiểm tra
@require_voice_channel
async def play_music(interaction):
    # Nội dung xử lý khi người dùng đã trong voice channel
    await interaction.followup.send("Đang phát nhạc!")

# Sử dụng decorator trong trường hợp khác
@require_voice_channel
async def stop_music(interaction):
    # Nội dung xử lý khi người dùng đã trong voice channel
    await interaction.followup.send("Dừng phát nhạc!")
