"""
システムトレイアイコン管理モジュール

pystray を使ってシステムトレイにアイコンを表示し、
右クリックメニューから各機能にアクセスできるようにする。
"""

import threading
from typing import Callable, Optional
from PIL import Image, ImageDraw, ImageFont
import pystray
from pystray import MenuItem as Item


def _create_default_icon() -> Image.Image:
    """デフォルトのトレイアイコンを生成する（テキストベース）"""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 背景の角丸矩形（紫色）
    draw.rounded_rectangle(
        [(2, 2), (size - 2, size - 2)],
        radius=12,
        fill=(139, 92, 246, 255),  # 紫色 (#8b5cf6)
    )

    # テキスト "J" を中央に描画
    try:
        font = ImageFont.truetype("segoeui.ttf", 36)
    except (OSError, IOError):
        font = ImageFont.load_default()

    # テキストのバウンディングボックスを取得して中央寄せ
    bbox = draw.textbbox((0, 0), "J", font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - 2

    draw.text((x, y), "J", fill=(255, 255, 255, 255), font=font)

    return img


class TrayApp:
    """システムトレイアイコンとメニューを管理するクラス"""

    def __init__(
        self,
        on_settings: Callable,
        on_toggle_pause: Callable,
        on_quit: Callable,
        on_engine_change: Callable,
        current_engine: str = "mymemory",
    ):
        """
        Args:
            on_settings: 設定画面を開くコールバック
            on_toggle_pause: 一時停止/再開のコールバック
            on_quit: アプリ終了のコールバック
            on_engine_change: エンジン変更のコールバック（エンジン名を引数に取る）
            current_engine: 現在の翻訳エンジン名
        """
        self._on_settings = on_settings
        self._on_toggle_pause = on_toggle_pause
        self._on_quit = on_quit
        self._on_engine_change = on_engine_change
        self._current_engine = current_engine
        self._paused = False
        self._icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """トレイアイコンを表示する（別スレッドで実行）"""
        icon_image = _create_default_icon()
        menu = self._create_menu()

        self._icon = pystray.Icon(
            name="JA2EN",
            icon=icon_image,
            title="JA2EN - ゲーム内翻訳ツール",
            menu=menu,
        )

        # pystray は自身のイベントループを持つので別スレッドで実行
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """トレイアイコンを停止する"""
        if self._icon:
            self._icon.stop()
            self._icon = None

    def update_engine(self, engine_name: str) -> None:
        """現在のエンジン表示を更新する"""
        self._current_engine = engine_name
        if self._icon:
            self._icon.menu = self._create_menu()
            self._icon.update_menu()

    def _create_menu(self) -> pystray.Menu:
        """右クリックメニューを作成する"""
        return pystray.Menu(
            Item("⚙️ 設定を開く", self._handle_settings),
            pystray.Menu.SEPARATOR,
            Item(
                "🔄 翻訳エンジン",
                pystray.Menu(
                    Item(
                        "MyMemory（無料）",
                        lambda: self._handle_engine_change("mymemory"),
                        checked=lambda item: self._current_engine == "mymemory",
                        radio=True,
                    ),
                    Item(
                        "DeepL",
                        lambda: self._handle_engine_change("deepl"),
                        checked=lambda item: self._current_engine == "deepl",
                        radio=True,
                    ),
                    Item(
                        "Google",
                        lambda: self._handle_engine_change("google"),
                        checked=lambda item: self._current_engine == "google",
                        radio=True,
                    ),
                ),
            ),
            pystray.Menu.SEPARATOR,
            Item(
                lambda text: "▶️ 再開" if self._paused else "⏸️ 一時停止",
                self._handle_toggle_pause,
            ),
            pystray.Menu.SEPARATOR,
            Item("❌ 終了", self._handle_quit),
        )

    def _handle_settings(self, icon=None, item=None) -> None:
        """設定画面を開く"""
        self._on_settings()

    def _handle_toggle_pause(self, icon=None, item=None) -> None:
        """一時停止/再開を切り替える"""
        self._paused = not self._paused
        self._on_toggle_pause(self._paused)
        if self._icon:
            self._icon.menu = self._create_menu()
            self._icon.update_menu()

    def _handle_engine_change(self, engine_name: str) -> None:
        """翻訳エンジンを変更する"""
        self._current_engine = engine_name
        self._on_engine_change(engine_name)
        if self._icon:
            self._icon.menu = self._create_menu()
            self._icon.update_menu()

    def _handle_quit(self, icon=None, item=None) -> None:
        """アプリを終了する"""
        self.stop()
        self._on_quit()
