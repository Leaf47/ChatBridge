"""
プラットフォーム抽象化 — 自動選択モジュール

sys.platform に基づいて適切なプラットフォーム実装を返す。
将来 macOS 対応を追加する場合は、ここに macos.py のインポートを追加するだけ。
"""

import sys
from typing import Optional

from native.base import BasePlatform

# シングルトンインスタンス
_instance: Optional[BasePlatform] = None


def get_platform() -> BasePlatform:
    """
    現在の OS に対応するプラットフォーム実装を返す（シングルトン）。

    Returns:
        BasePlatform の具象インスタンス

    Raises:
        NotImplementedError: 未対応のプラットフォームの場合
    """
    global _instance

    if _instance is not None:
        return _instance

    if sys.platform == "win32":
        from native.windows import WindowsPlatform
        _instance = WindowsPlatform()
    elif sys.platform == "darwin":
        # Phase 2.5 で実装予定
        raise NotImplementedError(
            "macOS はまだサポートされていません。Phase 2.5 で対応予定です。"
        )
    else:
        raise NotImplementedError(
            f"未対応のプラットフォーム: {sys.platform}"
        )

    return _instance
