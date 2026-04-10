"""
翻訳結果オーバーレイウィンドウ

ゲーム画面の上に半透明のダークパネルとして表示される。
Enter で翻訳結果を確定、Esc でキャンセル。

フルスクリーンゲーム対応:
  - ウィンドウのフォーカスを奪わない（SWP_NOACTIVATE）
  - Enter/Esc はグローバルホットキー（pynput）で処理する
"""

import sys
import threading
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
)
from PySide6.QtCore import Qt, Signal, QTimer, QPoint
from PySide6.QtGui import (
    QFont, QColor, QPainter, QBrush, QPen,
    QFontDatabase, QCursor, QKeyEvent, QPaintEvent,
)

from i18n import t

# Win32 API を使用してフォーカスを奪わずに最前面表示する
if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes

    _user32 = ctypes.windll.user32

    # SetWindowPos の定数
    HWND_TOPMOST = ctypes.wintypes.HWND(-1)
    SWP_NOACTIVATE = 0x0010
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_SHOWWINDOW = 0x0040

# pynput でグローバルキー入力を監視（オーバーレイ表示中のみ）
from pynput import keyboard as pynput_keyboard


# 言語コード → 表示ラベル（オーバーレイに表示する）
_LANG_LABELS = {
    "ja": "JP",
    "en": "EN",
    "zh": "ZH",
    "ko": "KO",
    "fr": "FR",
    "de": "DE",
    "es": "ES",
    "pt": "PT",
    "ru": "RU",
}


def _lang_label(lang_code: str) -> str:
    """言語コードから表示用ラベルを返す"""
    return _LANG_LABELS.get(lang_code, lang_code.upper())


class TranslationOverlay(QWidget):
    """翻訳結果を表示するオーバーレイウィンドウ"""

    # シグナル
    confirmed = Signal(str)   # Enter で確定されたとき（翻訳結果を渡す）
    cancelled = Signal()      # Esc でキャンセルされたとき

    # グローバルキーから安全にUIスレッドへ通知するためのシグナル
    _confirm_signal = Signal()
    _cancel_signal = Signal()

    def __init__(self, opacity: float = 0.9, position: str = "cursor"):
        super().__init__()
        self._opacity = opacity
        self._position = position
        self._original_text = ""
        self._translated_text = ""
        self._engine_name = ""
        self._is_loading = False
        self._loading_dots = 0
        self._loading_timer = QTimer(self)
        self._loading_timer.timeout.connect(self._update_loading)

        # グローバルキーリスナー（オーバーレイ表示中のみ有効）
        self._key_listener: pynput_keyboard.Listener | None = None
        self._overlay_visible = False

        # 内部シグナルを接続
        self._confirm_signal.connect(self._do_confirm)
        self._cancel_signal.connect(self._do_cancel)

        self._setup_window()
        self._setup_ui()

    def _setup_window(self) -> None:
        """ウィンドウの属性を設定する"""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # タスクバーに表示しない
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedWidth(420)

    def _setup_ui(self) -> None:
        """UIコンポーネントをセットアップする"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # メインのコンテナウィジェット（角丸背景描画用）
        self._container = QWidget()
        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(20, 16, 20, 16)
        container_layout.setSpacing(8)

        # ヘッダー行: アプリ名 + エンジン名
        header_layout = QHBoxLayout()
        self._title_label = QLabel(t("app_name"))
        self._title_label.setStyleSheet(
            "color: #8b5cf6; font-weight: bold; font-size: 13px;"
        )
        self._engine_label = QLabel("")
        self._engine_label.setStyleSheet(
            "color: #6b7280; font-size: 11px;"
        )
        self._engine_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        header_layout.addWidget(self._title_label)
        header_layout.addStretch()
        header_layout.addWidget(self._engine_label)
        container_layout.addLayout(header_layout)

        # 区切り線
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #374151;")
        container_layout.addWidget(separator)

        # 原文ラベル
        self._original_label = QLabel("")
        self._original_label.setStyleSheet(
            "color: #9ca3af; font-size: 13px; padding: 4px 0;"
        )
        self._original_label.setWordWrap(True)
        container_layout.addWidget(self._original_label)

        # 翻訳結果ラベル
        self._translated_label = QLabel("")
        self._translated_label.setStyleSheet(
            "color: #f3f4f6; font-size: 15px; font-weight: bold; padding: 4px 0;"
        )
        self._translated_label.setWordWrap(True)
        container_layout.addWidget(self._translated_label)

        # 区切り線
        separator2 = QWidget()
        separator2.setFixedHeight(1)
        separator2.setStyleSheet("background-color: #374151;")
        container_layout.addWidget(separator2)

        # ヒント行
        hint_layout = QHBoxLayout()
        enter_hint = QLabel(t("overlay_confirm"))
        enter_hint.setStyleSheet("color: #6b7280; font-size: 11px;")
        esc_hint = QLabel(t("overlay_cancel"))
        esc_hint.setStyleSheet("color: #6b7280; font-size: 11px;")
        hint_layout.addWidget(enter_hint)
        hint_layout.addStretch()
        hint_layout.addWidget(esc_hint)
        container_layout.addLayout(hint_layout)

        layout.addWidget(self._container)

    def paintEvent(self, event: QPaintEvent) -> None:
        """角丸の半透明背景を描画する"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 背景色（ダークグレー、半透明）
        bg_color = QColor(17, 24, 39)  # Tailwind gray-900 相当
        bg_color.setAlphaF(self._opacity)

        # 角丸の矩形を描画
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(QColor(75, 85, 99, 180), 1))  # 薄いボーダー
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 12, 12)

    def show_translation(
        self,
        original: str,
        translated: str,
        engine_name: str,
        source_lang: str = "ja",
        target_lang: str = "en",
    ) -> None:
        """翻訳結果を表示してオーバーレイを表示する"""
        self._original_text = original
        self._translated_text = translated
        self._engine_name = engine_name
        self._is_loading = False
        self._loading_timer.stop()

        src = _lang_label(source_lang)
        tgt = _lang_label(target_lang)
        self._original_label.setText(f"{src} {original}")
        self._translated_label.setText(f"{tgt} {translated}")
        self._engine_label.setText(f"[{engine_name}]")

        self._position_window()
        self.adjustSize()
        self._show_no_activate()

    def show_loading(self, original: str, engine_name: str, source_lang: str = "ja") -> None:
        """翻訳中の状態を表示する"""
        self._original_text = original
        self._engine_name = engine_name
        self._is_loading = True
        self._loading_dots = 0

        src = _lang_label(source_lang)
        self._original_label.setText(f"{src} {original}")
        self._translated_label.setText(f"🔄 {t('overlay_loading')}")
        self._engine_label.setText(f"[{engine_name}]")

        self._loading_timer.start(400)  # 400msごとにアニメーション更新

        self._position_window()
        self.adjustSize()
        self._show_no_activate()

    def _show_no_activate(self) -> None:
        """フォーカスを奪わずにウィンドウを最前面に表示する"""
        # まず通常の show() で表示（WA_ShowWithoutActivating が効く）
        self.show()

        # Win32 API で確実にフォーカスを奪わず最前面にする
        if sys.platform == "win32":
            hwnd = int(self.winId())
            _user32.SetWindowPos(
                hwnd,
                HWND_TOPMOST,
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
            )

        # グローバルキーリスナーを開始
        self._start_key_listener()

    # Enter/Esc の仮想キーコード（Win32 フィルタで使用）
    _VK_RETURN = 0x0D
    _VK_ESCAPE = 0x1B

    def _start_key_listener(self) -> None:
        """
        オーバーレイ表示中のグローバルキーリスナーを開始する。

        win32_event_filter を使って Enter/Esc キーをゲームに届かないよう
        抑制（suppress）する。これにより、Enter でチャットの原文が
        送信されてしまう問題を防ぐ。
        """
        # 既存のリスナーがあれば停止
        self._stop_key_listener()

        self._overlay_visible = True
        self._key_listener = pynput_keyboard.Listener(
            on_press=self._on_global_key_press,
            win32_event_filter=self._win32_key_filter,
        )
        self._key_listener.daemon = True
        self._key_listener.start()

    def _win32_key_filter(self, msg, data) -> None:
        """
        Win32 低レベルキーボードフック用フィルタ。
        オーバーレイ表示中に Enter/Esc キーを他アプリに渡さないよう抑制する。
        他のキーはそのまま通過させる。
        """
        if not self._overlay_visible:
            return

        # data.vkCode に仮想キーコードが入っている
        if data.vkCode in (self._VK_RETURN, self._VK_ESCAPE):
            # suppress_event() でキーイベントをゲームに届かないようにする
            self._key_listener.suppress_event()

    def _stop_key_listener(self) -> None:
        """グローバルキーリスナーを停止する"""
        self._overlay_visible = False
        if self._key_listener is not None:
            self._key_listener.stop()
            self._key_listener = None

    def _on_global_key_press(self, key) -> None:
        """
        グローバルキー入力のハンドラ（pynput スレッドから呼ばれる）。
        オーバーレイ表示中のみ Enter/Esc を処理する。
        """
        if not self._overlay_visible:
            return

        try:
            if key == pynput_keyboard.Key.enter:
                # Enter: 確定（シグナル経由でUIスレッドへ）
                if not self._is_loading:
                    self._confirm_signal.emit()
            elif key == pynput_keyboard.Key.esc:
                # Esc: キャンセル（シグナル経由でUIスレッドへ）
                self._cancel_signal.emit()
        except AttributeError:
            pass  # 特殊キー以外は無視

    def _do_confirm(self) -> None:
        """確定処理（UIスレッドで実行される）"""
        self._loading_timer.stop()
        self._stop_key_listener()
        self.hide()
        self.confirmed.emit(self._translated_text)

    def _do_cancel(self) -> None:
        """キャンセル処理（UIスレッドで実行される）"""
        self._loading_timer.stop()
        self._stop_key_listener()
        self.hide()
        self.cancelled.emit()

    def _update_loading(self) -> None:
        """ローディングアニメーションを更新する"""
        self._loading_dots = (self._loading_dots + 1) % 4
        dots = "." * self._loading_dots
        base = t('overlay_loading').rstrip('.')
        self._translated_label.setText(f"🔄 {base}{dots}")

    def _position_window(self) -> None:
        """オーバーレイの表示位置を設定する"""
        if self._position == "cursor":
            # マウスカーソルの近くに表示
            cursor_pos = QCursor.pos()
            x = cursor_pos.x() - self.width() // 2
            y = cursor_pos.y() - self.height() - 20  # カーソルの上に表示

            # 画面外にはみ出さないように調整
            screen = self.screen()
            if screen:
                screen_geo = screen.availableGeometry()
                x = max(screen_geo.left() + 10, min(x, screen_geo.right() - self.width() - 10))
                y = max(screen_geo.top() + 10, min(y, screen_geo.bottom() - self.height() - 10))

            self.move(x, y)

        elif self._position == "center":
            # 画面中央に表示
            screen = self.screen()
            if screen:
                screen_geo = screen.availableGeometry()
                x = (screen_geo.width() - self.width()) // 2 + screen_geo.left()
                y = (screen_geo.height() - self.height()) // 2 + screen_geo.top()
                self.move(x, y)

        elif self._position == "corner":
            # 右下に表示
            screen = self.screen()
            if screen:
                screen_geo = screen.availableGeometry()
                x = screen_geo.right() - self.width() - 20
                y = screen_geo.bottom() - self.height() - 20
                self.move(x, y)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        キー入力のフォールバック。
        フォーカスがある場合（ボーダーレス/ウィンドウモード時）にも対応。
        グローバルホットキーと同じ処理をする。
        """
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if not self._is_loading:
                self._do_confirm()
        elif event.key() == Qt.Key.Key_Escape:
            self._do_cancel()

    def update_settings(self, opacity: float, position: str) -> None:
        """設定を更新する"""
        self._opacity = opacity
        self._position = position
        self.update()  # 再描画
