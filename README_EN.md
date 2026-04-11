# ChatBridge — Chat Translation Tool 🌉

A desktop tool that translates in-game chat in real time.
Translate your typed text with a single hotkey and send it instantly.

> 🌐 [日本語版](README.md)

## Features

- 🎮 **Hotkey Translation**: Press `Alt+J` to instantly translate selected/typed text
- 🌏 **Multi-language**: Supports translation between 9 languages including Japanese ⇔ English
- 🔄 **Overlay Display**: Shows translation results on top of your game screen (without stealing focus)
- ⚙️ **Settings Panel**: Customize hotkeys, translation direction, UI language, and more
- 🌐 **UI Localization**: Built-in Japanese/English UI, extensible via external JSON files
- 🛡️ **Admin Privileges**: Automatically manages privileges required for keyboard simulation in games
- 🚀 **Auto-Start**: Supports auto-start with admin privileges via Task Scheduler
- 🔒 **Single Instance**: Prevents duplicate instances across admin/standard privilege levels
- 💰 **Free**: Uses MyMemory Translation API (no API key required)

## Installation

Simply place `ChatBridge.exe` in any folder.
No installer required — it does not modify the registry or system folders.

```
📁 ChatBridge/
  ├── ChatBridge.exe
  └── config.json (auto-generated on first launch)
```

## Usage

### First Launch

1. Double-click `ChatBridge.exe` (or right-click → "Run as administrator")
2. Select your language (日本語 / English)
3. If admin privileges are required, an elevation dialog will appear automatically
4. You'll be asked whether to set up auto-start on Windows startup
5. A system tray icon will appear when it's running

### ⚠️ Administrator Privileges

When using ChatBridge with games that run with administrator privileges
(e.g., **Genshin Impact, Valorant, Apex Legends**),
ChatBridge must also be **run as administrator**.

If launched without admin privileges, you'll be automatically prompted to elevate.

> **Why?** Due to Windows security restrictions (UIPI),
> a standard-privilege app cannot detect key inputs in an elevated app.

### Translation

1. Type text in your game's chat box
2. Press `Alt+J`
3. The translation result appears in an overlay
4. `Enter` → Paste the translation / `Esc` → Cancel

### Settings

Right-click the system tray icon → "Open Settings"

| Setting | Description |
|---|---|
| Hotkey | Key to trigger translation (default: `Alt+J`) |
| Translation Direction | Source/target language pair |
| Overlay Position | Cursor position / Screen center / Top right |
| Overlay Opacity | 30% – 100% |
| Auto-Paste | Paste immediately without confirmation |
| Auto-Start | Auto-launch on Windows startup via Task Scheduler |
| UI Language | 日本語 / English |
| MyMemory Email | Register to increase daily limit to 50,000 characters |

## Auto-Start Setup

1. Right-click tray icon → "Open Settings"
2. Check "Launch on Windows startup"
3. Click "Yes" on the UAC prompt
4. ChatBridge will now auto-launch with admin privileges on Windows startup (no UAC shown)

> **How it works**: Uses Windows Task Scheduler.
> UAC confirmation is only required when registering the task.
> Subsequent auto-launches on startup will not show a UAC prompt.

## Uninstallation

1. Exit ChatBridge
2. If auto-start was enabled, **turn it off in Settings first**,
   or manually delete the `ChatBridge` task from Task Scheduler
3. Delete the ChatBridge folder — done!

> **Portable Design**: Except for the auto-start setting (Task Scheduler),
> ChatBridge does not create files or registry entries outside its folder.

## UI Localization

Japanese and English are built into the app.
To add other languages:

1. Create a `locales/` folder in the same directory as the app
2. Place JSON files like `locales/ko.json`
3. Select the new language in Settings

See the `_BUILTIN` dictionary in [i18n.py](i18n.py) for the JSON format reference.

## Tech Stack

- Python 3.12+
- PySide6 (Qt6) — UI & Overlay
- pynput — Hotkey detection & key simulation
- pystray — System tray
- MyMemory API — Translation engine
- PyInstaller — exe build

## License

MIT
