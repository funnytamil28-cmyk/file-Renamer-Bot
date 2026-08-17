import asyncio
import json
import os
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import Config

app = Client(
    "AdvancedRenameBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
)

USER_DATA = {}


# --- Helper Functions for Progress Bar ---
def humanbytes(size):
  if not size:
    return "0 B"
  for unit in ["B", "KB", "MB", "GB", "TB"]:
    if size < 1024.0:
      break
    size /= 1024.0
  return f"{size:.2f} {unit}"


def time_formatter(milliseconds: int) -> str:
  seconds, milliseconds = divmod(int(milliseconds), 1000)
  minutes, seconds = divmod(seconds, 60)
  hours, minutes = divmod(minutes, 60)
  tmp = (
      ((str(hours) + "h, ") if hours else "")
      + ((str(minutes) + "m, ") if minutes else "")
      + ((str(seconds) + "s") if seconds else "")
  )
  return tmp if tmp else "0s"


async def progress_func(current, total, ud_type, message, start_time):
  now = time.time()
  diff = now - start_time
  if round(diff % 3.0) == 0 or current == total:
    percentage = current * 100 / total
    speed = current / diff
    time_to_completion = round((total - current) / speed) * 1000

    progress = "[{0}{1}]".format(
        "".join(["█" for _ in range(int(percentage / 10))]),
        "".join(["░" for _ in range(10 - int(percentage / 10))]),
    )

    tmp = (
        f"**{ud_type}**\n\n"
        f"📊 **Progress:** {progress} `{percentage:.2f}%`\n"
        f"🚀 **Speed:** `{humanbytes(speed)}/s`\n"
        f"📦 **Done:** `{humanbytes(current)}` / `{humanbytes(total)}`\n"
        f"⏱️ **ETA:** `{time_formatter(time_to_completion)}`"
    )
    try:
      await message.edit_text(text=tmp)
    except Exception:
      pass


# --- Probe File Streams ---
async def get_file_streams(file_path):
  cmd = [
      "ffprobe",
      "-v",
      "quiet",
      "-print_format",
      "json",
      "-show_streams",
      file_path,
  ]
  process = await asyncio.create_subprocess_exec(
      *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
  )
  stdout, _ = await process.communicate()
  try:
    data = json.loads(stdout.decode())
    return data.get("streams", [])
  except Exception:
    return []


# --- Start Command ---
@app.on_message(filters.command("start"))
async def start_handler(client, message):
  await message.reply_text(
      f"👋 **Vanakkam {message.from_user.first_name}!**\n\n"
      "Enakku edhavadhu Video/Document file anuppunga. Stream removal, custom thumbnail, and metadata auto-apply aagum!"
  )


# --- Set Custom Thumbnail Command ---
@app.on_message(filters.command("thumb") | (filters.private & filters.photo))
async def save_thumb(client, message):
  user_id = message.from_user.id
  thumb_path = f"thumb_{user_id}.jpg"

  if message.photo:
    await message.download(file_name=thumb_path)
    await message.reply_text("✅ **Custom Thumbnail Saved!**")
  else:
    await message.reply_text("📷 Photo reply/send panni thumbnail save panna.")


# --- Media Receiver Handler ---
@app.on_message(filters.private & (filters.document | filters.video))
async def media_handler(client, message):
  user_id = message.from_user.id
  status_msg = await message.reply_text(
      "📥 **Downloading File to Analyze Streams...**"
  )

  start_time = time.time()
  file_path = await client.download_media(
      message=message,
      progress=progress_func,
      progress_args=("📥 **Downloading File...**", status_msg, start_time),
  )

  file_name = (
      message.document.file_name if message.document else message.video.file_name
  )
  streams = await get_file_streams(file_path)

  audio_tracks = [s for s in streams if s.get("codec_type") == "audio"]
  sub_tracks = [s for s in streams if s.get("codec_type") == "subtitle"]

  USER_DATA[user_id] = {
      "file_path": file_path,
      "original_name": file_name,
      "new_name": file_name,
      "audio_tracks": audio_tracks,
      "sub_tracks": sub_tracks,
      "remove_audio_indexes": [],
      "remove_sub_indexes": [],
      "custom_metadata": f"Encoded By @{client.me.username}",
  }

  buttons = InlineKeyboardMarkup([
      [
          InlineKeyboardButton(
              "🎵 Audio Streams", callback_data="view_audio"
          ),
          InlineKeyboardButton("💬 Subtitle Streams", callback_data="view_sub"),
      ],
      [
          InlineKeyboardButton(
              "🚀 Remove Selected & Process", callback_data="process_file"
          )
      ],
  ])

  await status_msg.edit_text(
      f"📂 **File Received:** `{file_name}`\n\n"
      f"🎵 **Audio Tracks:** `{len(audio_tracks)}` | 💬 **Subtitles:** `{len(sub_tracks)}`\n\n"
      "Keazhe irukura options click panni remove panna vendiya streams select pannunga:",
      reply_markup=buttons,
  )


# --- Callback Query Handler ---
@app.on_callback_query()
async def callback_handler(client, callback):
  user_id = callback.from_user.id
  data = callback.data

  if user_id not in USER_DATA:
    return await callback.answer(
        "❌ Session Expired. File ah thirumba anuppunga.", show_alert=True
    )

  udata = USER_DATA[user_id]

  if data == "view_audio":
    btn_list = []
    for idx, track in enumerate(udata["audio_tracks"]):
      lang = track.get("tags", {}).get("language", f"Track {idx+1}")
      is_selected = idx in udata["remove_audio_indexes"]
      mark = "❌ [REMOVE]" if is_selected else "✅ [KEEP]"
      btn_list.append([
          InlineKeyboardButton(
              f"{mark} Audio #{idx+1} ({lang.upper()})",
              callback_data=f"toggle_audio_{idx}",
          )
      ])

    btn_list.append([InlineKeyboardButton("⬅️ Back", callback_data="main_menu")])
    await callback.message.edit_text(
        "❌ **Select Audio Streams to REMOVE:**",
        reply_markup=InlineKeyboardMarkup(btn_list),
    )

  elif data.startswith("toggle_audio_"):
    idx = int(data.split("_")[-1])
    if idx in udata["remove_audio_indexes"]:
      udata["remove_audio_indexes"].remove(idx)
    else:
      udata["remove_audio_indexes"].append(idx)
    await callback.answer("Updated!")

    btn_list = []
    for i, track in enumerate(udata["audio_tracks"]):
      lang = track.get("tags", {}).get("language", f"Track {i+1}")
      is_selected = i in udata["remove_audio_indexes"]
      mark = "❌ [REMOVE]" if is_selected else "✅ [KEEP]"
      btn_list.append([
          InlineKeyboardButton(
              f"{mark} Audio #{i+1} ({lang.upper()})",
              callback_data=f"toggle_audio_{i}",
          )
      ])
    btn_list.append([InlineKeyboardButton("⬅️ Back", callback_data="main_menu")])
    await callback.message.edit_reply_markup(
        reply_markup=InlineKeyboardMarkup(btn_list)
    )

  elif data == "view_sub":
    btn_list = []
    for idx, track in enumerate(udata["sub_tracks"]):
      lang = track.get("tags", {}).get("language", f"Sub {idx+1}")
      is_selected = idx in udata["remove_sub_indexes"]
      mark = "❌ [REMOVE]" if is_selected else "✅ [KEEP]"
      btn_list.append([
          InlineKeyboardButton(
              f"{mark} Subtitle #{idx+1} ({lang.upper()})",
              callback_data=f"toggle_sub_{idx}",
          )
      ])

    btn_list.append([InlineKeyboardButton("⬅️ Back", callback_data="main_menu")])
    await callback.message.edit_text(
        "❌ **Select Subtitle Streams to REMOVE:**",
        reply_markup=InlineKeyboardMarkup(btn_list),
    )

  elif data.startswith("toggle_sub_"):
    idx = int(data.split("_")[-1])
    if idx in udata["remove_sub_indexes"]:
      udata["remove_sub_indexes"].remove(idx)
    else:
      udata["remove_sub_indexes"].append(idx)
    await callback.answer("Updated!")

    btn_list = []
    for i, track in enumerate(udata["sub_tracks"]):
      lang = track.get("tags", {}).get("language", f"Sub {i+1}")
      is_selected = i in udata["remove_sub_indexes"]
      mark = "❌ [REMOVE]" if is_selected else "✅ [KEEP]"
      btn_list.append([
          InlineKeyboardButton(
              f"{mark} Subtitle #{i+1} ({lang.upper()})",
              callback_data=f"toggle_sub_{i}",
          )
      ])
    btn_list.append([InlineKeyboardButton("⬅️ Back", callback_data="main_menu")])
    await callback.message.edit_reply_markup(
        reply_markup=InlineKeyboardMarkup(btn_list)
    )

  elif data == "main_menu":
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🎵 Audio Streams", callback_data="view_audio"
            ),
            InlineKeyboardButton("💬 Subtitle Streams", callback_data="view_sub"),
        ],
        [
            InlineKeyboardButton(
                "🚀 Remove Selected & Process", callback_data="process_file"
            )
        ],
    ])
    await callback.message.edit_text(
        "⚙️ **Stream Removal Configuration Menu**", reply_markup=buttons
    )

  elif data == "process_file":
    await callback.message.edit_text(
        "⚙️ **FFmpeg Processing Stream Removal...**"
    )
    await start_ffmpeg_process(client, callback.message, user_id)


# --- FFmpeg Exec & File Upload Function ---
async def start_ffmpeg_process(client, status_msg, user_id):
  udata = USER_DATA[user_id]
  in_file = udata["file_path"]
  out_file = f"clean_{udata['new_name']}"

  ffmpeg_cmd = ["ffmpeg", "-i", in_file, "-map", "0"]

  for a_idx in udata["remove_audio_indexes"]:
    ffmpeg_cmd.extend(["-map", f"-0:a:{a_idx}"])

  for s_idx in udata["remove_sub_indexes"]:
    ffmpeg_cmd.extend(["-map", f"-0:s:{s_idx}"])

  ffmpeg_cmd.extend(
      ["-metadata", f"title={udata['custom_metadata']}", "-c", "copy", out_file]
  )

  proc = await asyncio.create_subprocess_exec(*ffmpeg_cmd)
  await proc.communicate()

  thumb_path = f"thumb_{user_id}.jpg"
  thumb = thumb_path if os.path.exists(thumb_path) else None

  await status_msg.edit_text("📤 **Uploading Processed File...**")
  start_time = time.time()

  await client.send_document(
      chat_id=status_msg.chat.id,
      document=out_file,
      thumb=thumb,
      caption=f"✅ **Processed File:** `{udata['new_name']}`\n🏷️ **Title:** `{udata['custom_metadata']}`",
      progress=progress_func,
      progress_args=("📤 **Uploading File...**", status_msg, start_time),
  )

  await status_msg.delete()

  # Clean Up Storage
  for p in [in_file, out_file]:
    if os.path.exists(p):
      os.remove(p)


app.run()
    
  
