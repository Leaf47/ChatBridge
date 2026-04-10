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

# Win32 API の関数
user32 = ctypes.windll.user32


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
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


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


def _is_modifier_pressed() -> bool:
    """修飾キー（Ctrl/Shift/Alt）が物理的に押されているかチェック"""
    for vk in (VK_CONTROL, VK_SHIFT, VK_ALT):
        # GetAsyncKeyState の最上位ビットが 1 ならキーが押されている
        if user32.GetAsyncKeyState(vk) & 0x8000:
            return True
    return False


def _wait_for_modifier_release(timeout: float = 2.0) -> None:
    """
    ユーザーが修飾キーを物理的に離すまで待機する。
    SendInput でリリースを偽装するとフォーカスが飛んだり
    pynput のキー状態が壊れる問題を回避する。
    """
    start = time.time()
    while _is_modifier_pressed():
        if time.time() - start > timeout:
            break  # タイムアウト（安全弁）
        time.sleep(0.02)  # 20ms間隔でポーリング


def _get_foreground_window() -> int:
    """現在のフォアグラウンドウィンドウのハンドルを取得する"""
    return user32.GetForegroundWindow()


def _ensure_foreground(hwnd: int) -> None:
    """指定したウィンドウをフォアグラウンドにする（失敗しても続行）"""
    if hwnd and user32.GetForegroundWindow() != hwnd:
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.05)


class ClipboardHandler:
    """クリップボード操作と翻訳ワークフローを管理するクラス"""

    def __init__(self):
        self._saved_clipboard: Optional[str] = None
        self._target_hwnd: Optional[int] = None

    def grab_text(self) -> str:
        """
        アクティブウィンドウのテキスト入力欄からテキストを取得する。
        """
        # ホットキーが押された時点のフォアグラウンドウィンドウを記録
        self._target_hwnd = _get_foreground_window()

        # クリップボードの内容を退避
        try:
            self._saved_clipboard = pyperclip.paste()
        except Exception:
            self._saved_clipboard = ""

        # ユーザーが修飾キーを物理的に離すまで待つ
        # （SendInput でリリースを偽装するとフォーカスが飛ぶ問題を回避）
        _wait_for_modifier_release()

        # ターゲットウィンドウにフォーカスがあることを確認
        _ensure_foreground(self._target_hwnd)

        # クリップボードをクリアして、コピー結果を判定できるようにする
        pyperclip.copy("")
        time.sleep(0.05)

        # まず Ctrl+C で選択中のテキストだけを取得
        _key_combo(VK_CONTROL, 0x43)  # 0x43 = 'C'
        time.sleep(0.15)

        try:
            text = pyperclip.paste()
        except Exception:
            text = ""

        # 選択テキストが取れなかった場合は Ctrl+A → Ctrl+C にフォールバック
        if not text.strip():
            _key_combo(VK_CONTROL, 0x41)  # 0x41 = 'A' (全選択)
            time.sleep(0.05)
            _key_combo(VK_CONTROL, 0x43)  # 0x43 = 'C' (コピー)
            time.sleep(0.15)

            try:
                text = pyperclip.paste()
            except Exception:
                text = ""

        return text.strip()

    def paste_text(self, text: str) -> None:
        """テキストをアクティブウィンドウにペーストする。"""
        # ユーザーが修飾キーを離すまで待つ
        _wait_for_modifier_release()

        # ターゲットウィンドウにフォーカスを確認
        if self._target_hwnd:
            _ensure_foreground(self._target_hwnd)

        # Ctrl+A（全選択 — 元のテキストを上書きするため）
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
                time.sleep(0.2)
                pyperclip.copy(self._saved_clipboard)
            except Exception:
                pass
            finally:
                self._saved_clipboard = None
