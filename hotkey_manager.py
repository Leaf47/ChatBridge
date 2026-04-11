"""
グローバルホットキー管理モジュール

pynput を使ってゲーム中でも動作するグローバルホットキーを検出する。
pynput のリスナーはアプリ全体で一つだけ使用する（複数リスナーの競合を避けるため）。
オーバーレイ表示中の Enter/Esc の抑制もこのリスナーで統合的に処理する。
"""

import threading
from typing import Callable, Optional, TYPE_CHECKING
from pynput import keyboard


# ホットキー文字列からキーオブジェクトへの変換マッピング
MODIFIER_MAP = {
    "ctrl": keyboard.Key.ctrl_l,
    "alt": keyboard.Key.alt_l,
    "shift": keyboard.Key.shift_l,
}


def parse_hotkey(hotkey_str: str) -> tuple[set, Optional[keyboard.KeyCode]]:
    """
    ホットキー文字列をパースして (修飾キーのセット, メインキー) を返す。

    例: "alt+j" → ({Key.alt_l}, KeyCode(char='j'))
         "ctrl+shift+k" → ({Key.ctrl_l, Key.shift_l}, KeyCode(char='k'))

    Args:
        hotkey_str: "alt+j" 形式のホットキー文字列

    Returns:
        (修飾キーのセット, メインキー) のタプル
    """
    parts = hotkey_str.lower().strip().split("+")
    modifiers = set()
    main_key = None

    for part in parts:
        part = part.strip()
        if part in MODIFIER_MAP:
            modifiers.add(MODIFIER_MAP[part])
        else:
            # 通常のキー
            if len(part) == 1:
                main_key = keyboard.KeyCode.from_char(part)
            else:
                # 特殊キー（enter, space 等）
                try:
                    main_key = getattr(keyboard.Key, part)
                except AttributeError:
                    main_key = keyboard.KeyCode.from_char(part[0])

    return modifiers, main_key


class HotkeyManager:
    """
    グローバルホットキーの登録・検出を管理するクラス。

    アプリ全体で唯一の pynput Listener を管理し、
    ホットキー検出とオーバーレイのキー処理を統合する。
    """

    # WM_KEYDOWN のメッセージコード（キー押下時のみ処理するため）
    _WM_KEYDOWN = 0x0100
    _WM_SYSKEYDOWN = 0x0104

    def __init__(self):
        self._listener: Optional[keyboard.Listener] = None
        self._callbacks: dict[str, Callable] = {}
        self._hotkeys: dict[str, tuple[set, Optional[keyboard.KeyCode]]] = {}
        self._pressed_keys: set = set()
        self._enabled: bool = True
        self._lock = threading.Lock()
        # オーバーレイへの参照（Enter/Esc の抑制と通知用）
        self._overlay = None

    def register(self, hotkey_str: str, callback: Callable) -> None:
        """
        ホットキーとコールバックを登録する。

        Args:
            hotkey_str: "alt+j" 形式のホットキー文字列
            callback: ホットキーが押されたときに呼ばれる関数
        """
        modifiers, main_key = parse_hotkey(hotkey_str)
        self._hotkeys[hotkey_str] = (modifiers, main_key)
        self._callbacks[hotkey_str] = callback

    def unregister(self, hotkey_str: str) -> None:
        """ホットキーの登録を解除する"""
        self._hotkeys.pop(hotkey_str, None)
        self._callbacks.pop(hotkey_str, None)

    def update_hotkey(self, old_hotkey: str, new_hotkey: str, callback: Callable) -> None:
        """ホットキーを変更する（古いキーを解除して新しいキーを登録）"""
        self.unregister(old_hotkey)
        self.register(new_hotkey, callback)

    def set_overlay(self, overlay) -> None:
        """
        オーバーレイへの参照を設定する。
        オーバーレイ表示中に Enter/Esc を抑制して overlay に通知するために必要。
        """
        self._overlay = overlay

    def set_enabled(self, enabled: bool) -> None:
        """ホットキーの有効/無効を切り替える"""
        self._enabled = enabled

    def start(self) -> None:
        """ホットキーリスナーを開始する"""
        if self._listener is not None:
            self.stop()

        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
            win32_event_filter=self._win32_key_filter,
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        """ホットキーリスナーを停止する"""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        self._pressed_keys.clear()

    def _on_press(self, key) -> None:
        """キーが押されたときのハンドラ"""
        if not self._enabled:
            return

        # オーバーレイ表示中の Enter/Esc は win32_event_filter で処理済みなので、
        # ここではホットキーの照合のみ行う
        with self._lock:
            # 修飾キーの正規化（左右を区別しない）
            normalized = self._normalize_key(key)
            self._pressed_keys.add(normalized)

            # 登録されたホットキーと照合
            for hotkey_str, (modifiers, main_key) in self._hotkeys.items():
                if self._check_hotkey(modifiers, main_key):
                    callback = self._callbacks.get(hotkey_str)
                    if callback:
                        # コールバックは別スレッドで実行（リスナーをブロックしない）
                        threading.Thread(target=callback, daemon=True).start()

    def _on_release(self, key) -> None:
        """キーが離されたときのハンドラ"""
        with self._lock:
            normalized = self._normalize_key(key)
            self._pressed_keys.discard(normalized)

    def _check_hotkey(self, modifiers: set, main_key) -> bool:
        """現在押されているキーがホットキーと一致するかチェック"""
        # すべての修飾キーが押されているか
        for mod in modifiers:
            if mod not in self._pressed_keys:
                return False

        # メインキーが押されているか
        if main_key is not None and main_key not in self._pressed_keys:
            return False

        return True

    @staticmethod
    def _normalize_key(key) -> keyboard.Key | keyboard.KeyCode:
        """左右のキーを区別せずに正規化する"""
        # 右Ctrlを左Ctrlとして扱う
        if key == keyboard.Key.ctrl_r:
            return keyboard.Key.ctrl_l
        if key == keyboard.Key.alt_r:
            return keyboard.Key.alt_l
        if key == keyboard.Key.shift_r:
            return keyboard.Key.shift_l

        # KeyCode の場合、仮想キーコード(vk)を使って正規化する
        # Ctrl を押しながらキーを押すと char が制御文字になるため、
        # vk から実際のキーを判定する必要がある
        if isinstance(key, keyboard.KeyCode):
            # vk が A-Z の範囲 (65-90) なら、対応する小文字に変換
            if key.vk is not None and 65 <= key.vk <= 90:
                return keyboard.KeyCode.from_char(chr(key.vk + 32))  # 小文字化
            # vk がない場合は char で正規化
            if key.char and key.char.isprintable():
                return keyboard.KeyCode.from_char(key.char.lower())

        return key

    def _win32_key_filter(self, msg, data) -> None:
        """
        Win32 低レベルキーボードフック用フィルタ。

        オーバーレイ表示中に Enter/Esc キーをゲームに届かないよう抑制し、
        overlay にキー入力を通知する。その他のキーはそのまま通過させる。

        重要: suppress_event() は SuppressException を raise するため、
        その後のコードは実行されない。overlay.handle_key() は必ず
        suppress_event() より前に呼ぶこと。
        """
        # オーバーレイが未設定または非表示なら何もしない
        if self._overlay is None or not self._overlay.overlay_visible:
            return

        from overlay import TranslationOverlay
        vk = data.vkCode

        if vk in (TranslationOverlay.VK_RETURN, TranslationOverlay.VK_ESCAPE):
            # キー押下時のみ overlay に通知（キーリリース時は抑制のみ）
            if msg in (self._WM_KEYDOWN, self._WM_SYSKEYDOWN):
                self._overlay.handle_key(vk)

            # ゲームにキーを届かないように抑制
            # ※ SuppressException が raise されるため、これ以降のコードは実行されない
            self._listener.suppress_event()

