import asyncio
import os
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


# Start Command
@app.on_message(filters.command("start"))
async def start_handler(client, message):
  await message.reply_text(
      f"👋 **Vanakkam {message.from_user.first_name}!**\n\n"
      "Enakku edhavadhu File, Video, or Audio send pannunga. "
      "Rename, Thumbnail, Stream Removal, & Metadata options irukku."
  )


# Set Thumbnail Command
@app.on_message(filters.command("thumb") | (filters.private & filters.photo))
async def save_thumb(client, message):
  user_id = message.from_user.id
  thumb_path = f"thumb_{user_id}.jpg"

  if message.photo:
    await message.download(file_name=thumb_path)
    await message.reply_text("✅ **Custom Thumbnail Saved!**")
  else:
    await message.reply_text("📷 Photo reply/send panni thumbnail save panna.")


# Catch Media & Show Interactive Menu
@app.on_message(filters.private & (filters.document | filters.video))
async def media_handler(client, message):
  user_id = message.from_user.id
  file_name = message.document.file_name if message.document else message.video.file_name

  USER_DATA[user_id] = {
      "message": message,
      "original_name": file_name,
      "new_name": file_name,
      "remove_audio": False,
      "remove_sub": False,
      "custom_metadata": f"Encoded By @{client.me.username}",
  }

  buttons = InlineKeyboardMarkup([
      [
          InlineKeyboardButton("✏️ Rename File", callback_data="btn_rename"),
          InlineKeyboardButton(
              "🎬 Remove Streams", callback_data="btn_streams"
          ),
      ],
      [
          InlineKeyboardButton("🏷️ Metadata", callback_data="btn_metadata"),
          InlineKeyboardButton("🚀 Start Process", callback_data="btn_process"),
      ],
  ])

  await message.reply_text(
      f"📂 **File Received:** `{file_name}`\n\nKeazhe irukura options use panni modify pannunga:",
      reply_markup=buttons,
  )


# Callback Query Handler for Buttons
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
      title = track.get("tags", {}).get("title", "Audio")
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

    # Refresh audio menu view
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

    # Refresh sub menu view
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
      
