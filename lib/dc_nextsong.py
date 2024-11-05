import discord
import asyncio

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -filter:a "volume=0.25"'
}

async def play_next(voice_client, music_queue, interaction):
    # Kiểm tra xem có bài nào trong hàng đợi không
    next_song = music_queue.get_next()
    if next_song:
        title, url = next_song
        music_queue.is_playing = True
        print(f'Now playing: {title}')
        await interaction.followup.send(f"Now playing: {title}")
        # Phát nhạc và xử lý callback khi nhạc kết thúc
        def on_song_end(error):
            # Nếu có lỗi, in ra lỗi
            if error:
                print(f'Error: {error}')
            # Sử dụng asyncio để lên lịch cho bài hát tiếp theo sau khi kết thúc
            future = asyncio.run_coroutine_threadsafe(play_next(voice_client, music_queue, interaction), bot.loop)
            try:
                future.result()
            except Exception as e:
                print(f"Error scheduling next song: {e}")
        audio_source = discord.FFmpegPCMAudio(url, **ffmpeg_options)
        voice_client.play(audio_source, after=on_song_end)
    else:
        music_queue.is_playing = False
        # Ngắt kết nối nếu không còn bài hát
        await voice_client.disconnect()