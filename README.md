# 🤖 Advanced Telegram File Renamer & Stream Remover Bot

A powerful Pyrogram-based Telegram Bot to rename files, manage metadata, save custom thumbnails, and dynamically remove specific audio/subtitle streams using FFmpeg. Designed for easy deployment on **Railway** and other cloud platforms.

---

## ✨ Features

- ⚡ **Fast Stream Copying**: Removes unwanted streams without re-encoding, preserving video quality.
- 🎵 **Dynamic Stream Removal**: Detects audio and subtitle streams and lets you select tracks via interactive inline buttons (`❌ [REMOVE]` / `✅ [KEEP]`).
- 📊 **Real-time Progress Bar**: Displays live download and upload speed, progress percentage, transferred size, and ETA.
- 🖼️ **Custom Thumbnail Support**: Set permanent custom thumbnails for uploads using the `/thumb` command.
- 🏷️ **Custom Metadata**: Automatically injects custom metadata titles into output files.

---

## 🛠️ Repository Structure

```text
StreamRemoveBot/
├── bot.py           # Core bot execution script
├── config.py        # Environment variables loader
├── requirements.txt # Python dependencies
├── nixpacks.toml    # Railway system-level dependencies (FFmpeg setup)
└── Procfile         # Process manager file
# file-Renamer-Bot
