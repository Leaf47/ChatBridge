"""
エリア指定オーバーレイ

画面のスクリーンショットを背景に表示し、その上に半透明の暗いオーバーレイを重ねる。
ユーザーがマウスドラッグでキャプチャ対象のチャットエリアを指定する。
選択領域部分は暗いオーバーレイが除去され、実際の画面が見える。

操作:
  - マウスドラッグ: 矩形範囲を選択（赤い枠線で表示）
  - Enter / ダブルクリック: 選択を確定して area_selected シグナルを発行
  - Esc / 右クリック: 選択をキャンセル
"""

from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, Signal, QRect, QPoint
from PySide6.QtGui import (
    QPainter, QColor, QPen, QFont, QCursor,
    QPixmap, QScreen, QRegion,
)


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
        self._screenshot: QPixmap | None = None  # 背景スクリーンショット

        self._setup_window()

    def _setup_window(self) -> None:
        """ウィンドウ属性を設定する"""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

        # 全画面に拡張
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

    def show(self) -> None:
        """エリア指定モードを開始する"""
        self._start_pos = None
        self._end_pos = None
        self._is_dragging = False

        # 表示前に画面全体のスクリーンショットを撮る
        screen = QApplication.primaryScreen()
        if screen:
            self._screenshot = screen.grabWindow(0)
            self.setGeometry(screen.geometry())

        super().showFullScreen()

    def paintEvent(self, event) -> None:
        """スクリーンショット + 暗いオーバーレイ + 選択領域を描画する"""
        painter = QPainter(self)
        full_rect = self.rect()

        # 1. 背景にスクリーンショットを描画
        if self._screenshot:
            painter.drawPixmap(full_rect, self._screenshot)

        # 2. 選択領域の外側だけ暗いオーバーレイを描画
        if self._start_pos and self._end_pos:
            sel_rect = self._get_selection_rect()

            # 選択領域以外を暗くするリージョンを作成
            outer = QRegion(full_rect)
            inner = QRegion(sel_rect)
            dark_region = outer.subtracted(inner)

            painter.setClipRegion(dark_region)
            painter.fillRect(full_rect, QColor(0, 0, 0, 140))
            painter.setClipping(False)

            # 選択領域に薄い青の半透明を重ねる
            painter.fillRect(sel_rect, QColor(59, 130, 246, 30))

            # 赤い枠線
            pen = QPen(QColor(239, 68, 68), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(sel_rect)

            # サイズ表示
            painter.setPen(QColor(255, 255, 255, 240))
            painter.setFont(QFont("Segoe UI", 11))
            size_text = f"{sel_rect.width()} × {sel_rect.height()}"
            painter.drawText(
                sel_rect.x(), sel_rect.y() - 6, size_text
            )
        else:
            # 選択前: 全体を暗くする
            painter.fillRect(full_rect, QColor(0, 0, 0, 140))

        # 3. ガイドテキスト（常に表示）
        painter.setPen(QColor(255, 255, 255, 220))
        painter.setFont(QFont("Segoe UI", 14))
        from i18n import t
        guide_text = t("area_select_guide")
        painter.drawText(
            full_rect,
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter,
            f"\n\n{guide_text}",
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
            if self._start_pos and self._end_pos:
                self._confirm()
        elif event.key() == Qt.Key.Key_Escape:
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
