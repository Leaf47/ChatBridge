"""
設定画面モジュール

ホットキー、翻訳エンジン、APIキー、オーバーレイ設定を管理するUIを提供する。
ダークテーマのコンパクトなウィンドウ。
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QLineEdit, QPushButton, QSlider,
    QCheckBox, QGroupBox, QFormLayout, QMessageBox,
    QTabWidget,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QKeySequence

from config import Config
from translator import get_translator_names, create_translator, TranslationError


# ダークテーマのスタイルシート
DARK_STYLE = """
QWidget {
    background-color: #1f2937;
    color: #f3f4f6;
    font-family: 'Segoe UI', 'Yu Gothic UI', sans-serif;
    font-size: 13px;
}
QGroupBox {
    border: 1px solid #374151;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 20px;
    font-weight: bold;
    color: #d1d5db;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QLineEdit {
    background-color: #111827;
    border: 1px solid #374151;
    border-radius: 6px;
    padding: 6px 10px;
    color: #f3f4f6;
}
QLineEdit:focus {
    border-color: #8b5cf6;
}
QComboBox {
    background-color: #111827;
    border: 1px solid #374151;
    border-radius: 6px;
    padding: 6px 10px;
    color: #f3f4f6;
}
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #111827;
    border: 1px solid #374151;
    color: #f3f4f6;
    selection-background-color: #8b5cf6;
}
QPushButton {
    background-color: #8b5cf6;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #7c3aed;
}
QPushButton:pressed {
    background-color: #6d28d9;
}
QPushButton#secondaryBtn {
    background-color: #374151;
    color: #d1d5db;
}
QPushButton#secondaryBtn:hover {
    background-color: #4b5563;
}
QSlider::groove:horizontal {
    height: 6px;
    background-color: #374151;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background-color: #8b5cf6;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}
QSlider::sub-page:horizontal {
    background-color: #8b5cf6;
    border-radius: 3px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #374151;
    background-color: #111827;
}
QCheckBox::indicator:checked {
    background-color: #8b5cf6;
    border-color: #8b5cf6;
}
QTabWidget::pane {
    border: 1px solid #374151;
    border-radius: 0 0 8px 8px;
    background-color: #1f2937;
}
QTabBar::tab {
    background-color: #111827;
    color: #9ca3af;
    padding: 8px 16px;
    border: 1px solid #374151;
    border-bottom: none;
    border-radius: 6px 6px 0 0;
}
QTabBar::tab:selected {
    background-color: #1f2937;
    color: #f3f4f6;
    border-color: #374151;
}
"""


class HotkeyInput(QLineEdit):
    """ホットキー入力用のカスタムフィールド（キーバインド記録方式）"""

    hotkey_changed = Signal(str)

    def __init__(self, current_hotkey: str = ""):
        super().__init__()
        self._hotkey = current_hotkey
        self.setText(current_hotkey)
        self.setReadOnly(True)
        self.setPlaceholderText("クリックしてキーを入力...")
        self._recording = False

    def mousePressEvent(self, event):
        """クリックでキー記録モードに入る"""
        self._recording = True
        self.setText("キーを入力してください...")
        self.setStyleSheet("border-color: #8b5cf6; background-color: #1e1b4b;")
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        """キー入力をキャプチャしてホットキー文字列に変換する"""
        if not self._recording:
            return

        parts = []
        modifiers = event.modifiers()

        if modifiers & Qt.KeyboardModifier.ControlModifier:
            parts.append("ctrl")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            parts.append("alt")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            parts.append("shift")

        # メインキーを取得（修飾キー単独は無視）
        key = event.key()
        if key not in (
            Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Shift,
            Qt.Key.Key_Meta, Qt.Key.Key_AltGr,
        ):
            # キー名を取得
            key_text = event.text().lower()
            if key_text and key_text.isprintable():
                parts.append(key_text)
            else:
                # 特殊キー
                key_name = QKeySequence(key).toString().lower()
                if key_name:
                    parts.append(key_name)

            if parts:
                self._hotkey = "+".join(parts)
                self.setText(self._hotkey)
                self._recording = False
                self.setStyleSheet("")  # スタイルをリセット
                self.hotkey_changed.emit(self._hotkey)

    def get_hotkey(self) -> str:
        """現在設定されているホットキー文字列を返す"""
        return self._hotkey


class SettingsWindow(QWidget):
    """設定画面ウィンドウ"""

    # 設定が変更されたことを通知するシグナル
    settings_changed = Signal()

    def __init__(self, config: Config):
        super().__init__()
        self._config = config
        self._setup_window()
        self._setup_ui()
        self._load_settings()

    def _setup_window(self) -> None:
        """ウィンドウの属性を設定する"""
        self.setWindowTitle("JA2EN - 設定")
        self.setFixedSize(480, 520)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setStyleSheet(DARK_STYLE)

    def _setup_ui(self) -> None:
        """UIコンポーネントをセットアップする"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # タイトル
        title = QLabel("⚙️ JA2EN 設定")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #8b5cf6;")
        main_layout.addWidget(title)

        # タブウィジェット
        tabs = QTabWidget()
        tabs.addTab(self._create_general_tab(), "一般")
        tabs.addTab(self._create_translator_tab(), "翻訳エンジン")
        main_layout.addWidget(tabs)

        # ボタン行
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("キャンセル")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.hide)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("💾 保存")
        save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(save_btn)

        main_layout.addLayout(btn_layout)

    def _create_general_tab(self) -> QWidget:
        """一般設定タブを作成する"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        # ホットキー設定
        hotkey_group = QGroupBox("🎮 ホットキー")
        hotkey_layout = QFormLayout(hotkey_group)
        self._hotkey_input = HotkeyInput()
        hotkey_layout.addRow("翻訳ホットキー:", self._hotkey_input)
        layout.addWidget(hotkey_group)

        # オーバーレイ設定
        overlay_group = QGroupBox("🖥️ オーバーレイ")
        overlay_layout = QFormLayout(overlay_group)

        # 表示位置
        self._position_combo = QComboBox()
        self._position_combo.addItems(["カーソル付近", "画面中央", "右下"])
        overlay_layout.addRow("表示位置:", self._position_combo)

        # 透明度スライダー
        opacity_widget = QWidget()
        opacity_hlayout = QHBoxLayout(opacity_widget)
        opacity_hlayout.setContentsMargins(0, 0, 0, 0)
        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(30, 100)
        self._opacity_slider.setTickInterval(10)
        self._opacity_label = QLabel("90%")
        self._opacity_slider.valueChanged.connect(
            lambda v: self._opacity_label.setText(f"{v}%")
        )
        opacity_hlayout.addWidget(self._opacity_slider)
        opacity_hlayout.addWidget(self._opacity_label)
        overlay_layout.addRow("透明度:", opacity_widget)

        # 即ペーストオプション
        self._auto_paste_check = QCheckBox("確認なしで即座にペーストする")
        overlay_layout.addRow("", self._auto_paste_check)

        layout.addWidget(overlay_group)
        layout.addStretch()
        return tab

    def _create_translator_tab(self) -> QWidget:
        """翻訳エンジン設定タブを作成する"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        # MyMemory 設定（メイン）
        mymemory_group = QGroupBox("📧 MyMemory 設定")
        mymemory_layout = QFormLayout(mymemory_group)

        # メールアドレス入力
        self._mymemory_email_input = QLineEdit()
        self._mymemory_email_input.setPlaceholderText("example@email.com（任意）")
        mymemory_layout.addRow("メールアドレス:", self._mymemory_email_input)

        # 説明ラベル
        email_hint = QLabel(
            "💡 メールアドレスを設定すると、1日の使用量が\n"
            "   5,000文字 → 50,000文字（10倍）に増加します。\n"
            "   未設定でも使えます。"
        )
        email_hint.setStyleSheet("color: #9ca3af; font-size: 11px; padding: 4px 0;")
        email_hint.setWordWrap(True)
        mymemory_layout.addRow("", email_hint)

        # 接続テストボタン
        test_btn = QPushButton("🧪 接続テスト")
        test_btn.setObjectName("secondaryBtn")
        test_btn.clicked.connect(self._test_connection)
        mymemory_layout.addRow("", test_btn)

        layout.addWidget(mymemory_group)

        # エンジン選択（将来の拡張用）
        engine_group = QGroupBox("🔄 翻訳エンジン（将来の拡張）")
        engine_layout = QFormLayout(engine_group)

        self._engine_combo = QComboBox()
        for key, display_name in get_translator_names():
            self._engine_combo.addItem(display_name, key)
        self._engine_combo.setEnabled(False)
        engine_layout.addRow("エンジン:", self._engine_combo)

        self._deepl_key_input = QLineEdit()
        self._deepl_key_input.setPlaceholderText("将来のアップデートで有効化予定")
        self._deepl_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._deepl_key_input.setEnabled(False)
        engine_layout.addRow("DeepL:", self._deepl_key_input)

        self._google_key_input = QLineEdit()
        self._google_key_input.setPlaceholderText("将来のアップデートで有効化予定")
        self._google_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._google_key_input.setEnabled(False)
        engine_layout.addRow("Google:", self._google_key_input)

        # 注釈ラベル
        future_hint = QLabel("🔒 DeepL / Google への切り替えは将来のアップデートで対応予定です。")
        future_hint.setStyleSheet("color: #6b7280; font-size: 11px; padding: 4px 0;")
        future_hint.setWordWrap(True)
        engine_layout.addRow("", future_hint)

        layout.addWidget(engine_group)

        layout.addStretch()
        return tab

    def _test_connection(self) -> None:
        """MyMemory APIの接続テストを行う"""
        email = self._mymemory_email_input.text().strip()

        try:
            translator = create_translator("mymemory", mymemory_email=email)
            result = translator.translate("これはテストです", source="ja", target="en")

            email_status = (
                f"📧 メールアドレス設定済み（1日50,000文字）"
                if email
                else "📧 メールアドレス未設定（1日5,000文字）"
            )

            QMessageBox.information(
                self,
                "接続テスト成功",
                f"✅ MyMemory に接続できました！\n\n"
                f"テスト翻訳: 「これはテストです」→ 「{result}」\n\n"
                f"{email_status}",
            )
        except TranslationError as e:
            QMessageBox.warning(
                self,
                "接続テスト失敗",
                f"❌ エラーが発生しました:\n\n{e}",
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "接続テスト失敗",
                f"❌ 予期しないエラー:\n\n{e}",
            )

    def _load_settings(self) -> None:
        """設定ファイルからUIに値を読み込む"""
        # ホットキー
        self._hotkey_input._hotkey = self._config.get("hotkey_translate", "ctrl+j")
        self._hotkey_input.setText(self._hotkey_input._hotkey)

        # オーバーレイ位置
        position = self._config.get("overlay_position", "cursor")
        position_map = {"cursor": 0, "center": 1, "corner": 2}
        self._position_combo.setCurrentIndex(position_map.get(position, 0))

        # 透明度
        opacity = int(self._config.get("overlay_opacity", 0.9) * 100)
        self._opacity_slider.setValue(opacity)
        self._opacity_label.setText(f"{opacity}%")

        # 即ペースト
        self._auto_paste_check.setChecked(self._config.get("auto_paste", False))

        # MyMemory メールアドレス
        self._mymemory_email_input.setText(self._config.get("mymemory_email", ""))

        # 翻訳エンジン
        engine = self._config.get("translator", "mymemory")
        for i in range(self._engine_combo.count()):
            if self._engine_combo.itemData(i) == engine:
                self._engine_combo.setCurrentIndex(i)
                break

        # APIキー
        self._deepl_key_input.setText(self._config.get("api_keys.deepl", ""))
        self._google_key_input.setText(self._config.get("api_keys.google", ""))

    def _save_settings(self) -> None:
        """UIの値を設定ファイルに保存する"""
        # ホットキー
        self._config.set("hotkey_translate", self._hotkey_input.get_hotkey())

        # オーバーレイ位置
        position_map = {0: "cursor", 1: "center", 2: "corner"}
        self._config.set(
            "overlay_position",
            position_map.get(self._position_combo.currentIndex(), "cursor"),
        )

        # 透明度
        self._config.set("overlay_opacity", self._opacity_slider.value() / 100.0)

        # 即ペースト
        self._config.set("auto_paste", self._auto_paste_check.isChecked())

        # MyMemory メールアドレス
        self._config.set("mymemory_email", self._mymemory_email_input.text().strip())

        # 翻訳エンジン
        self._config.set("translator", self._engine_combo.currentData())

        # APIキー
        self._config.set("api_keys.deepl", self._deepl_key_input.text())
        self._config.set("api_keys.google", self._google_key_input.text())

        # 保存
        self._config.save()
        self.settings_changed.emit()
        self.hide()
