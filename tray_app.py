"""
システムトレイアイコン管理モジュール

pystray を使ってシステムトレイにアイコンを表示し、
右クリックメニューから各機能にアクセスできるようにする。
"""

import os
import threading
from typing import Callable, Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import pystray
from pystray import MenuItem as Item

from i18n import t


# アイコンファイルのパス
_ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
_ICON_PATH = os.path.join(_ASSETS_DIR, "icon.png")


def _load_icon(paused: bool = False) -> Image.Image:
    """
    トレイアイコンを読み込む。
    assets/icon.png がなければフォールバックで生成する。
    一時停止時はグレースケール + 半透明にする。
    """
    size = 64

    # アイコン画像の読み込み
    if os.path.isfile(_ICON_PATH):
        img = Image.open(_ICON_PATH).convert("RGBA").resize((size, size), Image.LANCZOS)
    else:
        # フォールバック: コード生成アイコン
        img = _create_fallback_icon(size)

    if paused:
        # グレースケールに変換して一時停止を表現
        gray = img.convert("L").convert("RGBA")
        # 半透明にする
        alpha = gray.split()[3]
        alpha = alpha.point(lambda p: int(p * 0.5))
        gray.putalpha(alpha)
        # 右下に⏸マーク
        draw = ImageDraw.Draw(gray)
        bar_w, bar_h = 4, 14
        gap = 4
        bx = size - 20
        by = size - 20
        draw.rectangle([(bx, by), (bx + bar_w, by + bar_h)], fill=(255, 255, 255, 255))
        draw.rectangle([(bx + bar_w + gap, by), (bx + bar_w * 2 + gap, by + bar_h)], fill=(255, 255, 255, 255))
        return gray

    return img


def _create_fallback_icon(size: int = 64) -> Image.Image:
    """アイコンファイルがない場合のフォールバックアイコン"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        [(2, 2), (size - 2, size - 2)],
        radius=12,
        fill=(139, 92, 246, 255),
    )
    try:
        font = ImageFont.truetype("segoeui.ttf", 28)
    except (OSError, IOError):
        font = ImageFont.load_default()

    text = "CB"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(((size - tw) // 2, (size - th) // 2 - 2), text, fill=(255, 255, 255, 255), font=font)
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
        icon_image = _load_icon(paused=False)
        menu = self._create_menu()

        self._icon = pystray.Icon(
            name="ChatBridge",
            icon=icon_image,
            title=t("tray_title"),
            menu=menu,
        )

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
            Item(t("tray_settings"), self._handle_settings),
            pystray.Menu.SEPARATOR,
            Item(
                t("tray_engine"),
                pystray.Menu(
                    Item(
                        t("tray_engine_mymemory"),
                        lambda: self._handle_engine_change("mymemory"),
                        checked=lambda item: self._current_engine == "mymemory",
                        radio=True,
                    ),
                    Item(
                        t("tray_engine_deepl"),
                        lambda: None,
                        enabled=False,
                    ),
                    Item(
                        t("tray_engine_google"),
                        lambda: None,
                        enabled=False,
                    ),
                ),
            ),
            pystray.Menu.SEPARATOR,
            Item(
                lambda text: t("tray_resume") if self._paused else t("tray_pause"),
                self._handle_toggle_pause,
            ),
            pystray.Menu.SEPARATOR,
            Item(t("tray_quit"), self._handle_quit),
        )

    def _handle_settings(self, icon=None, item=None) -> None:
        """設定画面を開く"""
        self._on_settings()

    def _handle_toggle_pause(self, icon=None, item=None) -> None:
        """一時停止/再開を切り替える"""
        self._paused = not self._paused
        self._on_toggle_pause(self._paused)

        if self._icon:
            self._icon.icon = _load_icon(paused=self._paused)
            self._icon.title = t("tray_title_paused") if self._paused else t("tray_title")
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
