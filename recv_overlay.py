"""
受信翻訳オーバーレイ

画面上にフローティングウィンドウとして受信翻訳結果を時系列で表示する。
既存の TranslationOverlay（送信翻訳用）とは独立したウィンドウ。

特徴:
  - ドラッグで移動可能
  - 端をドラッグしてサイズ変更可能
  - 翻訳結果を時系列でスクロール表示
  - 半透明ダークテーマ
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QPushButton, QSizeGrip,
)
from PySide6.QtCore import Qt, Signal, QPoint, QSize
from PySide6.QtGui import QFont, QColor, QPainter, QCursor

from i18n import t


class ReceivedTranslationOverlay(QWidget):
    """受信翻訳結果をリアルタイム表示するフローティングウィンドウ"""

    # 最大表示メッセージ数
    MAX_MESSAGES = 50

    def __init__(self, opacity: float = 0.85):
        super().__init__()
        self._opacity = opacity
        self._drag_pos: QPoint | None = None
        self._messages: list[tuple[str, str]] = []  # (原文, 翻訳文)

        self._setup_window()
        self._setup_ui()

    def _setup_window(self) -> None:
        """ウィンドウ属性を設定する"""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # デフォルトサイズ（後で位置は設定画面から調整可能）
        self.setMinimumSize(250, 120)
        self.resize(400, 300)

    def _setup_ui(self) -> None:
        """UIコンポーネントをセットアップする"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # タイトルバー（ドラッグ移動用）
        self._title_bar = QWidget()
        self._title_bar.setFixedHeight(28)
        self._title_bar.setStyleSheet(
            "background-color: rgba(17, 24, 39, 220);"
            "border-top-left-radius: 8px;"
            "border-top-right-radius: 8px;"
        )
        title_layout = QHBoxLayout(self._title_bar)
        title_layout.setContentsMargins(10, 0, 4, 0)
        title_layout.setSpacing(4)

        title_label = QLabel("📖 " + t("recv_overlay_title"))
        title_label.setStyleSheet(
            "color: #a78bfa; font-size: 12px; font-weight: bold;"
            "font-family: 'Segoe UI', 'Yu Gothic UI', sans-serif;"
        )
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        # クリアボタン
        clear_btn = QPushButton("🗑")
        clear_btn.setFixedSize(24, 24)
        clear_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #6b7280;"
            "border: none; font-size: 13px; }"
            "QPushButton:hover { color: #f87171; }"
        )
        clear_btn.setToolTip(t("recv_overlay_clear"))
        clear_btn.clicked.connect(self.clear_messages)
        title_layout.addWidget(clear_btn)

        # 閉じるボタン
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #6b7280;"
            "border: none; font-size: 13px; font-weight: bold; }"
            "QPushButton:hover { color: #f87171; }"
        )
        close_btn.clicked.connect(self.hide)
        title_layout.addWidget(close_btn)

        main_layout.addWidget(self._title_bar)

        # メッセージ表示エリア（スクロール可能）
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll_area.setStyleSheet(
            "QScrollArea { background-color: rgba(31, 41, 55, 200);"
            "border: none; border-bottom-left-radius: 8px;"
            "border-bottom-right-radius: 8px; }"
            "QScrollBar:vertical { width: 6px; background: transparent; }"
            "QScrollBar::handle:vertical {"
            "background: rgba(107, 114, 128, 150); border-radius: 3px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {"
            "height: 0px; }"
        )

        self._messages_container = QWidget()
        self._messages_layout = QVBoxLayout(self._messages_container)
        self._messages_layout.setContentsMargins(8, 8, 8, 8)
        self._messages_layout.setSpacing(6)
        self._messages_layout.addStretch()

        self._scroll_area.setWidget(self._messages_container)
        main_layout.addWidget(self._scroll_area)

        # サイズ変更グリップ（右下角）
        self._size_grip = QSizeGrip(self)
        self._size_grip.setStyleSheet(
            "QSizeGrip { width: 12px; height: 12px;"
            "background: transparent; }"
        )

    def paintEvent(self, event) -> None:
        """背景を描画する"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 半透明の背景（描画はスタイルシートに任せるが、不透明度を適用）
        self.setWindowOpacity(self._opacity)
        painter.end()

    # --- ドラッグ移動 ---

    def mousePressEvent(self, event) -> None:
        """タイトルバーのドラッグ開始"""
        if event.button() == Qt.MouseButton.LeftButton:
            # タイトルバー領域のみドラッグ対応
            if event.position().y() <= self._title_bar.height():
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event) -> None:
        """ドラッグ中のウィンドウ移動"""
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        """ドラッグ終了"""
        self._drag_pos = None

    # --- メッセージ管理 ---

    def add_message(self, original: str, translated: str) -> None:
        """
        翻訳結果を追加表示する。

        Args:
            original: 原文
            translated: 翻訳文
        """
        self._messages.append((original, translated))

        # 最大件数を超えたら古いものを削除
        if len(self._messages) > self.MAX_MESSAGES:
            self._messages.pop(0)
            # UI からも最初のウィジェットを削除
            item = self._messages_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        # メッセージウィジェットを追加
        msg_widget = self._create_message_widget(original, translated)

        # stretch の前に挿入
        count = self._messages_layout.count()
        self._messages_layout.insertWidget(count - 1, msg_widget)

        # 最下部にスクロール
        self._scroll_to_bottom()

        # 非表示なら表示する
        if not self.isVisible():
            self.show()

    def _create_message_widget(self, original: str, translated: str) -> QWidget:
        """1件分のメッセージウィジェットを作成する"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        # 原文（小さく薄い色で表示）
        orig_label = QLabel(original)
        orig_label.setWordWrap(True)
        orig_label.setStyleSheet(
            "color: #9ca3af; font-size: 10px;"
            "font-family: 'Segoe UI', 'Yu Gothic UI', sans-serif;"
        )
        layout.addWidget(orig_label)

        # 翻訳文（メインの表示）
        trans_label = QLabel(translated)
        trans_label.setWordWrap(True)
        trans_label.setStyleSheet(
            "color: #f3f4f6; font-size: 13px;"
            "font-family: 'Segoe UI', 'Yu Gothic UI', sans-serif;"
        )
        layout.addWidget(trans_label)

        # 区切り線
        widget.setStyleSheet(
            "QWidget { background-color: rgba(55, 65, 81, 100);"
            "border-radius: 4px; }"
        )

        return widget

    def _scroll_to_bottom(self) -> None:
        """スクロールエリアを最下部に移動する"""
        from PySide6.QtCore import QTimer
        QTimer.singleShot(50, lambda: (
            self._scroll_area.verticalScrollBar().setValue(
                self._scroll_area.verticalScrollBar().maximum()
            )
        ))

    def clear_messages(self) -> None:
        """すべてのメッセージをクリアする"""
        self._messages.clear()
        # レイアウトから stretch 以外のウィジェットを全削除
        while self._messages_layout.count() > 1:
            item = self._messages_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

    def update_settings(self, opacity: float = None) -> None:
        """表示設定を更新する"""
        if opacity is not None:
            self._opacity = opacity
            self.setWindowOpacity(self._opacity)

    def set_default_position(self, region: tuple[int, int, int, int]) -> None:
        """
        キャプチャエリアに基づいてデフォルト位置を設定する。

        オーバーレイはキャプチャエリアの右側に配置する。
        画面からはみ出す場合は左側に配置する。

        Args:
            region: (left, top, right, bottom) — キャプチャ領域
        """
        left, top, right, bottom = region
        screen = self.screen().geometry() if self.screen() else None

        # キャプチャエリアの右側に配置
        overlay_x = right + 10
        overlay_y = top

        # 画面右端からはみ出す場合は左側に配置
        if screen and overlay_x + self.width() > screen.right():
            overlay_x = left - self.width() - 10

        self.move(overlay_x, overlay_y)
        self.resize(400, bottom - top)

    def resizeEvent(self, event) -> None:
        """サイズ変更時にグリップ位置を更新する"""
        super().resizeEvent(event)
        self._size_grip.move(
            self.width() - self._size_grip.width(),
            self.height() - self._size_grip.height(),
        )
