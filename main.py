"""
ChatBridge — チャット翻訳ツール

メインエントリーポイント。
すべてのコンポーネントを初期化し、アプリケーションのイベントループを開始する。
管理者権限での実行が必須（ゲーム上でのキー入力シミュレーションに必要）。
"""

import sys
import os
import signal
import ctypes
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


def _is_admin() -> bool:
    """現在のプロセスが管理者権限で実行されているかチェックする"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def _relaunch_as_admin() -> None:
    """管理者権限でアプリを再起動する（UACプロンプト表示）"""
    if getattr(sys, 'frozen', False):
        # exe の場合
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

    def __init__(self, app: QApplication, config: Config):
        # Qt アプリケーション（main() で作成済みのインスタンスを使用）
        self._app = app
        self._app.setQuitOnLastWindowClosed(False)

        # 設定（main() で読み込み済み）
        self._config = config

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
        self._hotkey_manager.set_overlay(self._overlay)  # オーバーレイの Enter/Esc 処理を統合
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

        # 初回起動時に自動起動登録ダイアログを表示
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
        """初回起動時のセットアップダイアログを表示する（自動起動登録のみ）"""
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
                QMessageBox.information(
                    None, "✅ ChatBridge",
                    t("first_launch_success"),
                )
            else:
                QMessageBox.warning(
                    None, "⚠️ ChatBridge",
                    t("general_auto_start_admin_fail"),
                )

        # ダイアログ表示後（Yes/No どちらでも）セットアップ完了とする
        self._config.set("setup_complete", True)
        self._config.save()

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
        self._hotkey_manager.set_overlay(self._overlay)  # オーバーレイの参照を引き継ぐ
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


def _create_global_mutex():
    """
    全権限レベルからアクセス可能な名前付きMutexを作成する。

    管理者権限で作成したMutexは、デフォルトでは通常権限プロセスから
    アクセスできない（ERROR_ACCESS_DENIED）。NULL DACL を設定した
    SECURITY_ATTRIBUTES を使うことで、全権限レベルからアクセス可能にする。

    Returns:
        tuple: (mutex_handle, already_exists)
            - mutex_handle: Mutexのハンドル（0の場合は作成失敗）
            - already_exists: 既に同名のMutexが存在する場合True
    """
    # SECURITY_ATTRIBUTES 構造体を定義
    class SECURITY_ATTRIBUTES(ctypes.Structure):
        _fields_ = [
            ("nLength", ctypes.c_ulong),
            ("lpSecurityDescriptor", ctypes.c_void_p),
            ("bInheritHandle", ctypes.c_int),
        ]

    _advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    # NULL DACL のセキュリティ記述子を作成
    # これにより全ユーザー・全権限レベルからアクセス可能になる
    sd = ctypes.c_buffer(64)  # SECURITY_DESCRIPTOR バッファ
    _advapi32.InitializeSecurityDescriptor(ctypes.byref(sd), 1)  # SECURITY_DESCRIPTOR_REVISION = 1
    # NULL DACL を設定（第2引数=True: DACLあり, 第3引数=None: NULL DACL, 第4引数=False: デフォルト）
    _advapi32.SetSecurityDescriptorDacl(ctypes.byref(sd), True, None, False)

    sa = SECURITY_ATTRIBUTES()
    sa.nLength = ctypes.sizeof(SECURITY_ATTRIBUTES)
    sa.lpSecurityDescriptor = ctypes.addressof(sd)
    sa.bInheritHandle = False

    mutex_name = "Global\\ChatBridge_SingleInstance_Mutex"
    mutex = _kernel32.CreateMutexW(ctypes.byref(sa), False, mutex_name)
    last_error = ctypes.get_last_error()

    # ERROR_ALREADY_EXISTS (183): 同じ名前のMutexが既に存在する
    # ERROR_ACCESS_DENIED (5): 権限不足でアクセスできない（=別権限で起動中）
    already_exists = (last_error == 183) or (mutex == 0 and last_error == 5)

    return mutex, already_exists


def main():
    """エントリーポイント"""
    # --- 多重起動防止 ---
    # Windows の名前付き Mutex を使用して、同じアプリの2重起動を防ぐ。
    # Global\ プレフィックスで管理者/通常権限の両方から見えるようにする。
    # NULL DACL で全権限レベルからアクセス可能にする。
    _mutex_handle, already_running = _create_global_mutex()

    if already_running:
        # 既に起動中 → 簡易ダイアログを表示して終了
        print("ChatBridge: already running, showing notification...")
        app = QApplication(sys.argv)
        i18n.init("ja")
        try:
            config = Config()
            i18n.init(config.get("ui_lang", "ja"))
        except Exception:
            pass
        msg = QMessageBox()
        msg.setWindowTitle("ChatBridge")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(t("already_running"))
        # ゲーム等の全画面アプリの背後に隠れないよう最前面に表示
        msg.setWindowFlags(msg.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        msg.exec()
        sys.exit(0)

    # 最低限の Qt を初期化
    app = QApplication(sys.argv)

    # 設定の読み込み（config.json がなければ作成される）
    try:
        config = Config()
    except Exception:
        config = None

    # i18n を初期化
    ui_lang = config.get("ui_lang", "ja") if config else "ja"
    i18n.init(ui_lang)

    # --- 初回起動: 言語選択 ---
    # lang_selected が False のときは、管理者チェックより先に言語を決める。
    # こうすることで管理者チェックのダイアログも正しい言語で表示できる。
    if config and not config.get("lang_selected", False):
        lang_msg = QMessageBox()
        lang_msg.setWindowTitle("ChatBridge — Language / 言語")
        lang_msg.setIcon(QMessageBox.Icon.Question)
        lang_msg.setText("🌐 Select your language / 言語を選択してください")
        lang_msg.setWindowFlags(
            lang_msg.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
        )

        ja_btn = lang_msg.addButton("日本語", QMessageBox.ButtonRole.AcceptRole)
        en_btn = lang_msg.addButton("English", QMessageBox.ButtonRole.AcceptRole)
        lang_msg.setDefaultButton(ja_btn)

        lang_msg.exec()

        if lang_msg.clickedButton() == en_btn:
            chosen_lang = "en"
        else:
            chosen_lang = "ja"

        # 選択した言語を保存して i18n を再初期化
        config.set("ui_lang", chosen_lang)
        config.set("lang_selected", True)
        config.save()
        i18n.init(chosen_lang)

    # --- 管理者権限チェック ---
    if not _is_admin():
        msg = QMessageBox()
        msg.setWindowTitle("ChatBridge")
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText(t("admin_required_title"))
        msg.setInformativeText(t("admin_required_detail"))
        msg.setWindowFlags(msg.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        relaunch_btn = msg.addButton(
            t("admin_required_relaunch"), QMessageBox.ButtonRole.AcceptRole
        )
        quit_btn = msg.addButton(
            t("admin_required_quit"), QMessageBox.ButtonRole.RejectRole
        )
        msg.setDefaultButton(relaunch_btn)

        msg.exec()

        if msg.clickedButton() == relaunch_btn:
            _relaunch_as_admin()

        sys.exit(0)

    # --- 通常起動（管理者権限あり） ---
    try:
        chatbridge = ChatBridgeApp(app, config)
        sys.exit(chatbridge.run())
    except KeyboardInterrupt:
        print(f"\n{t('shut_down')}")
        sys.exit(0)


if __name__ == "__main__":
    main()
