"""
グローバルホットキー管理モジュール

pynput を使ってゲーム中でも動作するグローバルホットキーを検出する。
"""

import threading
from typing import Callable, Optional
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

    例: "ctrl+j" → ({Key.ctrl_l}, KeyCode(char='j'))
         "ctrl+shift+k" → ({Key.ctrl_l, Key.shift_l}, KeyCode(char='k'))

    Args:
        hotkey_str: "ctrl+j" 形式のホットキー文字列

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
    """グローバルホットキーの登録・検出を管理するクラス"""

    def __init__(self):
        self._listener: Optional[keyboard.Listener] = None
        self._callbacks: dict[str, Callable] = {}
        self._hotkeys: dict[str, tuple[set, Optional[keyboard.KeyCode]]] = {}
        self._pressed_keys: set = set()
        self._enabled: bool = True
        self._lock = threading.Lock()

    def register(self, hotkey_str: str, callback: Callable) -> None:
        """
        ホットキーとコールバックを登録する。

        Args:
            hotkey_str: "ctrl+j" 形式のホットキー文字列
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
        # KeyCode の場合、小文字に正規化
        if isinstance(key, keyboard.KeyCode) and key.char:
            return keyboard.KeyCode.from_char(key.char.lower())
        return key
