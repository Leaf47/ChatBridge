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


def _create_icon(paused: bool = False) -> Image.Image:
    """
    トレイアイコンを生成する。
    通常時: 紫色の「J」
    一時停止時: グレーの「J」に一時停止マーク
    """
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if paused:
        # 一時停止: グレー背景
        bg_color = (107, 114, 128, 255)  # グレー (#6b7280)
    else:
        # 通常: 紫色背景
        bg_color = (139, 92, 246, 255)  # 紫色 (#8b5cf6)

    # 背景の角丸矩形
    draw.rounded_rectangle(
        [(2, 2), (size - 2, size - 2)],
        radius=12,
        fill=bg_color,
    )

    # テキスト "J" を中央に描画
    try:
        font = ImageFont.truetype("segoeui.ttf", 36)
    except (OSError, IOError):
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), "J", font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - 2

    draw.text((x, y), "J", fill=(255, 255, 255, 255), font=font)

    # 一時停止時: 右下に⏸マーク（小さい二本線）
    if paused:
        bar_w, bar_h = 4, 14
        gap = 4
        # 右下に配置
        bx = size - 20
        by = size - 20
        draw.rectangle([(bx, by), (bx + bar_w, by + bar_h)], fill=(255, 255, 255, 255))
        draw.rectangle([(bx + bar_w + gap, by), (bx + bar_w * 2 + gap, by + bar_h)], fill=(255, 255, 255, 255))

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
        icon_image = _create_icon(paused=False)
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
                "🔄 翻訳エンジン: MyMemory",
                pystray.Menu(
                    Item(
                        "MyMemory（無料）",
                        lambda: self._handle_engine_change("mymemory"),
                        checked=lambda item: self._current_engine == "mymemory",
                        radio=True,
                    ),
                    Item(
                        "DeepL（準備中）",
                        lambda: None,  # 何もしない
                        enabled=False,
                    ),
                    Item(
                        "Google（準備中）",
                        lambda: None,  # 何もしない
                        enabled=False,
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

        # アイコンを更新（色とマーク変更）
        if self._icon:
            self._icon.icon = _create_icon(paused=self._paused)
            title = "JA2EN - ⏸️ 一時停止中" if self._paused else "JA2EN - ゲーム内翻訳ツール"
            self._icon.title = title
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
