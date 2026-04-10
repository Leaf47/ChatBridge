"""
設定画面モジュール

ホットキー、翻訳エンジン、言語設定、オーバーレイ設定を管理するUIを提供する。
ダークテーマのコンパクトなウィンドウ。
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QLineEdit, QPushButton, QSlider,
    QCheckBox, QGroupBox, QFormLayout, QMessageBox,
    QTabWidget, QScrollArea,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QKeySequence

from config import Config
from translator import get_translator_names, create_translator, TranslationError
from i18n import t, get_available_languages
import sys
import os


# タスクスケジューラでの自動起動管理（管理者権限で自動起動）
_TASK_NAME = "ChatBridge"


def _get_exe_path() -> str:
    """実行ファイルのパスを取得する"""
    if getattr(sys, 'frozen', False):
        return f'"{sys.executable}"'
    else:
        exe_path = sys.executable
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
        return f'"{exe_path}" "{script_path}"'



def _get_auto_start_admin() -> bool:
    """タスクスケジューラに管理者権限の自動起動タスクが登録されているか確認する"""
    import subprocess
    try:
        result = subprocess.run(
            ["schtasks", "/query", "/tn", _TASK_NAME],
            capture_output=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return result.returncode == 0
    except Exception:
        return False


def _set_auto_start_admin(enabled: bool) -> bool:
    """
    タスクスケジューラで管理者権限の自動起動を設定する。
    登録時にUACが発生する場合がある。成功時True、失敗時Falseを返す。
    """
    import subprocess
    try:
        if enabled:
            exe_path = _get_exe_path()
            # PowerShellでタスクを作成（最上位特権 + ログオン時実行）
            ps_script = (
                f'$action = New-ScheduledTaskAction -Execute {exe_path};'
                f'$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME;'
                f'$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit 0;'
                f'$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest -LogonType Interactive;'
                f'$task = New-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -Principal $principal;'
                f'Register-ScheduledTask -TaskName "{_TASK_NAME}" -InputObject $task -Force'
            )
            # 管理者昇格して実行（UACプロンプトが表示される）
            result = subprocess.run(
                ["powershell", "-Command",
                 f'Start-Process powershell -ArgumentList \'-Command {ps_script}\' -Verb RunAs -Wait'],
                capture_output=True, timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            # 登録されたか確認
            return _get_auto_start_admin()
        else:
            # タスクの削除（管理者昇格）
            result = subprocess.run(
                ["powershell", "-Command",
                 f'Start-Process schtasks -ArgumentList \'/delete /tn "{_TASK_NAME}" /f\' -Verb RunAs -Wait'],
                capture_output=True, timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return not _get_auto_start_admin()
    except Exception:
        return False


# サポートする翻訳言語の一覧（コード, ネイティブ表記名）
TRANSLATION_LANGUAGES = [
    ("ja", "日本語"),
    ("en", "English"),
    ("zh", "中文"),
    ("ko", "한국어"),
    ("fr", "Français"),
    ("de", "Deutsch"),
    ("es", "Español"),
    ("pt", "Português"),
    ("ru", "Русский"),
]

def _get_check_svg_path() -> str:
    """チェックマークSVGファイルのパスを取得する（スラッシュ区切り）"""
    if getattr(sys, 'frozen', False):
        base = os.path.join(sys._MEIPASS, "assets")
    else:
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    # Qtのスタイルシートではスラッシュ区切りが必要
    return os.path.join(base, "check.svg").replace("\\", "/")


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
    min-height: 20px;
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
    min-height: 20px;
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
QCheckBox {
    spacing: 8px;
    color: #e5e7eb;
}
QCheckBox:disabled {
    color: #6b7280;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 2px solid #6b7280;
    background-color: #1f2937;
}
QCheckBox::indicator:hover {
    border-color: #a78bfa;
    background-color: #2d3748;
}
QCheckBox::indicator:checked {
    background-color: #8b5cf6;
    border-color: #8b5cf6;
    image: url({{CHECK_SVG_PATH}});
}
QCheckBox::indicator:checked:hover {
    background-color: #7c3aed;
    border-color: #7c3aed;
}
QCheckBox::indicator:disabled {
    border-color: #374151;
    background-color: #111827;
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
        self.setPlaceholderText(t("general_hotkey_hint"))
        self._recording = False

    def mousePressEvent(self, event):
        """クリックでキー記録モードに入る"""
        self._recording = True
        self.setText("...")
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

        key = event.key()
        if key not in (
            Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Shift,
            Qt.Key.Key_Meta, Qt.Key.Key_AltGr,
        ):
            key_text = event.text().lower()
            if key_text and key_text.isprintable():
                parts.append(key_text)
            else:
                key_name = QKeySequence(key).toString().lower()
                if key_name:
                    parts.append(key_name)

            if parts:
                self._hotkey = "+".join(parts)
                self.setText(self._hotkey)
                self._recording = False
                self.setStyleSheet("")
                self.hotkey_changed.emit(self._hotkey)

    def get_hotkey(self) -> str:
        """現在設定されているホットキー文字列を返す"""
        return self._hotkey


class SettingsWindow(QWidget):
    """設定画面ウィンドウ"""

    settings_changed = Signal()

    def __init__(self, config: Config):
        super().__init__()
        self._config = config
        self._setup_window()
        self._setup_ui()
        self._load_settings()

    def _setup_window(self) -> None:
        """ウィンドウの属性を設定する"""
        self.setWindowTitle(t("settings_title"))
        self.setFixedSize(480, 680)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        # チェックマークSVGのパスを動的に解決してスタイルに注入
        style = DARK_STYLE.replace("{{CHECK_SVG_PATH}}", _get_check_svg_path())
        self.setStyleSheet(style)

    def _setup_ui(self) -> None:
        """UIコンポーネントをセットアップする"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # タイトル
        title = QLabel(t("settings_header"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #8b5cf6;")
        main_layout.addWidget(title)

        # タブウィジェット
        tabs = QTabWidget()
        tabs.addTab(self._create_general_tab(), t("tab_general"))
        tabs.addTab(self._create_translator_tab(), t("tab_translator"))
        main_layout.addWidget(tabs)

        # ボタン行
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton(t("cancel"))
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.hide)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton(t("save"))
        save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(save_btn)

        main_layout.addLayout(btn_layout)

    def _create_general_tab(self) -> QWidget:
        """一般設定タブを作成する（スクロール可能）"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        # ホットキー設定
        hotkey_group = QGroupBox(t("general_hotkey_group"))
        hotkey_layout = QFormLayout(hotkey_group)
        self._hotkey_input = HotkeyInput()
        hotkey_layout.addRow(t("general_hotkey_label"), self._hotkey_input)
        layout.addWidget(hotkey_group)

        # オーバーレイ設定
        overlay_group = QGroupBox(t("overlay_opacity_group"))
        overlay_layout = QFormLayout(overlay_group)

        # 表示位置
        self._position_combo = QComboBox()
        self._position_combo.addItems([
            t("overlay_position_cursor"),
            t("overlay_position_center"),
            t("overlay_position_top_right"),
        ])
        overlay_layout.addRow(t("overlay_position_group").replace("📍 ", ""), self._position_combo)

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
        overlay_layout.addRow(t("overlay_opacity_label"), opacity_widget)

        # 即ペーストオプション
        self._auto_paste_check = QCheckBox(t("general_auto_paste"))
        overlay_layout.addRow("", self._auto_paste_check)

        layout.addWidget(overlay_group)

        # 起動設定
        startup_group = QGroupBox("🚀 起動")
        startup_layout = QVBoxLayout(startup_group)
        startup_layout.setSpacing(6)

        self._auto_start_check = QCheckBox(t("general_auto_start"))
        startup_layout.addWidget(self._auto_start_check)

        auto_start_hint = QLabel(t("general_auto_start_hint"))
        auto_start_hint.setStyleSheet("color: #6b7280; font-size: 11px; padding: 2px 0 0 28px;")
        auto_start_hint.setWordWrap(True)
        startup_layout.addWidget(auto_start_hint)
        layout.addWidget(startup_group)

        # UI言語設定
        lang_group = QGroupBox(t("general_ui_lang_group"))
        lang_layout = QFormLayout(lang_group)

        self._ui_lang_combo = QComboBox()
        for code, name in get_available_languages():
            self._ui_lang_combo.addItem(name, code)
        lang_layout.addRow(t("general_ui_lang_label"), self._ui_lang_combo)

        lang_hint = QLabel(t("general_ui_lang_hint"))
        lang_hint.setStyleSheet("color: #6b7280; font-size: 11px; padding: 4px 0;")
        lang_hint.setWordWrap(True)
        lang_layout.addRow("", lang_hint)

        layout.addWidget(lang_group)

        layout.addStretch()

        scroll.setWidget(tab)
        return scroll

    def _create_translator_tab(self) -> QWidget:
        """翻訳エンジン設定タブを作成する（スクロール可能）"""
        # スクロールエリアで内容が多くても対応
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        # 翻訳方向
        lang_group = QGroupBox(t("translator_lang_group"))
        lang_group_layout = QVBoxLayout(lang_group)

        self._source_lang_combo = QComboBox()
        self._target_lang_combo = QComboBox()
        for code, name in TRANSLATION_LANGUAGES:
            self._source_lang_combo.addItem(name, code)
            self._target_lang_combo.addItem(name, code)

        # 横並びレイアウト: [翻訳元 ▼] [🔄] [翻訳先 ▼]
        lang_row = QHBoxLayout()
        lang_row.setSpacing(8)

        source_col = QVBoxLayout()
        source_label = QLabel(t("translator_source_label"))
        source_label.setStyleSheet("color: #9ca3af; font-size: 11px;")
        source_col.addWidget(source_label)
        source_col.addWidget(self._source_lang_combo)
        lang_row.addLayout(source_col, 1)

        # 入れ替えボタン
        swap_btn = QPushButton("⇄")
        swap_btn.setObjectName("secondaryBtn")
        swap_btn.setFixedSize(44, 36)
        swap_btn.setStyleSheet("font-size: 18px; font-weight: bold;")
        swap_btn.setToolTip(t("translator_swap"))
        swap_btn.clicked.connect(self._swap_languages)
        # 垂直中央に寄せるためにストレッチで挟む
        swap_col = QVBoxLayout()
        swap_col.addSpacing(16)
        swap_col.addWidget(swap_btn)
        lang_row.addLayout(swap_col, 0)

        target_col = QVBoxLayout()
        target_label = QLabel(t("translator_target_label"))
        target_label.setStyleSheet("color: #9ca3af; font-size: 11px;")
        target_col.addWidget(target_label)
        target_col.addWidget(self._target_lang_combo)
        lang_row.addLayout(target_col, 1)

        lang_group_layout.addLayout(lang_row)

        layout.addWidget(lang_group)

        # MyMemory 設定
        mymemory_group = QGroupBox(t("translator_mymemory_group"))
        mymemory_layout = QFormLayout(mymemory_group)

        self._mymemory_email_input = QLineEdit()
        self._mymemory_email_input.setPlaceholderText(t("translator_email_placeholder"))
        mymemory_layout.addRow(t("translator_email_label"), self._mymemory_email_input)

        email_hint = QLabel(t("translator_email_hint"))
        email_hint.setStyleSheet("color: #9ca3af; font-size: 11px; padding: 4px 0;")
        email_hint.setWordWrap(True)
        mymemory_layout.addRow("", email_hint)

        test_btn = QPushButton(t("translator_test"))
        test_btn.setObjectName("secondaryBtn")
        test_btn.clicked.connect(self._test_connection)
        mymemory_layout.addRow("", test_btn)

        layout.addWidget(mymemory_group)

        # エンジン選択（将来の拡張用）
        engine_group = QGroupBox(t("translator_future_group"))
        engine_layout = QFormLayout(engine_group)

        self._engine_combo = QComboBox()
        for key, display_name in get_translator_names():
            self._engine_combo.addItem(display_name, key)
        self._engine_combo.setEnabled(False)
        engine_layout.addRow(t("translator_engine_label"), self._engine_combo)

        self._deepl_key_input = QLineEdit()
        self._deepl_key_input.setPlaceholderText(t("translator_future_placeholder"))
        self._deepl_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._deepl_key_input.setEnabled(False)
        engine_layout.addRow("DeepL:", self._deepl_key_input)

        self._google_key_input = QLineEdit()
        self._google_key_input.setPlaceholderText(t("translator_future_placeholder"))
        self._google_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._google_key_input.setEnabled(False)
        engine_layout.addRow("Google:", self._google_key_input)

        future_hint = QLabel(t("translator_future_hint"))
        future_hint.setStyleSheet("color: #6b7280; font-size: 11px; padding: 4px 0;")
        future_hint.setWordWrap(True)
        engine_layout.addRow("", future_hint)

        layout.addWidget(engine_group)

        layout.addStretch()

        scroll.setWidget(tab)
        return scroll


    def _swap_languages(self) -> None:
        """翻訳元と翻訳先を入れ替える"""
        source_idx = self._source_lang_combo.currentIndex()
        target_idx = self._target_lang_combo.currentIndex()
        self._source_lang_combo.setCurrentIndex(target_idx)
        self._target_lang_combo.setCurrentIndex(source_idx)

    def _test_connection(self) -> None:
        """MyMemory APIの接続テストを行う"""
        email = self._mymemory_email_input.text().strip()
        source = self._source_lang_combo.currentData()
        target = self._target_lang_combo.currentData()

        try:
            translator = create_translator("mymemory", mymemory_email=email)
            test_text = "これはテストです" if source == "ja" else "This is a test"
            result = translator.translate(test_text, source=source, target=target)

            email_status = (
                f"📧 50,000 chars/day" if email else "📧 5,000 chars/day"
            )

            QMessageBox.information(
                self,
                "✅",
                t("translator_test_success",
                  source=test_text, result=result, email_status=email_status),
            )
        except TranslationError as e:
            QMessageBox.warning(
                self, "❌", t("translator_test_fail", error=str(e)),
            )
        except Exception as e:
            QMessageBox.critical(
                self, "❌", t("translator_test_fail", error=str(e)),
            )

    def _load_settings(self) -> None:
        """設定ファイルからUIに値を読み込む"""
        # ホットキー
        self._hotkey_input._hotkey = self._config.get("hotkey_translate", "alt+j")
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

        # 自動起動（config の保存値から読み込む）
        auto_start = self._config.get("auto_start", False)
        self._auto_start_check.setChecked(auto_start)
        # 保存時の差分検出用に初期値を記録
        self._initial_auto_start = auto_start

        # UI言語
        ui_lang = self._config.get("ui_lang", "ja")
        for i in range(self._ui_lang_combo.count()):
            if self._ui_lang_combo.itemData(i) == ui_lang:
                self._ui_lang_combo.setCurrentIndex(i)
                break

        # 翻訳言語ペア
        source = self._config.get("source_lang", "ja")
        target = self._config.get("target_lang", "en")
        for i in range(self._source_lang_combo.count()):
            if self._source_lang_combo.itemData(i) == source:
                self._source_lang_combo.setCurrentIndex(i)
                break
        for i in range(self._target_lang_combo.count()):
            if self._target_lang_combo.itemData(i) == target:
                self._target_lang_combo.setCurrentIndex(i)
                break

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

        # 自動起動（変更があった場合のみタスクスケジューラを操作）
        auto_start = self._auto_start_check.isChecked()
        self._config.set("auto_start", auto_start)

        if auto_start != self._initial_auto_start:
            success = _set_auto_start_admin(auto_start)
            if auto_start and not success:
                QMessageBox.warning(
                    self, "⚠️",
                    t("general_auto_start_admin_fail"),
                )
                self._auto_start_check.setChecked(False)
                self._config.set("auto_start", False)
            self._initial_auto_start = self._auto_start_check.isChecked()

        # UI言語（変更があれば再起動を促す）
        new_lang = self._ui_lang_combo.currentData()
        old_lang = self._config.get("ui_lang", "ja")
        self._config.set("ui_lang", new_lang)

        # 翻訳言語ペア
        self._config.set("source_lang", self._source_lang_combo.currentData())
        self._config.set("target_lang", self._target_lang_combo.currentData())

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

        # 言語が変更された場合、再起動を促す
        if new_lang != old_lang:
            msg = QMessageBox()
            msg.setWindowTitle("ChatBridge")
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setText(t("lang_changed_restart"))
            msg.setWindowFlags(msg.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
            msg.addButton(QMessageBox.StandardButton.Ok)
            msg.exec()
