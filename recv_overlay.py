"""
受信翻訳オーバーレイ

画面上にフローティングウィンドウとして受信翻訳結果を時系列で表示する。
既存の TranslationOverlay（送信翻訳用）とは独立したウィンドウ。

特徴:
  - ドラッグで移動可能
  - 端をドラッグしてサイズ変更可能
  - 翻訳結果を時系列でスクロール表示
  - 半透明ダークテーマ
  - ターゲットウィンドウが非アクティブ時は自動で隠す
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QPushButton, QSizeGrip,
)
from PySide6.QtCore import Qt, Signal, QPoint, QSize, QTimer
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
        self._target_hwnd = None  # 監視対象のウィンドウハンドル
        self._auto_hide_timer: QTimer | None = None
        self._should_be_visible = False  # サービスから見た表示要求

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

        # デフォルトサイズ
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

        self._title_label = QLabel("📖 " + t("recv_overlay_title"))
        self._title_label.setStyleSheet(
            "color: #a78bfa; font-size: 12px; font-weight: bold;"
            "font-family: 'Segoe UI', 'Yu Gothic UI', sans-serif;"
        )
        title_layout.addWidget(self._title_label)
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

        # 待機中ラベル（メッセージがない時に表示）
        self._waiting_label = QLabel(t("recv_overlay_waiting"))
        self._waiting_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._waiting_label.setStyleSheet(
            "color: #6b7280; font-size: 12px;"
            "font-family: 'Segoe UI', 'Yu Gothic UI', sans-serif;"
            "background-color: rgba(31, 41, 55, 200);"
            "padding: 20px;"
        )

        # メッセージ表示エリア（スクロール可能）
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll_area.setStyleSheet(
            "QScrollArea { background-color: rgba(31, 41, 55, 200);"
            "border: none; }"
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

        # ステータスバー（パイプラインの状態をリアルタイム表示）
        self._status_bar = QLabel("")
        self._status_bar.setFixedHeight(20)
        self._status_bar.setStyleSheet(
            "color: #6b7280; font-size: 10px;"
            "font-family: 'Segoe UI', 'Yu Gothic UI', sans-serif;"
            "background-color: rgba(17, 24, 39, 200);"
            "padding: 2px 8px;"
            "border-bottom-left-radius: 8px;"
            "border-bottom-right-radius: 8px;"
        )

        # 初期状態では待機ラベルを表示、スクロールエリアを非表示
        main_layout.addWidget(self._waiting_label)
        main_layout.addWidget(self._scroll_area)
        main_layout.addWidget(self._status_bar)
        self._scroll_area.hide()
        self._status_bar.hide()

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
        self.setWindowOpacity(self._opacity)
        painter.end()

    # --- ドラッグ移動 ---

    def mousePressEvent(self, event) -> None:
        """タイトルバーのドラッグ開始"""
        if event.button() == Qt.MouseButton.LeftButton:
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

    # --- フォアグラウンドウィンドウ監視（自動表示/非表示） ---

    def start_auto_hide(self, target_title: str = "") -> str:
        """
        フォアグラウンドウィンドウの監視を開始する。

        target_title が空の場合、現在のフォアグラウンドウィンドウのタイトルを
        自動検出して使用する。

        Returns:
            検出/使用されたターゲットアプリのウィンドウタイトル
        """
        import ctypes

        if not target_title:
            # フォアグラウンドウィンドウのタイトルを取得
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd) + 1
            buf = ctypes.create_unicode_buffer(length)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length)
            target_title = buf.value

        self._target_title = target_title
        self._should_be_visible = True

        # 1秒ごとにフォアグラウンドウィンドウをチェック
        if self._auto_hide_timer is None:
            self._auto_hide_timer = QTimer(self)
            self._auto_hide_timer.timeout.connect(self._check_foreground)
        self._auto_hide_timer.start(1000)

        return target_title

    def stop_auto_hide(self) -> None:
        """フォアグラウンドウィンドウの監視を停止する"""
        self._should_be_visible = False
        if self._auto_hide_timer:
            self._auto_hide_timer.stop()

    def _check_foreground(self) -> None:
        """フォアグラウンドウィンドウをチェックし、表示/非表示を切り替える"""
        if not self._should_be_visible:
            return

        import ctypes
        hwnd = ctypes.windll.user32.GetForegroundWindow()

        # フォアグラウンドウィンドウのタイトルを取得
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd) + 1
        buf = ctypes.create_unicode_buffer(length)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length)
        current_title = buf.value

        # ターゲットアプリまたはオーバーレイ自身がフォアグラウンドならOK
        is_target_active = (
            self._target_title in current_title
            or current_title in self._target_title
            or hwnd == int(self.winId())
        )

        if is_target_active and not self.isVisible():
            self.show()
        elif not is_target_active and self.isVisible():
            self.hide()

    # --- メッセージ管理 ---

    def show_waiting(self) -> None:
        """待機状態でオーバーレイを表示する"""
        self._waiting_label.show()
        self._scroll_area.hide()
        self._should_be_visible = True
        self.show()

    def add_message(self, original: str, translated: str) -> None:
        """
        翻訳結果を追加表示する。

        Args:
            original: 原文
            translated: 翻訳文
        """
        self._messages.append((original, translated))

        # 待機ラベルを消してメッセージエリアを表示
        if self._waiting_label.isVisible():
            self._waiting_label.hide()
            self._scroll_area.show()

        # 最大件数を超えたら古いものを削除
        if len(self._messages) > self.MAX_MESSAGES:
            self._messages.pop(0)
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

        # 非表示なら表示する（auto_hide が有効でも、メッセージ追加時は表示）
        if not self.isVisible() and self._should_be_visible:
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
        QTimer.singleShot(50, lambda: (
            self._scroll_area.verticalScrollBar().setValue(
                self._scroll_area.verticalScrollBar().maximum()
            )
        ))

    def clear_messages(self) -> None:
        """すべてのメッセージをクリアする"""
        self._messages.clear()
        while self._messages_layout.count() > 1:
            item = self._messages_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        # 待機ラベルに戻す
        self._waiting_label.show()
        self._scroll_area.hide()

    def update_status(self, status_text: str) -> None:
        """ステータスバーのテキストを更新する"""
        self._status_bar.setText(status_text)
        if not self._status_bar.isVisible():
            self._status_bar.show()

    def update_settings(self, opacity: float = None) -> None:
        """表示設定を更新する"""
        if opacity is not None:
            self._opacity = opacity
            self.setWindowOpacity(self._opacity)

    def set_default_position(self, region: tuple[int, int, int, int]) -> None:
        """
        キャプチャエリアに基づいてデフォルト位置を設定する。
        """
        left, top, right, bottom = region
        screen = self.screen().geometry() if self.screen() else None

        overlay_x = right + 10
        overlay_y = top

        if screen and overlay_x + self.width() > screen.right():
            overlay_x = left - self.width() - 10

        self.move(overlay_x, overlay_y)
        self.resize(400, max(bottom - top, 120))

    def resizeEvent(self, event) -> None:
        """サイズ変更時にグリップ位置を更新する"""
        super().resizeEvent(event)
        self._size_grip.move(
            self.width() - self._size_grip.width(),
            self.height() - self._size_grip.height(),
        )
