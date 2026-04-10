# ChatBridge — Chat Translation Tool 🌉

A desktop tool that translates in-game chat in real time.
Translate your typed text with a single hotkey and send it instantly.

## Features

- 🎮 **Hotkey Translation**: Press `Alt+J` to instantly translate selected/typed text
- 🌏 **Multi-language**: Supports translation between 9 languages including Japanese ⇔ English
- 🔄 **Overlay Display**: Shows translation results on top of your game screen
- ⚙️ **Settings Panel**: Customize hotkeys, translation direction, UI language, and more
- 🌐 **UI Localization**: Built-in Japanese/English UI, extensible via external JSON files
- 💰 **Free**: Uses MyMemory Translation API (no API key required)

## Installation

Simply place `ChatBridge.exe` in any folder.
No installer required — it does not modify the registry or system folders.

```
📁 ChatBridge/
  ├── ChatBridge.exe
  └── README.md
```

A `config.json` (settings file) will be automatically created in the same folder on first launch.

## Usage

### Launch

Double-click `ChatBridge.exe` to start.
A system tray icon will appear when it's running.

### ⚠️ Administrator Privileges (Important)

When using ChatBridge with games that run with administrator privileges
(e.g., **Genshin Impact, Valorant, Apex Legends**),
ChatBridge must also be **run as administrator**.

This is due to Windows security restrictions (UIPI) —
a standard-privilege app cannot detect key inputs in an elevated app.

**To manually run as administrator:**
1. Right-click `ChatBridge.exe`
2. Select "Run as administrator"
3. Click "Yes" on the UAC prompt

**To automatically run as administrator on startup:**
1. Launch ChatBridge (right-click → Run as administrator for the first time)
2. Right-click the system tray icon → "Open Settings"
3. Check "Launch on Windows startup"
4. Check "Run as administrator (required for games)"
5. Click "Yes" on the UAC prompt that appears
6. From now on, ChatBridge will auto-launch with admin privileges on Windows startup (no UAC prompt)

> **How it works**: Admin auto-start uses Windows Task Scheduler.
> UAC confirmation is only required when registering the task.
> Subsequent auto-launches on startup will not show a UAC prompt.
> Standard auto-start uses the Registry (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`).

### Translation

1. Activate the window containing the text you want to translate
2. Press `Alt+J` and release
3. The translation result appears in an overlay
4. `Enter` → Paste the translation / `Esc` → Cancel

### Settings

Right-click the system tray icon → "Open Settings"

## Uninstallation

1. Exit ChatBridge
2. If auto-start was enabled, **turn it off in Settings first**, or manually:
   - **Standard auto-start**: Remove `ChatBridge` from Registry `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
   - **Admin auto-start**: Delete the `ChatBridge` task from Task Scheduler
3. Delete the ChatBridge folder — done!

> **Portable Design**: Except for the auto-start settings mentioned above,
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
- PySide6 (Qt6) — UI
- pynput — Hotkey detection & key simulation
- pystray — System tray
- MyMemory API — Translation

## License

MIT
