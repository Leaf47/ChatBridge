"""
OCR エンジン — 抽象基底クラス

すべての OCR エンジンはこのクラスを継承して実装する。
translator/base.py と同様のインターフェース設計。
"""

from abc import ABC, abstractmethod
import numpy as np


class BaseOCR(ABC):
    """OCR エンジンの抽象基底クラス"""

    @abstractmethod
    def recognize(self, image: np.ndarray, lang: str = "eng") -> str:
        """
        画像からテキストを認識する。

        Args:
            image: RGB の numpy 配列 (H, W, 3)
            lang: OCR 言語コード（例: "eng", "jpn", "jpn+eng"）

        Returns:
            認識されたテキスト文字列
        """
        pass

    @abstractmethod
    def name(self) -> str:
        """エンジン名を返す"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """エンジンが利用可能かどうかを返す"""
        pass
