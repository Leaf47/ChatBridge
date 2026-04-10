"""
クリップボード操作モジュール

ゲーム内のチャット欄からテキストを取得し、翻訳結果をペーストする。
Win32 API (SendInput) を使ってキー入力をシミュレートする。
"""

import ctypes
import ctypes.wintypes
import time
import pyperclip
from typing import Optional


# Win32 API の定数
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_ALT = 0x12
VK_RETURN = 0x0D


class KEYBDINPUT(ctypes.Structure):
    """キーボード入力を表す Win32 構造体"""
    _fields_ = [
        ("wVk", ctypes.wintypes.WORD),
        ("wScan", ctypes.wintypes.WORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT(ctypes.Structure):
    """入力イベントを表す Win32 構造体"""
    class _INPUT(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]

    _anonymous_ = ("_input",)
    _fields_ = [
        ("type", ctypes.wintypes.DWORD),
        ("_input", _INPUT),
    ]


def _send_key(vk_code: int, key_up: bool = False) -> None:
    """Win32 SendInput でキー入力を送信する"""
    flags = KEYEVENTF_KEYUP if key_up else 0
    inp = INPUT(
        type=INPUT_KEYBOARD,
        ki=KEYBDINPUT(
            wVk=vk_code,
            wScan=0,
            dwFlags=flags,
            time=0,
            dwExtraInfo=None,
        ),
    )
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def _press_key(vk_code: int) -> None:
    """キーを押す"""
    _send_key(vk_code, key_up=False)


def _release_key(vk_code: int) -> None:
    """キーを離す"""
    _send_key(vk_code, key_up=True)


def _key_combo(modifier_vk: int, key_vk: int, delay: float = 0.05) -> None:
    """修飾キー + キーの組み合わせを送信する"""
    _press_key(modifier_vk)
    time.sleep(delay)
    _press_key(key_vk)
    time.sleep(delay)
    _release_key(key_vk)
    time.sleep(delay)
    _release_key(modifier_vk)
    time.sleep(delay)


def _release_all_modifiers() -> None:
    """
    すべての修飾キーをリリースする。
    ホットキー（例: Ctrl+J）の後、ユーザーがまだ Ctrl を押している場合に
    クリップボード操作と競合しないようにする。
    """
    _release_key(VK_CONTROL)
    _release_key(VK_SHIFT)
    _release_key(VK_ALT)


class ClipboardHandler:
    """クリップボード操作と翻訳ワークフローを管理するクラス"""

    def __init__(self):
        self._saved_clipboard: Optional[str] = None

    def grab_text(self) -> str:
        """
        アクティブウィンドウのテキスト入力欄からテキストを取得する。

        手順:
        1. 現在のクリップボード内容を退避
        2. 修飾キーをすべてリリース（ユーザーがまだ押している場合の競合防止）
        3. Ctrl+A で全選択
        4. Ctrl+C でコピー
        5. クリップボードからテキストを取得
        """
        # クリップボードの内容を退避
        try:
            self._saved_clipboard = pyperclip.paste()
        except Exception:
            self._saved_clipboard = ""

        # ユーザーがまだ修飾キーを押している可能性があるので、
        # まず全ての修飾キーをリリースしてから操作開始
        _release_all_modifiers()
        time.sleep(0.15)

        # Ctrl+A（全選択）
        _key_combo(VK_CONTROL, 0x41)  # 0x41 = 'A'
        time.sleep(0.05)

        # Ctrl+C（コピー）
        _key_combo(VK_CONTROL, 0x43)  # 0x43 = 'C'
        time.sleep(0.15)

        # クリップボードからテキストを取得
        try:
            text = pyperclip.paste()
        except Exception:
            text = ""

        return text.strip()

    def paste_text(self, text: str) -> None:
        """
        テキストをアクティブウィンドウにペーストする。
        """
        # 修飾キーを全てリリース
        _release_all_modifiers()
        time.sleep(0.05)

        # Ctrl+A（全選択）
        _key_combo(VK_CONTROL, 0x41)
        time.sleep(0.05)

        # 翻訳結果をクリップボードにセット
        pyperclip.copy(text)
        time.sleep(0.05)

        # Ctrl+V（ペースト）
        _key_combo(VK_CONTROL, 0x56)  # 0x56 = 'V'
        time.sleep(0.1)

        # 元のクリップボード内容を復元
        self._restore_clipboard()

    def restore_original(self) -> None:
        """キャンセル時にクリップボードを復元する"""
        self._restore_clipboard()

    def _restore_clipboard(self) -> None:
        """退避しておいたクリップボード内容を復元する"""
        if self._saved_clipboard is not None:
            try:
                # 少し待ってからクリップボードを復元
                time.sleep(0.2)
                pyperclip.copy(self._saved_clipboard)
            except Exception:
                pass
            finally:
                self._saved_clipboard = None
