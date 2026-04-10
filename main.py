"""
JA2EN — ゲーム内日本語→英語翻訳ツール

メインエントリーポイント。
すべてのコンポーネントを初期化し、アプリケーションのイベントループを開始する。
"""

import sys
import signal
import threading
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, Qt, Slot

from config import Config
from translator import create_translator, TranslationError
from hotkey_manager import HotkeyManager
from clipboard_handler import ClipboardHandler
from overlay import TranslationOverlay
from settings_ui import SettingsWindow
from tray_app import TrayApp


class JA2ENApp:
    """JA2EN アプリケーションのメインクラス"""

    def __init__(self):
        # Qt アプリケーション
        self._app = QApplication(sys.argv)
        self._app.setQuitOnLastWindowClosed(False)  # トレイアプリなのでウィンドウを閉じても終了しない

        # 設定の読み込み
        self._config = Config()

        # 翻訳エンジンの初期化
        self._translator = self._create_translator()

        # クリップボードハンドラ
        self._clipboard = ClipboardHandler()

        # オーバーレイウィンドウ
        self._overlay = TranslationOverlay(
            opacity=self._config.get("overlay_opacity", 0.9),
            position=self._config.get("overlay_position", "cursor"),
        )
        self._overlay.confirmed.connect(self._on_translation_confirmed)
        self._overlay.cancelled.connect(self._on_translation_cancelled)

        # 設定画面
        self._settings_window = SettingsWindow(self._config)
        self._settings_window.settings_changed.connect(self._on_settings_changed)

        # ホットキーマネージャー
        self._hotkey_manager = HotkeyManager()
        self._hotkey_manager.register(
            self._config.get("hotkey_translate", "ctrl+j"),
            self._on_translate_hotkey,
        )

        # システムトレイ
        self._tray = TrayApp(
            on_settings=self._show_settings,
            on_toggle_pause=self._on_toggle_pause,
            on_quit=self._quit,
            on_engine_change=self._on_engine_change_from_tray,
            current_engine=self._config.get("translator", "mymemory"),
        )

    def _create_translator(self):
        """設定に基づいて翻訳エンジンを作成する"""
        engine_name = self._config.get("translator", "mymemory")
        api_keys = self._config.get("api_keys", {})
        mymemory_email = self._config.get("mymemory_email", "")
        return create_translator(engine_name, api_keys, mymemory_email=mymemory_email)

    def run(self) -> int:
        """アプリケーションを開始する"""
        print("JA2EN を起動しています...")
        print(f"翻訳エンジン: {self._translator.name()}")
        print(f"ホットキー: {self._config.get('hotkey_translate', 'ctrl+j')}")
        print("システムトレイにアイコンが表示されます。")
        print("終了: トレイアイコン右クリック → 終了、または Ctrl+C")

        # Ctrl+C (SIGINT) で終了できるようにする
        signal.signal(signal.SIGINT, lambda *args: self._quit())

        # Qt イベントループは C++ で動くため、Python のシグナルが届かない。
        # 定期的に Python に制御を戻すタイマーを追加する。
        self._signal_timer = QTimer()
        self._signal_timer.timeout.connect(lambda: None)  # Python に制御を戻すだけ
        self._signal_timer.start(200)  # 200msごと

        # ホットキーリスナーを開始
        self._hotkey_manager.start()

        # トレイアイコンを表示
        self._tray.start()

        # Qt イベントループを開始
        return self._app.exec()

    def _on_translate_hotkey(self) -> None:
        """翻訳ホットキーが押されたときの処理（別スレッドから呼ばれる）"""
        # クリップボードからテキストを取得
        text = self._clipboard.grab_text()
        if not text:
            return

        # オーバーレイにローディングを表示（UIスレッドで実行）
        QTimer.singleShot(0, lambda: self._overlay.show_loading(text, self._translator.name()))

        # 翻訳を実行（現在のスレッドで実行=別スレッド）
        try:
            translated = self._translator.translate(text, source="ja", target="en")
        except TranslationError as e:
            # エラー時はエラーメッセージをオーバーレイに表示
            QTimer.singleShot(
                0,
                lambda: self._overlay.show_translation(text, f"⚠️ {e}", self._translator.name()),
            )
            return

        # auto_paste が有効なら確認なしでペースト
        if self._config.get("auto_paste", False):
            self._clipboard.paste_text(translated)
            return

        # 翻訳結果をオーバーレイに表示（UIスレッドで実行）
        QTimer.singleShot(
            0,
            lambda: self._overlay.show_translation(text, translated, self._translator.name()),
        )

    @Slot(str)
    def _on_translation_confirmed(self, translated_text: str) -> None:
        """翻訳結果が確定されたとき（Enter押下）"""
        self._clipboard.paste_text(translated_text)

    @Slot()
    def _on_translation_cancelled(self) -> None:
        """翻訳がキャンセルされたとき（Esc押下）"""
        self._clipboard.restore_original()

    def _show_settings(self) -> None:
        """設定画面を表示する（UIスレッドで実行する必要がある）"""
        QTimer.singleShot(0, self._settings_window.show)

    def _on_settings_changed(self) -> None:
        """設定が変更されたときの処理"""
        # 翻訳エンジンを再作成
        self._translator = self._create_translator()

        # ホットキーを更新
        self._hotkey_manager.stop()
        self._hotkey_manager = HotkeyManager()
        self._hotkey_manager.register(
            self._config.get("hotkey_translate", "ctrl+j"),
            self._on_translate_hotkey,
        )
        self._hotkey_manager.start()

        # オーバーレイの設定を更新
        self._overlay.update_settings(
            opacity=self._config.get("overlay_opacity", 0.9),
            position=self._config.get("overlay_position", "cursor"),
        )

        # トレイのエンジン表示を更新
        self._tray.update_engine(self._config.get("translator", "mymemory"))

        print(f"設定を更新しました。エンジン: {self._translator.name()}")

    def _on_toggle_pause(self, paused: bool) -> None:
        """一時停止/再開の切り替え"""
        self._hotkey_manager.set_enabled(not paused)
        status = "一時停止" if paused else "再開"
        print(f"JA2EN: {status}")

    def _on_engine_change_from_tray(self, engine_name: str) -> None:
        """トレイメニューからエンジンが変更されたとき"""
        self._config.set("translator", engine_name)
        self._config.save()
        self._translator = self._create_translator()
        print(f"翻訳エンジンを変更しました: {self._translator.name()}")

    def _quit(self) -> None:
        """アプリケーションを終了する"""
        print("JA2EN を終了します...")
        self._hotkey_manager.stop()
        self._tray.stop()
        self._app.quit()


def main():
    """エントリーポイント"""
    try:
        app = JA2ENApp()
        sys.exit(app.run())
    except KeyboardInterrupt:
        print("\nJA2EN を終了しました。")
        sys.exit(0)


if __name__ == "__main__":
    main()
