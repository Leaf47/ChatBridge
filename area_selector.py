"""
エリア指定オーバーレイ

画面全体を半透明で覆い、ユーザーがマウスドラッグでキャプチャ対象の
チャットエリアを指定するための UI。

操作:
  - マウスドラッグ: 矩形範囲を選択（赤い枠線で表示）
  - Enter / ダブルクリック: 選択を確定して area_selected シグナルを発行
  - Esc / 右クリック: 選択をキャンセル
"""

from PySide6.QtWidgets import QWidget, QLabel, QApplication
from PySide6.QtCore import Qt, Signal, QRect, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QCursor


class AreaSelector(QWidget):
    """画面上のエリアをドラッグで選択する半透明オーバーレイ"""

    # (left, top, right, bottom) のタプルを通知
    area_selected = Signal(tuple)
    # キャンセル通知
    cancelled = Signal()

    def __init__(self):
        super().__init__()
        self._start_pos: QPoint | None = None
        self._end_pos: QPoint | None = None
        self._is_dragging = False

        self._setup_window()

    def _setup_window(self) -> None:
        """ウィンドウ属性を設定する"""
        # フルスクリーン半透明オーバーレイ
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

        # 全画面に拡張
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

    def show(self) -> None:
        """エリア指定モードを開始する"""
        self._start_pos = None
        self._end_pos = None
        self._is_dragging = False

        # 全画面に再設定（マルチモニター対応）
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        super().showFullScreen()

    def paintEvent(self, event) -> None:
        """オーバーレイと選択領域を描画する"""
        painter = QPainter(self)

        # 半透明の暗いオーバーレイ
        painter.fillRect(self.rect(), QColor(0, 0, 0, 120))

        # ガイドテキスト
        painter.setPen(QColor(255, 255, 255, 200))
        painter.setFont(QFont("Segoe UI", 14))
        from i18n import t
        guide_text = t("area_select_guide")
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter,
                         f"\n\n{guide_text}")

        # 選択領域の描画
        if self._start_pos and self._end_pos:
            rect = self._get_selection_rect()

            # 選択領域内を明るく表示（暗いオーバーレイを打ち消す）
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_Clear
            )
            painter.fillRect(rect, QColor(0, 0, 0, 0))
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_SourceOver
            )

            # 半透明の青い塗りつぶし
            painter.fillRect(rect, QColor(59, 130, 246, 40))

            # 赤い枠線
            pen = QPen(QColor(239, 68, 68), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(rect)

            # サイズ表示
            painter.setPen(QColor(255, 255, 255, 220))
            painter.setFont(QFont("Segoe UI", 11))
            size_text = f"{rect.width()} × {rect.height()}"
            painter.drawText(
                rect.x(), rect.y() - 6, size_text
            )

        painter.end()

    def mousePressEvent(self, event) -> None:
        """ドラッグ開始"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._start_pos = event.pos()
            self._end_pos = event.pos()
            self._is_dragging = True
            self.update()
        elif event.button() == Qt.MouseButton.RightButton:
            # 右クリックでキャンセル
            self._cancel()

    def mouseMoveEvent(self, event) -> None:
        """ドラッグ中"""
        if self._is_dragging:
            self._end_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        """ドラッグ終了"""
        if event.button() == Qt.MouseButton.LeftButton and self._is_dragging:
            self._end_pos = event.pos()
            self._is_dragging = False
            self.update()

    def mouseDoubleClickEvent(self, event) -> None:
        """ダブルクリックで確定"""
        if self._start_pos and self._end_pos:
            self._confirm()

    def keyPressEvent(self, event) -> None:
        """キー入力の処理"""
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            # Enter で確定
            if self._start_pos and self._end_pos:
                self._confirm()
        elif event.key() == Qt.Key.Key_Escape:
            # Esc でキャンセル
            self._cancel()

    def _get_selection_rect(self) -> QRect:
        """選択領域の QRect を返す（座標を正規化）"""
        if not self._start_pos or not self._end_pos:
            return QRect()
        return QRect(self._start_pos, self._end_pos).normalized()

    def _confirm(self) -> None:
        """選択を確定する"""
        rect = self._get_selection_rect()
        if rect.width() < 10 or rect.height() < 10:
            # 小さすぎる選択は無視
            return

        # グローバル座標に変換
        screen_pos = self.mapToGlobal(rect.topLeft())
        region = (
            screen_pos.x(),
            screen_pos.y(),
            screen_pos.x() + rect.width(),
            screen_pos.y() + rect.height(),
        )
        self.hide()
        self.area_selected.emit(region)

    def _cancel(self) -> None:
        """選択をキャンセルする"""
        self.hide()
        self.cancelled.emit()
