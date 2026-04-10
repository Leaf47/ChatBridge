"""
ChatBridge — チャット翻訳ツール

メインエントリーポイント。
すべてのコンポーネントを初期化し、アプリケーションのイベントループを開始する。
"""

import sys
import os
import signal
import threading
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer, Qt, Slot, Signal, QObject

from config import Config
import i18n
from i18n import t
from translator import create_translator, TranslationError
from hotkey_manager import HotkeyManager
from clipboard_handler import ClipboardHandler
from overlay import TranslationOverlay
from settings_ui import SettingsWindow, _set_auto_start_admin
from tray_app import TrayApp


class UIBridge(QObject):
    """
    別スレッドから安全にUIを操作するためのブリッジ。
    シグナルは Qt が自動的にメインスレッドにディスパッチしてくれる。
    """
    show_settings_signal = Signal()
    show_overlay_loading = Signal(str, str, str)        # original, engine_name, source_lang
    show_overlay_result = Signal(str, str, str, str, str)    # original, translated, engine_name, source_lang, target_lang
    quit_signal = Signal()


class ChatBridgeApp:
    """ChatBridge アプリケーションのメインクラス"""

    def __init__(self):
        # Qt アプリケーション
        self._app = QApplication(sys.argv)
        self._app.setQuitOnLastWindowClosed(False)

        # 設定の読み込み
        self._config = Config()

        # i18n 初期化（設定の ui_lang に基づく）
        i18n.init(self._config.get("ui_lang", "ja"))

        # 翻訳エンジンの初期化
        self._translator = self._create_translator()

        # クリップボードハンドラ
        self._clipboard = ClipboardHandler()

        # UIブリッジ（別スレッド→メインスレッドの安全な通信）
        self._bridge = UIBridge()

        # オーバーレイウィンドウ
        self._overlay = TranslationOverlay(
            opacity=self._config.get("overlay_opacity", 0.9),
            position=self._config.get("overlay_position", "cursor"),
        )
        self._overlay.confirmed.connect(self._on_translation_confirmed)
        self._overlay.cancelled.connect(self._on_translation_cancelled)

        # UIブリッジのシグナルをオーバーレイに接続
        self._bridge.show_overlay_loading.connect(self._overlay.show_loading)
        self._bridge.show_overlay_result.connect(self._overlay.show_translation)

        # 設定画面
        self._settings_window = SettingsWindow(self._config)
        self._settings_window.settings_changed.connect(self._on_settings_changed)
        self._bridge.show_settings_signal.connect(self._settings_window.show)
        self._bridge.quit_signal.connect(self._do_quit)

        # ホットキーマネージャー
        self._hotkey_manager = HotkeyManager()
        self._hotkey_manager.register(
            self._config.get("hotkey_translate", "alt+j"),
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
        print(t("starting"))
        print(f"{t('engine_label')}: {self._translator.name()}")
        print(f"{t('hotkey_label')}: {self._config.get('hotkey_translate', 'alt+j')}")
        print(t("tray_notice"))
        print(t("exit_hint"))

        # 初回起動時にセットアップダイアログを表示
        if self._config.is_first_launch:
            QTimer.singleShot(500, self._show_first_launch_dialog)

        # Ctrl+C (SIGINT) で終了できるようにする
        signal.signal(signal.SIGINT, lambda *args: self._quit())

        # Qt イベントループは C++ で動くため、Python のシグナルが届かない。
        self._signal_timer = QTimer()
        self._signal_timer.timeout.connect(lambda: None)
        self._signal_timer.start(200)

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

        # 設定から言語ペアを取得
        source = self._config.get("source_lang", "ja")
        target = self._config.get("target_lang", "en")

        # オーバーレイにローディングを表示（シグナル経由でUIスレッドへ）
        self._bridge.show_overlay_loading.emit(text, self._translator.name(), source)

        # 翻訳を実行（現在のスレッドで実行=別スレッド）
        try:
            translated = self._translator.translate(text, source=source, target=target)
        except TranslationError as e:
            self._bridge.show_overlay_result.emit(text, f"⚠️ {e}", self._translator.name(), source, target)
            return
        except Exception as e:
            self._bridge.show_overlay_result.emit(text, f"⚠️ {e}", self._translator.name(), source, target)
            return

        # auto_paste が有効なら確認なしでペースト
        if self._config.get("auto_paste", False):
            self._clipboard.paste_text(translated)
            return

        # 翻訳結果をオーバーレイに表示（シグナル経由でUIスレッドへ）
        self._bridge.show_overlay_result.emit(text, translated, self._translator.name(), source, target)

    @Slot(str)
    def _on_translation_confirmed(self, translated_text: str) -> None:
        """翻訳結果が確定されたとき（Enter押下）"""
        threading.Thread(
            target=self._clipboard.paste_text,
            args=(translated_text,),
            daemon=True,
        ).start()

    @Slot()
    def _on_translation_cancelled(self) -> None:
        """翻訳がキャンセルされたとき（Esc押下）"""
        self._clipboard.restore_original()

    def _show_first_launch_dialog(self) -> None:
        """初回起動時のセットアップダイアログを表示する"""
        msg = QMessageBox()
        msg.setWindowTitle("ChatBridge — " + t("first_launch_title"))
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(t("first_launch_text"))
        msg.setInformativeText(t("first_launch_detail"))
        msg.setWindowFlags(msg.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        # ボタン
        yes_btn = msg.addButton(t("first_launch_yes"), QMessageBox.ButtonRole.AcceptRole)
        no_btn = msg.addButton(t("first_launch_later"), QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(yes_btn)

        msg.exec()

        if msg.clickedButton() == yes_btn:
            # タスクスケジューラに管理者権限自動起動を登録
            success = _set_auto_start_admin(True)
            if success:
                self._config.set("auto_start", True)
                self._config.set("auto_start_admin", True)
                self._config.save()
                # 管理者権限で再起動するか確認
                restart_msg = QMessageBox()
                restart_msg.setWindowTitle("ChatBridge")
                restart_msg.setIcon(QMessageBox.Icon.Question)
                restart_msg.setText(t("first_launch_success"))
                restart_msg.setInformativeText(t("first_launch_restart"))
                restart_msg.setWindowFlags(
                    restart_msg.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
                )
                restart_yes = restart_msg.addButton(
                    t("first_launch_restart_yes"), QMessageBox.ButtonRole.AcceptRole
                )
                restart_no = restart_msg.addButton(
                    t("first_launch_restart_no"), QMessageBox.ButtonRole.RejectRole
                )
                restart_msg.setDefaultButton(restart_yes)
                restart_msg.exec()

                if restart_msg.clickedButton() == restart_yes:
                    self._relaunch_as_admin()
            else:
                QMessageBox.warning(
                    None, "⚠️ ChatBridge",
                    t("general_auto_start_admin_fail"),
                )

    def _relaunch_as_admin(self) -> None:
        """管理者権限でアプリを再起動し、現プロセスを終了する"""
        import ctypes
        if getattr(sys, 'frozen', False):
            # exe の場合（--noconsole でビルドしていればコンソール不要）
            exe = sys.executable
            params = ""
        else:
            # 開発時: pythonw.exe を使ってコンソールウィンドウを出さない
            exe = sys.executable.replace("python.exe", "pythonw.exe")
            script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
            params = f'"{script}"'

        # ShellExecuteW で管理者昇格して起動（UACプロンプト表示）
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", exe, params, None, 1  # 1 = SW_SHOWNORMAL
        )
        # 現プロセスを終了
        self._do_quit()

    def _show_settings(self) -> None:
        """設定画面を表示する（シグナル経由でUIスレッドで実行）"""
        self._bridge.show_settings_signal.emit()

    def _on_settings_changed(self) -> None:
        """設定が変更されたときの処理"""
        # i18n を再初期化
        i18n.init(self._config.get("ui_lang", "ja"))

        # 翻訳エンジンを再作成
        self._translator = self._create_translator()

        # ホットキーを更新
        self._hotkey_manager.stop()
        self._hotkey_manager = HotkeyManager()
        self._hotkey_manager.register(
            self._config.get("hotkey_translate", "alt+j"),
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

        print(t("settings_updated", engine=self._translator.name()))

    def _on_toggle_pause(self, paused: bool) -> None:
        """一時停止/再開の切り替え"""
        self._hotkey_manager.set_enabled(not paused)
        status = t("paused") if paused else t("resumed")
        print(f"ChatBridge: {status}")

    def _on_engine_change_from_tray(self, engine_name: str) -> None:
        """トレイメニューからエンジンが変更されたとき"""
        self._config.set("translator", engine_name)
        self._config.save()
        self._translator = self._create_translator()
        print(t("engine_changed", engine=self._translator.name()))

    def _quit(self) -> None:
        """アプリケーションを終了する（どのスレッドからも呼べる）"""
        self._bridge.quit_signal.emit()

    @Slot()
    def _do_quit(self) -> None:
        """実際の終了処理（UIスレッドで実行される）"""
        print(t("shutting_down"))
        self._hotkey_manager.stop()
        self._tray.stop()
        self._app.quit()


def main():
    """エントリーポイント"""
    try:
        app = ChatBridgeApp()
        sys.exit(app.run())
    except KeyboardInterrupt:
        print(f"\n{t('shut_down')}")
        sys.exit(0)


if __name__ == "__main__":
    main()
