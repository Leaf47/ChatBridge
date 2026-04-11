"""
クリップボード操作モジュール

ゲーム内のチャット欄からテキストを取得し、翻訳結果をペーストする。
pynput の Controller を使ってキー入力をシミュレートする。
"""

import time
import pyperclip
from typing import Optional
from pynput.keyboard import Controller, Key

# プラットフォーム抽象化レイヤー
from native import get_platform


# キーボードコントローラー（pynput）
_kb = Controller()


def _wait_for_modifier_release(timeout: float = 2.0) -> None:
    """ユーザーが修飾キーを物理的に離すまで待機する"""
    plat = get_platform()
    start = time.time()
    while plat.is_modifier_pressed():
        if time.time() - start > timeout:
            break
        time.sleep(0.02)


def _ctrl_combo(char: str, delay: float = 0.05) -> None:
    """Ctrl + キーの組み合わせを pynput で送信する"""
    _kb.press(Key.ctrl)
    time.sleep(delay)
    _kb.press(char)
    time.sleep(delay)
    _kb.release(char)
    time.sleep(delay)
    _kb.release(Key.ctrl)
    time.sleep(delay)


class ClipboardHandler:
    """クリップボード操作と翻訳ワークフローを管理するクラス"""

    def __init__(self):
        self._saved_clipboard: Optional[str] = None

    def grab_text(self) -> str:
        """
        アクティブウィンドウのテキスト入力欄からテキストを取得する。

        手順:
        1. クリップボード退避
        2. ユーザーが修飾キーを離すまで待機
        3. Ctrl+C で選択テキストを取得
        4. なければ Ctrl+A → Ctrl+C で全選択
        """
        # クリップボードの内容を退避
        try:
            self._saved_clipboard = pyperclip.paste()
        except Exception:
            self._saved_clipboard = ""

        # ユーザーが修飾キーを物理的に離すまで待つ
        _wait_for_modifier_release()
        time.sleep(0.05)

        # クリップボードをクリア
        pyperclip.copy("")
        time.sleep(0.05)

        # まず Ctrl+C で選択中のテキストだけを取得
        _ctrl_combo('c')
        time.sleep(0.15)

        try:
            text = pyperclip.paste()
        except Exception:
            text = ""

        # 選択テキストが取れなかった場合は Ctrl+A → Ctrl+C にフォールバック
        if not text.strip():
            _ctrl_combo('a')  # 全選択
            time.sleep(0.05)
            _ctrl_combo('c')  # コピー
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
        time.sleep(0.05)

        # Ctrl+A（全選択 — 元のテキストを上書き）
        _ctrl_combo('a')
        time.sleep(0.05)

        # 翻訳結果をクリップボードにセット
        pyperclip.copy(text)
        time.sleep(0.05)

        # Ctrl+V（ペースト）
        _ctrl_combo('v')
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
