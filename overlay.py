"""
翻訳結果オーバーレイウィンドウ

ゲーム画面の上に半透明のダークパネルとして表示される。
Enter で翻訳結果を確定、Esc でキャンセル。
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
)
from PySide6.QtCore import Qt, Signal, QTimer, QPoint
from PySide6.QtGui import (
    QFont, QColor, QPainter, QBrush, QPen,
    QFontDatabase, QCursor, QKeyEvent, QPaintEvent,
)

from i18n import t


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
        self.show()
        self.activateWindow()
        self.setFocus()

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
        self.show()

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
        """キー入力のハンドラ"""
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            # Enter: 確定
            if not self._is_loading:
                self.hide()
                self.confirmed.emit(self._translated_text)
        elif event.key() == Qt.Key.Key_Escape:
            # Esc: キャンセル
            self._loading_timer.stop()
            self.hide()
            self.cancelled.emit()

    def update_settings(self, opacity: float, position: str) -> None:
        """設定を更新する"""
        self._opacity = opacity
        self._position = position
        self.update()  # 再描画
