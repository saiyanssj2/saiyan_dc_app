# Yêu cầu & Quyết định kỹ thuật
1. Bắt buộc phải lấy được nhạc trên youtube
2. Khi lấy theo playlist (bất kể số lượng là bao nhiêu, cần phải phản hồi và phát nhạc ngay lập tức)
3. yêu cầu khi sửa, thêm, xóa code phải đọc được những đoạn code liên quan, tránh xóa thiếu, xóa thừa, xóa sai
## Mục tiêu

- Deploy free trên hosting miễn phí (Render / Fly.io)
- Nhẹ, ít dependency, dễ maintain
- UI xịn sò (embed + buttons)
- Có thể kiếm tiền sau này (premium features)

## Quyết định: Bỏ Lavalink, dùng yt-dlp + FFmpeg

**Lý do:**
- Lavalink cần Java + ~512MB RAM → không chạy được trên free tier
- Cần quản lý 2 process → phức tạp khi deploy
- YouTube plugin của Lavalink hay bị block, phải update liên tục
- yt-dlp chỉ cần 1 process Python + FFmpeg, nhẹ, deploy 1 Dockerfile là xong

**Trade-off chấp nhận:**
- Không scale tốt bằng Lavalink (giới hạn ~5-10 voice channels đồng thời)
- Không hỗ trợ Spotify trực tiếp (chỉ YouTube)
- CPU usage cao hơn do FFmpeg chạy cùng process

## Roadmap kiếm tiền (Premium features)

### Free tier
- `/play`, `/pause`, `/skip`, `/previous`, `/next_10s`, `/previous_10s`, `/play_next`, `/stop`, `/shuffle`, `/loop`, `/favorite`, `/volume_up`, `/volume_down`, `/mute`, `/unmute`, `/quit` or `/disconnect`
- UI buttons (pause/resume, skip, previous, next_10s, previous_10s, stop, shuffle, loop, favorite, volume_up, volume_down, mute/unmute)

### Premium tier (Patreon/Ko-fi)
- 24/7 mode (bot không tự disconnect)
- Audio filters (bass boost, nightcore, slowed)
- Spotify/SoundCloud support
- Priority queue (bài premium user luôn phát trước)

## Khi nào quay lại Lavalink

- Khi bot phục vụ >50 guilds đồng thời
- Khi có revenue đủ trả VPS ($3-5/tháng)
- Dùng Oracle Cloud Free Tier (4 ARM cores, 24GB RAM) để host Lavalink miễn phí

### Các yêu cầu chi tiết: (phần nào không làm được cần hỏi lại thay vì viết 1 tính năng ko dùng được)
- /play: tìm nhạc trên youtube
    - Nếu là từ khóa: tìm top 10 bài đầu tiên để user lựa chọn dropdown hoặc checklist hoặc chat số
        - Nếu là dropdown hoặc chat số tương ứng thì phát bài đó
        - Nếu là checklist hoặc chat nhiều số thì phát những bài hát đó
    - Nếu là URL:
        - Nếu là URL 1 bài thì phát bài đó
        - Nếu là URL 1 playlist thì phát playlist đó
- /spotify: tìm nhạc trên spotify: tương tự youtube
- /search: tìm nhạc ở bất kỳ đâu:
    - Nếu user đưa từ khóa thì làm giống như youtube
    - Nếu user đưa link thì quét các file video hoặc âm nhạc của link đó để user lựa chọn
        - quá trình lựa chọn sẽ giống như youtube gồm dropdown hoặc checklist hoặc chat số
- /local: tìm nhạc trong máy cá nhân: cần hỏi lại đường dẫn tuyệt đối của file hoặc folder chứa file đó
    - nếu là folder thì quá trình giống như youtube gồm dropdown hoặc checklist hoặc chat số
### Giao diện:
- Nếu user phải trả lời: đưa ra câu hỏi và đợi user trả lời (chỉ user thấy, phản hồi xong thì xóa tín nhắn và đến với phần thêm bài hát)
- Nếu thêm bài hát: đưa ra UI thông báo (user) đã thêm:
    - Nếu 1 bài hát thì đưa ra thông tin tên, tác giả, ảnh bài hát, thời lượng
    - Nếu nhiều bài hát thì đưa ra thông tin playlist(nếu có), số bài hát, ảnh playlist(nếu có), thời lượng(nếu có)
    - Cuối cùng là gửi lại tin nhắn UI đang phát để UI ko bị trôi đi
- Nên tạo 3 queue để lưu danh sách gồm: queue đã phát, queue đang phát(luôn chỉ có 1 bài), queue sẽ phát
- Nên tạo 1 file để lưu danh sách bài hát favorite(lưu theo user, thông tin bài hát)
- Thông tin 1 bài hát nên lấy: tên, tác giả, url, ảnh
- UI thêm bài hát: hiển thị thông tin
- UI chính:
    - hiển thị header là thông tin bài đang phát
    - 3 bài hát đã phát gần nhất
    - 3 bài hát đầu tiên trong queue
    - các button
    - footer update thông báo

- Nếu tương tác với UI button hoặc lệnh: có thể update trực tiếp vào UI cũ:
    - Nếu hết bài thì giữ nguyên UI của bài cuối cùng và update footer UI thông báo hết bài hát
    - Nếu bài đầu tiên mà user sử dụng previous thì update footer UI thông báo bài đầu tiên
    - ⏸️/▶️pause/resume: nhạc đang phát thì hiện nút pause, nhấn thì nhạc dừng và update UI thành resume
    - 🔀shuffle: xáo trộn hàng đợi mỗi lần nhấn
    - ⏭️skip: chuyển tới bài đầu tiên trong hàng đợi, nếu đang loop cũng chuyển
    - ⏮️previous: chuyển tới bài trước đó đã phát (lấy bài đang phát ra khỏi queue đang phát và đưa vào đầu queue sẽ phát (FILO), lấy bài gần nhất đã phát ra khỏi queue đã phát (LIFO) và đưa vào queue đang phát,), nếu chưa có bài trước đó thì update UI thông báo
    - ⏪next_10s: tua bài đang phát 10s
    - ⏩previous_10s: tua ngược bài đang phát 10s
    - ⏹️stop: giữ bot lại, chuyển hết bài hát vào queue đã phát
    - loop:
        - 🔂loop 1:
        - 🔁loop all: Nếu bài cuối kết thúc thì đưa bài đầu tiên của queue đã phát (FIFO) vào queue đang phát và đưa phần còn lại của queue đã phát lưu lại vào queue sẽ phát, bài hát cuối cùng vừa phát cũng được lưu vào cuối queue sẽ phát.
        - 🔁(làm mờ đi)loop off:
    - ❤️/🤍favorite/Unfavorite: Thêm bài đang phát vào file json
    - 🔊volume_up: Tăng mỗi lần 10% (max 300%)
    - 🔉volume_down: Giảm mỗi lần 10% (min 10%)
    - 🔇/🔊mute/unmute:
        - mute: ghi nhớ âm lượng hiện tại rồi chuyển về 0%
        - unmute: chuyển về âm lượng trước đó
    - ⬇️download: cho phép download file âm thanh về máy
    - 📜/🗑️save_playlist/unsave_playlist: lưu playlist như favorite
    - 🧹clear playlist: xóa 3 queue
- Lệnh:
    - `/play_next`: dùng để đưa bài hát họ chọn vào đầu hàng đợi (LIFO)
    - `/quit` or `/disconnect`: cho bot thoát khỏi voice channel và xóa 3 queue
    - `/favorite`: để xem và thêm favorite vào queue
    - `/playlist`: để xem và thêm playlist vào queue
    - `/ping`:
    - và các lệnh tương ứng với nút UI

### trả lời câu hỏi
- timeout bao lâu nếu user không chọn? hủy nếu sau 1 min user ko chọn
- Câu hỏi: logic này khá phức tạp, bạn có muốn loop all hoạt động như "phát lại toàn bộ theo thứ tự ban đầu" không? Hay đúng như mô tả trên? phát lại toàn bộ theo thứ tự ban đầu
- Câu hỏi: discord.py hỗ trợ volume qua PCMVolumeTransformer, nhưng chỉ hoạt động khi wrap FFmpegPCMAudio. Bạn có muốn mình handle cái này không? nếu phức tạp có thể đổi thư viện, nếu đơn giản thì handle
- Câu hỏi: cái này khó - FFmpegPCMAudio stream không hỗ trợ seek trực tiếp. Cách duy nhất là restart FFmpeg với -ss offset. Mình cần track thời gian đang phát. Bạn có chấp nhận cách này không (sẽ có ~1-2s delay khi seek)? Nếu delay 1s thì được, hoặc sử dụng thư viện khác hỗ trợ
- Câu hỏi: lưu ở đâu? data/favorites.json? okay
- Và thông tin lưu gồm: tên, tác giả, url, ảnh - đúng không? đúng hoặc có thể lưu thêm những thứ m cần để gọi bài đó lên
- Câu hỏi: UI này update in-place (edit message cũ) hay gửi message mới mỗi lần? edit message cũ
- Câu hỏi: bạn có muốn làm trong lần này không hay để sau? Hãy chia nhỏ làm sau mỗi lần phản hồi
- Vì /spotify cần Spotify API credentials, /local cần path từ user? /local ý định của t là muốn hỏi user hoặc trong form /local cần user điền path ở mỗi request
- /play keyword → hiện top 10 → user chọn qua dropdown hay chat số? Hay để user tự chọn cách? Vì Discord chỉ cho dropdown tối đa 25 options, còn chat số thì cần bot lắng nghe message tiếp theo. -> Để user chọn
- Khi playlist lớn (ví dụ 100 bài), bạn muốn load hết vào queue ngay hay lazy load (load từng batch khi gần hết)? lazy load để bot ko được có độ trễ, ví dụ playlist 5 bài load mất 5s thì hãy load và phát bài đầu tiên nhanh nhất có thể rồi xử lý load tiếp 4 bài còn lại, bên dưới cứ xử lý còn trên UI vẫn hiện 5 bài hoặc 100 bài coi như ko hề bị delay
- Button favorite khi bài đang phát đã được thêm rồi thì hiện thị thế nào? Đổi màu button hay thông báo? đổi qua lại giữa ❤️/🤍
- /play_next hoạt động giống /play (tìm kiếm + chọn bài) nhưng đưa vào đầu queue - đúng không? Đúng
- Khi bot hết bài (queue trống, không loop), bot có tự disconnect sau X phút không hay ở lại chờ? có, nên disconnect sau 5 min

- Dropdown vs chat số - Discord có 2 cách:
Dropdown (Select Menu): user click chọn, chỉ chọn được 1 hoặc nhiều option, timeout tự ẩn sau 1 phút → clean hơn
Chat số: user gõ 1 hoặc 1 3 5, bot lắng nghe message tiếp theo → linh hoạt hơn nhưng phức tạp hơn
Bạn muốn cả hai (user tự chọn cách) hay chỉ dropdown cho đơn giản?
=> Nếu chọn được 1 hoặc nhiều option thì chỉ cần dùng dropdown cho đơn giản
- Khi user đang chọn bài (dropdown đang hiện), user khác trong cùng guild có thể interact không? Hay chỉ người gọi lệnh mới được chọn? có
- Seek track thời gian: mình cần lưu start_time khi bài bắt đầu phát. Khi seek, tính elapsed = now - start_time + offset rồi restart FFmpeg với -ss elapsed. Bạn có muốn hiển thị progress bar trên UI không (ví dụ ▶ 1:23 ━━━━●───── 3:45)? Nếu ko phức tạp và ko ảnh hưởng tới việc phát nhạc cũng như request từ user thì làm, ko thì chỉ cần tượng trưng thời gian phát thôi

-Lưu playlist như thế nào? - Lưu toàn bộ danh sách bài hiện tại trong queue (bao gồm cả bài đang phát) hay chỉ lưu URL playlist gốc? -Lưu 3 queue đã, đang, sẽ phát hiện tại, theo user lưu
- Lưu ở đâu? - Cùng file favorites.json hay file riêng playlists.json? Lưu vào playlists.json
- Gọi lại playlist bằng cách nào? - Có lệnh /playlist để xem và phát lại không? Thêm lệnh /playlist để xem và thêm playlist vào queue, thêm cả lệnh /favourite tương tự

### test 1.0
- Lỗi khi sử dụng /play sontung, bot đang suy nghĩ, có vào channel
- Lỗi khi tua 10s
[after_play error] exception: integer divide by zero
ERROR: [DRM] The requested site is known to use DRM protection. It will NOT be supported. 
       Please DO NOT open an issue, unless you have evidence that the video is not DRM protected 
[after_play error] exception: integer divide by zero
- các tương tác UI phản hồi hơi chậm

### fix 1.0
- /play sontung bị treo: do YDL_OPTS_SEARCH thiếu extract_flat, yt-dlp fetch từng video một mất 30-60s
  → Fix: thêm 'extract_flat': 'in_playlist' vào YDL_OPTS_SEARCH → search còn 1.8s
- /play sontung không có stream_url: extract_flat trả về url thay vì webpage_url
  → Fix: lấy e.get('webpage_url') or e.get('url', '') thay vì chỉ webpage_url
- asyncio.get_event_loop() deprecated Python 3.10+, bot dùng Python 3.14
  → Fix: đổi tất cả get_event_loop() → get_running_loop()
- Tua 10s xong bị chuyển bài ngay: voice_client.stop() trigger after_play của bài cũ → _on_track_end chạy
  → Fix: dùng counter _skip_next_end, tăng trước khi stop(), giảm trong _on_track_end
- Previous rồi tua 10s bị lỗi tương tự: play_track cũng gọi stop() khi đang phát
  → Fix: play_track cũng tăng _skip_next_end trước khi stop()
- Loop 1 nhấn skip vẫn phát lại bài cũ: _on_track_end thấy loop_mode=1 → phát lại
  → Fix: tạm set loop_mode=0 trước khi stop(), restore sau
- /local không phát được file local: make_ffmpeg_opts dùng -reconnect cho cả file local
  → Fix: thêm is_local flag, bỏ -reconnect options khi phát file local

- Nút ⏸️ khi nhấn không chuyển sang ▶️: _update_ui tạo MusicControlView mới → button reset về ⏸️
  → Fix: thêm is_paused vào MusicPlayer, MusicControlView check khi khởi tạo để set đúng icon
- Nút ⏹️ không chuyển UI sang ▶️: chưa set is_paused=False khi stop
  → Fix: set is_paused=False trong btn_stop và /stop command
- Nhấn ▶️ sau stop để phát lại: thêm case lấy bài cuối history phát lại
- /local không phát được: make_ffmpeg_opts dùng -reconnect cho cả file local
  → Fix: thêm is_local flag, bỏ -reconnect options khi phát file local

### tính năng đã làm
- /play: keyword → dropdown top 10, URL 1 bài, URL playlist (lazy load)
- /play_next: đưa vào đầu queue
- /skip, /stop, /queue, /disconnect, /quit
- /playlist: xem và thêm playlist đã lưu vào queue
- /favorite: xem và thêm bài yêu thích vào queue
- /local: phát file/folder local (mp3, flac, wav, ogg, m4a, aac, opus, wma)
- /search: tìm keyword hoặc link bất kỳ
- /spotify: tìm keyword, track, album, playlist Spotify (metadata → YouTube stream)
- 3 queue: history / current / upcoming
- Loop 0/1/2, shuffle, volume 10%-300%, mute/unmute
- Seek ±10s restart FFmpeg với is_local flag
- Favorite lưu data/favorites.json, Playlist lưu data/playlists.json
- UI in-place edit, progress bar, footer thông báo, auto disconnect sau 5 phút
- Button layout:
  - Row 0: ⏮️ ⏪ ⏸️/▶️ ⏩ ⏭️
  - Row 1: 🔀 🔁 ❤️/🤍 ⏹️ 🧹
  - Row 2: 🔇 🔉 🔊 📜 ⬇️
- Tách file: music_core.py / music_ui.py / music_controls.py / music_cog.py / local_cog.py / search_cog.py / spotify_cog.py
