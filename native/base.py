"""
プラットフォーム抽象化 — 基底クラス

OS 固有の処理をインターフェースとして定義する。
各プラットフォーム（Windows / macOS）はこのクラスを継承して実装する。
"""

from abc import ABC, abstractmethod
from typing import Any


class BasePlatform(ABC):
    """プラットフォーム固有処理の抽象基底クラス"""

    # --- 権限管理 ---

    @abstractmethod
    def is_admin(self) -> bool:
        """現在のプロセスが管理者/特権で実行されているかチェックする"""
        pass

    @abstractmethod
    def relaunch_as_admin(self) -> None:
        """管理者/特権権限でアプリを再起動する"""
        pass

    # --- 二重起動防止 ---

    @abstractmethod
    def create_single_instance_lock(self) -> tuple[Any, bool]:
        """
        二重起動防止用のロックを作成する。

        Returns:
            (lock_handle, already_running)
            - lock_handle: ロックのハンドル（プロセス終了まで保持する）
            - already_running: 既に別インスタンスが起動中の場合 True
        """
        pass

    # --- 自動起動 ---

    @abstractmethod
    def get_auto_start(self) -> bool:
        """自動起動が登録されているか確認する"""
        pass

    @abstractmethod
    def set_auto_start(self, enabled: bool) -> bool:
        """
        自動起動を設定する。

        Args:
            enabled: True で登録、False で解除

        Returns:
            操作が成功した場合 True
        """
        pass

    # --- ウィンドウ管理 ---

    @abstractmethod
    def show_window_no_activate(self, window_handle: int) -> None:
        """フォーカスを奪わずにウィンドウを最前面に表示する"""
        pass

    # --- 入力状態 ---

    @abstractmethod
    def is_modifier_pressed(self) -> bool:
        """修飾キー（Ctrl/Shift/Alt 等）が物理的に押されているかチェック"""
        pass

    # --- ユーティリティ ---

    @abstractmethod
    def get_exe_path(self) -> str:
        """実行ファイルのパスを返す（自動起動登録等で使用）"""
        pass
