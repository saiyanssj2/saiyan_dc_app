import discord
from discord.ext import commands
import requests
from bs4 import BeautifulSoup

def setup(bot):
    @bot.tree.command(name="lol")
    async def lol(interaction: discord.Interaction, champion: str):
        voice_channel = interaction.user.voice.channel

        if voice_channel is not None:
            # Kiểm tra xem bot đã kết nối chưa
            voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)

            if voice_client is None:
                # Kết nối đến kênh thoại nếu chưa có kết nối
                voice_client = await voice_channel.connect()

            try:
                await interaction.response.defer()
                audio_url = f"https://leagueoflegends.fandom.com/wiki/{champion}/LoL/Audio"
                response = requests.get(audio_url)
                soup = BeautifulSoup(response.content, "html.parser")
                audio_buttons = soup.find_all("audio", class_="ext-audiobutton")

                if audio_buttons:
                    audio_links = []
                    for audio in audio_buttons:
                        source = audio.find("source")
                        if source and source.has_attr('src'):
                            audio_links.append(source['src'])

                    if audio_links:
                        # Giới hạn số lượng âm thanh hiển thị
                        limited_audio_links = audio_links[:10]  # Hiển thị tối đa 10 âm thanh
                        audio_list = "\n".join([f"{i + 1}. {limited_audio_links[i]}" for i in range(len(limited_audio_links))])
                        audio_count = len(audio_links)
                        await interaction.followup.send(
                            f"Có {audio_count} âm thanh cho champion **{champion}**:\n{audio_list}\n"
                            "Vui lòng chọn số âm thanh để phát (1 đến 10)."
                        )
                        
                        def check(message):
                            return message.author == interaction.user and message.channel == interaction.channel

                        try:
                            message = await bot.wait_for('message', check=check, timeout=30.0)
                            choice = int(message.content)

                            if 1 <= choice <= len(limited_audio_links):
                                voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)

                                if voice_client and not voice_client.is_playing():
                                    voice_client.play(discord.FFmpegPCMAudio(limited_audio_links[choice - 1]))
                                    await interaction.followup.send(f"Đang phát âm thanh cho champion: {champion}")
                                else:
                                    await interaction.followup.send("Bot đã đang phát âm thanh.")
                            else:
                                await interaction.followup.send("Lựa chọn không hợp lệ.")
                        except ValueError:
                            await interaction.followup.send("Vui lòng nhập một số hợp lệ.")
                        except discord.TimeoutError:
                            await interaction.followup.send("Thời gian chọn âm thanh đã hết.")
                    else:
                        await interaction.followup.send("Không tìm thấy âm thanh cho champion. Vui lòng kiểm tra tên champion.")
                else:
                    await interaction.followup.send("Không tìm thấy âm thanh cho champion. Vui lòng kiểm tra tên champion.")
            except Exception as e:
                print(f"Có lỗi xảy ra khi xử lý lệnh /lol: {str(e)}")
                await interaction.followup.send("Có lỗi xảy ra trong quá trình xử lý lệnh.")
        else:
            await interaction.response.send_message("Bạn cần ở trong một kênh thoại để phát âm thanh.")