# ChatBridge — Chat Translation Tool 🌉

> 🌐 [日本語版](README.md)

A Windows desktop tool that translates in-game chat in real time.
Translate your typed text with a single hotkey and send it instantly.

### 💬 Why I Made This

After Genshin Impact introduced "Miliastra Wonderland," I found myself
communicating with players from around the world much more often.
But since I don't speak English, I was constantly switching to browser
translation sites or Alt+Tabbing to external translation apps just to
keep up with the conversation.

"Wouldn't it be great if I could translate without leaving the game screen?"

That's why I built ChatBridge.

> **⚠️ Disclaimer**
>
> ChatBridge was developed and tested primarily for use with **Genshin Impact**.
> It may work with other games or applications, but this is not guaranteed.
>
> This software is released under the **MIT License**.
> You are free to use, modify, and redistribute it,
> but **it comes with no warranty of any kind, and the developer assumes no
> liability for any issues arising from its use.**
> Use entirely **at your own risk**.

> **💡 Game Display Mode**
>
> ChatBridge's overlay works best in **Borderless Windowed** mode.
> In exclusive fullscreen mode, the overlay may not be visible.
> We recommend selecting "Borderless" or "Windowed" in your game's display settings.

Under the hood, it's simple: when you press the hotkey, it sends `Ctrl+A` → `Ctrl+C` to grab the chat text, translates it via the MyMemory API, and pastes the result with `Ctrl+V`. That's it.

> 📖 [Technical details (Specification)](SPEC.md)
>
> 🗺️ [Development Roadmap](ROADMAP.md)

## 📥 Download

You can download the latest version from the **GitHub Releases** page.

### 👉 [**Download Latest Version**](https://github.com/Leaf47/ChatBridge/releases)

> **💡 Tip**: Click `ChatBridge.exe` in the "Assets" section of the release page to start the download.

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

> **🛡️ Windows SmartScreen Warning**
>
> On first launch, you may see a "Windows protected your PC" warning.
> This is a standard warning for unsigned software from individual developers — it is not a virus.
>
> Click "**More info**" → then click "**Run anyway**" to proceed.
> (This warning will not appear again after the first launch.)

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
| MyMemory Email | Set an email address to increase daily translation limit (see below) |

### About MyMemory API

ChatBridge uses the **MyMemory API** (free) for translation.
No API key is required — it works out of the box.

| Condition | Daily Translation Limit |
|---|---|
| No email address set | 5,000 characters |
| Email address set | 50,000 characters |

You can set your email address in the "Translation" tab of the Settings panel.
This is a MyMemory API feature — including an email address in API requests
expands your daily usage quota.

## Auto-Start Setup

On first launch, you'll be asked whether to enable auto-start.
Selecting "Yes (Recommended)" will configure ChatBridge to launch
automatically when Windows starts.

To change this later:

1. Right-click tray icon → "Open Settings"
2. Toggle "Launch on Windows startup"
3. Save settings

> **How it works**: Uses Windows Task Scheduler to auto-launch with admin privileges.
> Once configured, subsequent auto-launches will not show a UAC (privilege confirmation) dialog.

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
