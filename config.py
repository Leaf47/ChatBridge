"""
ChatBridge 設定管理モジュール

config.json の読み書きとデフォルト値の管理を担当する。
"""

import json
import os
from pathlib import Path
from typing import Any

import sys

# 設定ファイルのパス
# exe化されている場合は exe と同じディレクトリ、そうでなければスクリプトのディレクトリ
if getattr(sys, 'frozen', False):
    CONFIG_DIR = Path(os.path.dirname(sys.executable))
else:
    CONFIG_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = CONFIG_DIR / "config.json"

# デフォルト設定
DEFAULT_CONFIG = {
    # ホットキー
    "hotkey_translate": "alt+j",

    # 翻訳エンジン（mymemory / deepl / google）
    "translator": "mymemory",

    # 翻訳の言語設定
    "source_lang": "ja",
    "target_lang": "en",

    # UI表示言語（ja / en、外部JSONで追加可能）
    "ui_lang": "ja",

    # オーバーレイ設定
    "overlay_position": "cursor",  # cursor / center / corner
    "overlay_opacity": 0.9,

    # 確認なしで即ペーストするか
    "auto_paste": False,

    # 初回セットアップ完了フラグ（初回起動ダイアログ表示後に True になる）
    "setup_complete": False,

    # 言語選択済みフラグ（言語選択ダイアログ表示後に True になる）
    "lang_selected": False,

    # Windows 起動時に自動起動（タスクスケジューラで管理者権限起動）
    "auto_start": False,

    # MyMemory メールアドレス（設定すると1日5,000文字→50,000文字に増加）
    "mymemory_email": "",

    # APIキー（将来の拡張用）
    "api_keys": {
        "deepl": "",
        "google": "",
    },
}


class Config:
    """設定の読み込み・保存・アクセスを管理するクラス"""

    def __init__(self):
        self._data: dict = {}
        self.is_first_launch = False
        self.load()

    def load(self) -> None:
        """設定ファイルを読み込む。なければデフォルトを生成する。"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
                # デフォルト設定にないキーがあれば補完
                self._merge_defaults()
            except (json.JSONDecodeError, IOError):
                # ファイルが壊れていたらデフォルトで上書き
                self._data = DEFAULT_CONFIG.copy()
                self.save()
        else:
            self._data = DEFAULT_CONFIG.copy()
            self.save()

        # 初回起動判定: setup_complete が False なら初回起動
        self.is_first_launch = not self._data.get("setup_complete", False)

    def save(self) -> None:
        """現在の設定をファイルに保存する。"""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"設定ファイルの保存に失敗しました: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """設定値を取得する。ドット区切りでネストしたキーにもアクセス可能。"""
        keys = key.split(".")
        value = self._data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """設定値を更新する。ドット区切りでネストしたキーにもアクセス可能。"""
        keys = key.split(".")
        data = self._data
        for k in keys[:-1]:
            if k not in data or not isinstance(data[k], dict):
                data[k] = {}
            data = data[k]
        data[keys[-1]] = value

    @property
    def data(self) -> dict:
        """設定データの辞書を返す（読み取り専用）"""
        return self._data.copy()

    def _merge_defaults(self) -> None:
        """デフォルト設定に存在するが、現在の設定に無いキーを補完する。"""
        self._data = self._deep_merge(DEFAULT_CONFIG, self._data)

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        """2つの辞書を再帰的にマージする。override が優先。"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = Config._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
