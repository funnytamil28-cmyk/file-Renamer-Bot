import os
import json
import asyncio
import subprocess
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

# Telegram API Credentials (Replace with your values)
API_ID = int(os.environ.get("API_ID", "1234567"))
API_HASH = os.environ.get("API_HASH", "YOUR_API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")

app = Client("stream_remover_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# User session data storage
USER_DATA = {}

# Helper function: Extract streams safely using FFprobe
def get_media_streams(file_path):
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "stream=index,codec_type,codec_name,language:stream_tags=language",
        "-of", "json",
        file_path
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        data = json.loads(result.stdout)
        return data.get("streams", [])
    except Exception as e:
        print(f"FFprobe Error: {e}")
        return []

@app.on_message(filters.document | filters.video)
async def handle_file(client: Client, message: Message):
    chat_id = message.chat.id
    status_msg = await message.reply_text("📥 Downloading file to inspect streams...")
    
    file_path = await message.download()
    
    await status_msg.edit_text("🔍 Analyzing media streams with FFprobe...")
    streams = get_media_streams(file_path)
    
    if not streams:
        await status_msg.edit_text("❌ Failed to read streams or file header corrupted! (FFprobe returned 0 streams)")
        if os.path.exists(file_path):
            os.remove(file_path)
        return

    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
    subtitle_streams = [s for s in streams if s.get("codec_type") == "subtitle"]

    USER_DATA[chat_id] = {
        "file_path": file_path,
        "audio_streams": audio_streams,
        "subtitle_streams": subtitle_streams,
        "remove_audio": [],
        "remove_subs": []
    }

    text = (
        f"📂 **File Received:** `{os.path.basename(file_path)}`\n\n"
        f"🎵 **Audio Tracks:** {len(audio_streams)} | 💬 **Subtitles:** {len(subtitle_streams)}\n\n"
        "Keazhe irukura options click panni remove panna vendiya streams select pannunga:"
    )

    buttons = [
        [InlineKeyboardButton("🎵 Audio Streams", callback_data="show_audio"),
         InlineKeyboardButton("💬 Subtitle Streams", callback_data="show_subs")],
        [InlineKeyboardButton("🚀 Remove Selected & Process", callback_data="process_ffmpeg")]
    ]

    await status_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex("process_ffmpeg"))
async def process_media(client: Client, callback: CallbackQuery):
    chat_id = callback.message.chat.id
    data = USER_DATA.get(chat_id)

    if not data or not os.path.exists(data.get("file_path", "")):
        await callback.answer("❌ File session expired. Please re-send the file.", show_alert=True)
        return

    file_path = data["file_path"]
    audio_count = len(data["audio_streams"])
    sub_count = len(data["subtitle_streams"])

    # Prevention: Infinite loop check if no streams present
    if audio_count == 0 and sub_count == 0:
        await callback.answer("⚠️ No selectable streams found in this file to remove!", show_alert=True)
        return

    await callback.message.edit_text("⚙️ **FFmpeg Processing Stream Removal...**\nPlease wait, this may take a few moments.")

    output_path = f"processed_{os.path.basename(file_path)}"
    
    # Build FFmpeg command safely
    ffmpeg_cmd = ["ffmpeg", "-y", "-i", file_path, "-map", "0:v?"]

    # Keep non-selected audio
    for idx, stream in enumerate(data["audio_streams"]):
        if idx not in data["remove_audio"]:
            ffmpeg_cmd.extend(["-map", f"0:{stream['index']}"])

    # Keep non-selected subtitles
    for idx, stream in enumerate(data["subtitle_streams"]):
        if idx not in data["remove_subs"]:
            ffmpeg_cmd.extend(["-map", f"0:{stream['index']}"])

    ffmpeg_cmd.extend(["-c", "copy", output_path])

    # Run FFmpeg asynchronously with Timeout protection
    try:
        proc = await asyncio.create_subprocess_exec(*ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        await asyncio.wait_for(proc.communicate(), timeout=600)  # 10 min timeout
        
        if proc.returncode == 0 and os.path.exists(output_path):
            await callback.message.edit_text("📤 Uploading processed file...")
            await client.send_document(chat_id, document=output_path, caption="✅ Stream removal complete!")
            await callback.message.delete()
        else:
            await callback.message.edit_text("❌ FFmpeg processing failed.")
    except asyncio.TimeoutError:
        await callback.message.edit_text("❌ Process timed out! FFmpeg took too long.")
    except Exception as e:
        await callback.message.edit_text(f"❌ Error: {str(e)}")
    finally:
        # Cleanup
        if os.path.exists(file_path): os.remove(file_path)
        if os.path.exists(output_path): os.remove(output_path)
        USER_DATA.pop(chat_id, None)

if __name__ == "__main__":
    print("Bot started running...")
    app.run()
    
