"""
ChatBridge 多言語対応モジュール（i18n）

日本語・英語はコード内に組み込み（exe 単体で動作可能）。
追加言語は locales/ フォルダに JSON ファイルを置くことで拡張可能。
"""

import json
import os
from typing import Dict, Optional

# ---------------------------------------------------------------------------
# 組み込み言語データ（日本語・英語）
# ---------------------------------------------------------------------------

_BUILTIN: Dict[str, Dict[str, str]] = {
    "ja": {
        "lang_name": "日本語",

        # --- アプリ全般 ---
        "app_name": "ChatBridge",
        "app_description": "チャット翻訳ツール",
        "starting": "ChatBridge を起動しています...",
        "engine_label": "翻訳エンジン",
        "hotkey_label": "ホットキー",
        "tray_notice": "システムトレイにアイコンが表示されます。",
        "exit_hint": "終了: トレイアイコン右クリック → 終了、または Ctrl+C",
        "shutting_down": "ChatBridge を終了します...",
        "shut_down": "ChatBridge を終了しました。",
        "paused": "一時停止",
        "resumed": "再開",
        "settings_updated": "設定を更新しました。エンジン: {engine}",
        "engine_changed": "翻訳エンジンを変更しました: {engine}",

        # --- トレイメニュー ---
        "tray_title": "ChatBridge - チャット翻訳ツール",
        "tray_title_paused": "ChatBridge - ⏸️ 一時停止中",
        "tray_settings": "⚙️ 設定を開く",
        "tray_engine": "🔄 翻訳エンジン: MyMemory",
        "tray_engine_mymemory": "MyMemory（無料）",
        "tray_engine_deepl": "DeepL（準備中）",
        "tray_engine_google": "Google（準備中）",
        "tray_pause": "⏸️ 一時停止",
        "tray_resume": "▶️ 再開",
        "tray_quit": "❌ 終了",

        # --- 設定画面 ---
        "settings_title": "ChatBridge - 設定",
        "settings_header": "⚙️ ChatBridge 設定",
        "tab_general": "一般",
        "tab_translator": "翻訳エンジン",
        "tab_overlay": "オーバーレイ",

        # 一般タブ
        "general_hotkey_group": "⌨️ ホットキー設定",
        "general_hotkey_label": "翻訳ホットキー:",
        "general_hotkey_hint": "例: alt+j, ctrl+shift+t, f2",
        "general_auto_paste": "翻訳結果を自動ペースト（確認なし）",
        "general_auto_start": "Windows 起動時に自動的に開く",
        "general_auto_start_hint": "※ タスクスケジューラを使用（管理者権限で自動起動）",
        "general_auto_start_admin_fail": "管理者権限での自動起動の登録に失敗しました。\nUACプロンプトで「はい」を選択してください。",
        "general_ui_lang_group": "🌐 表示言語",
        "general_ui_lang_label": "言語:",
        "general_ui_lang_hint": "※ 変更はアプリの再起動後に反映されます",

        # 翻訳エンジンタブ
        "translator_lang_group": "🌏 翻訳方向",
        "translator_source_label": "翻訳元:",
        "translator_target_label": "翻訳先:",
        "translator_swap": "🔄 入れ替え",
        "translator_mymemory_group": "📡 MyMemory 設定",
        "translator_email_label": "メールアドレス（任意）:",
        "translator_email_hint": "登録すると 1日50,000文字まで使用可能（未登録: 5,000文字）",
        "translator_email_placeholder": "your@email.com",
        "translator_test": "🧪 接続テスト",
        "translator_test_success": "✅ 接続成功！\n\n翻訳テスト: {source} → {result}\n{email_status}",
        "translator_test_fail": "❌ 接続エラー:\n{error}",
        "translator_future_group": "🔄 翻訳エンジン（将来の拡張）",
        "translator_engine_label": "エンジン:",
        "translator_future_hint": "🔒 DeepL / Google への切り替えは将来のアップデートで対応予定です。",
        "translator_future_placeholder": "将来のアップデートで有効化予定",

        # オーバーレイタブ
        "overlay_opacity_group": "🎨 表示設定",
        "overlay_opacity_label": "不透明度:",
        "overlay_position_group": "📍 表示位置",
        "overlay_position_cursor": "カーソル位置",
        "overlay_position_center": "画面中央",
        "overlay_position_top_right": "右上",

        # 初回起動ダイアログ
        "first_launch_title": "初回セットアップ",
        "first_launch_text": "🎉 ChatBridge へようこそ！",
        "first_launch_detail": "Windows 起動時に管理者権限で自動起動するように設定しますか？\n（タスクスケジューラを使用）",
        "first_launch_yes": "✅ はい（推奨）",
        "first_launch_later": "後で設定する",
        "first_launch_success": "管理者権限での自動起動を登録しました。\n次回のWindows起動時から自動で起動します。",

        # 管理者権限チェックダイアログ
        "admin_required_title": "⚠️ 管理者権限が必要です",
        "admin_required_detail": "ChatBridge はゲーム上でのキー入力シミュレーションのために\n管理者権限での実行が必要です。\n\n管理者権限で再起動しますか？",
        "admin_required_relaunch": "🔄 管理者権限で再起動",
        "admin_required_quit": "❌ 終了",

        # 保存・キャンセル
        "save": "💾 保存",
        "cancel": "キャンセル",
        "save_success": "設定を保存しました。",
        "save_fail": "設定の保存に失敗しました: {error}",
        "lang_changed_restart": "表示言語が変更されました。\n変更を完全に反映するには、アプリを再起動してください。",

        # --- オーバーレイ ---
        "overlay_loading": "翻訳中...",
        "overlay_confirm": "Enter: 確定",
        "overlay_cancel": "Esc: キャンセル",

        # --- 言語名（ドロップダウン用） ---
        "lang_ja": "日本語",
        "lang_en": "英語",
        "lang_zh": "中国語",
        "lang_ko": "韓国語",
        "lang_fr": "フランス語",
        "lang_de": "ドイツ語",
        "lang_es": "スペイン語",
        "lang_pt": "ポルトガル語",
        "lang_ru": "ロシア語",
    },

    "en": {
        "lang_name": "English",

        # --- App General ---
        "app_name": "ChatBridge",
        "app_description": "Chat Translation Tool",
        "starting": "Starting ChatBridge...",
        "engine_label": "Translation Engine",
        "hotkey_label": "Hotkey",
        "tray_notice": "Icon is displayed in the system tray.",
        "exit_hint": "Exit: Right-click tray icon → Exit, or Ctrl+C",
        "shutting_down": "Shutting down ChatBridge...",
        "shut_down": "ChatBridge has been closed.",
        "paused": "Paused",
        "resumed": "Resumed",
        "settings_updated": "Settings updated. Engine: {engine}",
        "engine_changed": "Translation engine changed: {engine}",

        # --- Tray Menu ---
        "tray_title": "ChatBridge - Chat Translation Tool",
        "tray_title_paused": "ChatBridge - ⏸️ Paused",
        "tray_settings": "⚙️ Open Settings",
        "tray_engine": "🔄 Translation Engine: MyMemory",
        "tray_engine_mymemory": "MyMemory (Free)",
        "tray_engine_deepl": "DeepL (Coming Soon)",
        "tray_engine_google": "Google (Coming Soon)",
        "tray_pause": "⏸️ Pause",
        "tray_resume": "▶️ Resume",
        "tray_quit": "❌ Quit",

        # --- Settings Window ---
        "settings_title": "ChatBridge - Settings",
        "settings_header": "⚙️ ChatBridge Settings",
        "tab_general": "General",
        "tab_translator": "Translation",
        "tab_overlay": "Overlay",

        # General Tab
        "general_hotkey_group": "⌨️ Hotkey Settings",
        "general_hotkey_label": "Translation Hotkey:",
        "general_hotkey_hint": "e.g. alt+j, ctrl+shift+t, f2",
        "general_auto_paste": "Auto-paste translation (no confirmation)",
        "general_auto_start": "Launch on Windows startup",
        "general_auto_start_hint": "* Uses Task Scheduler (auto-start with admin privileges)",
        "general_auto_start_admin_fail": "Failed to register admin auto-start.\nPlease select 'Yes' in the UAC prompt.",
        "general_ui_lang_group": "🌐 Display Language",
        "general_ui_lang_label": "Language:",
        "general_ui_lang_hint": "※ Changes take effect after restarting the app",

        # Translation Tab
        "translator_lang_group": "🌏 Translation Direction",
        "translator_source_label": "Source:",
        "translator_target_label": "Target:",
        "translator_swap": "🔄 Swap",
        "translator_mymemory_group": "📡 MyMemory Settings",
        "translator_email_label": "Email (optional):",
        "translator_email_hint": "Register to increase daily limit to 50,000 chars (default: 5,000)",
        "translator_email_placeholder": "your@email.com",
        "translator_test": "🧪 Test Connection",
        "translator_test_success": "✅ Connection successful!\n\nTranslation test: {source} → {result}\n{email_status}",
        "translator_test_fail": "❌ Connection error:\n{error}",
        "translator_future_group": "🔄 Translation Engines (Future)",
        "translator_engine_label": "Engine:",
        "translator_future_hint": "🔒 DeepL / Google support is planned for future updates.",
        "translator_future_placeholder": "Available in future updates",

        # Overlay Tab
        "overlay_opacity_group": "🎨 Display Settings",
        "overlay_opacity_label": "Opacity:",
        "overlay_position_group": "📍 Position",
        "overlay_position_cursor": "Cursor Position",
        "overlay_position_center": "Screen Center",
        "overlay_position_top_right": "Top Right",

        # First Launch Dialog
        "first_launch_title": "First-Time Setup",
        "first_launch_text": "🎉 Welcome to ChatBridge!",
        "first_launch_detail": "Would you like to set up auto-start with administrator privileges on Windows startup?\n(Uses Task Scheduler)",
        "first_launch_yes": "✅ Yes (Recommended)",
        "first_launch_later": "Set up later",
        "first_launch_success": "Admin auto-start has been registered.\nChatBridge will auto-launch on next Windows startup.",

        # Admin Required Dialog
        "admin_required_title": "⚠️ Administrator Privileges Required",
        "admin_required_detail": "ChatBridge requires administrator privileges\nfor keyboard input simulation in games.\n\nWould you like to restart with administrator privileges?",
        "admin_required_relaunch": "🔄 Restart as Administrator",
        "admin_required_quit": "❌ Quit",

        # Save / Cancel
        "save": "💾 Save",
        "cancel": "Cancel",
        "save_success": "Settings saved.",
        "save_fail": "Failed to save settings: {error}",
        "lang_changed_restart": "Display language has been changed.\nPlease restart the app to fully apply the change.",

        # --- Overlay ---
        "overlay_loading": "Translating...",
        "overlay_confirm": "Enter: Confirm",
        "overlay_cancel": "Esc: Cancel",

        # --- Language Names (for dropdowns) ---
        "lang_ja": "Japanese",
        "lang_en": "English",
        "lang_zh": "Chinese",
        "lang_ko": "Korean",
        "lang_fr": "French",
        "lang_de": "German",
        "lang_es": "Spanish",
        "lang_pt": "Portuguese",
        "lang_ru": "Russian",
    },
}

# ---------------------------------------------------------------------------
# 現在の言語と文字列キャッシュ
# ---------------------------------------------------------------------------

_current_lang: str = "ja"
_strings: Dict[str, str] = {}


def init(lang: str = "ja") -> None:
    """
    i18n を初期化する。

    1. 組み込みの日本語をベースにロード（フォールバック）
    2. 指定された言語の組み込みデータで上書き
    3. locales/ フォルダに外部 JSON があればさらに上書き
    """
    global _current_lang, _strings

    _current_lang = lang

    # ベース: 日本語（フォールバック）
    _strings = dict(_BUILTIN["ja"])

    # 指定言語の組み込みデータで上書き
    if lang in _BUILTIN and lang != "ja":
        _strings.update(_BUILTIN[lang])

    # 外部 JSON ファイルで上書き（カスタマイズ・追加言語対応）
    locale_file = _get_locale_path(lang)
    if locale_file and os.path.isfile(locale_file):
        try:
            with open(locale_file, "r", encoding="utf-8") as f:
                external = json.load(f)
            _strings.update(external)
        except (json.JSONDecodeError, OSError):
            pass  # 読み込み失敗時は組み込みを使用


def t(key: str, **kwargs) -> str:
    """
    翻訳文字列を取得する。

    Args:
        key: 文字列キー（例: "tray_quit"）
        **kwargs: フォーマット用のパラメータ（例: engine="MyMemory"）

    Returns:
        翻訳された文字列。キーが見つからない場合はキー自体を返す。
    """
    text = _strings.get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return text


def get_available_languages() -> list[tuple[str, str]]:
    """
    利用可能な言語の一覧を返す。
    (言語コード, 表示名) のタプルのリスト。

    組み込み言語 + locales/ フォルダ内の外部JSONを自動検出。
    """
    languages = {}

    # 組み込み言語
    for code, data in _BUILTIN.items():
        languages[code] = data.get("lang_name", code)

    # 外部 locales/ フォルダ
    locales_dir = _get_locales_dir()
    if locales_dir and os.path.isdir(locales_dir):
        for filename in os.listdir(locales_dir):
            if filename.endswith(".json"):
                code = filename[:-5]  # "ko.json" → "ko"
                if code not in languages:
                    try:
                        filepath = os.path.join(locales_dir, filename)
                        with open(filepath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        languages[code] = data.get("lang_name", code)
                    except (json.JSONDecodeError, OSError):
                        languages[code] = code

    return sorted(languages.items(), key=lambda x: x[0])


def current_lang() -> str:
    """現在の言語コードを返す"""
    return _current_lang


def _get_locales_dir() -> Optional[str]:
    """locales/ フォルダのパスを取得する"""
    # スクリプトと同じディレクトリの locales/
    base = os.path.dirname(os.path.abspath(__file__))
    locales = os.path.join(base, "locales")
    return locales


def _get_locale_path(lang: str) -> Optional[str]:
    """指定言語の JSON ファイルパスを返す"""
    locales_dir = _get_locales_dir()
    if locales_dir:
        return os.path.join(locales_dir, f"{lang}.json")
    return None
