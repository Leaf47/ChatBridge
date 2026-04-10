"""
翻訳エンジンの抽象基底クラス

すべての翻訳エンジンはこのクラスを継承して実装する。
将来ローカル翻訳モデルを追加する場合も、このインターフェースを実装すればOK。
"""

from abc import ABC, abstractmethod


class BaseTranslator(ABC):
    """翻訳エンジンの共通インターフェース"""

    @abstractmethod
    def translate(self, text: str, source: str = "ja", target: str = "en") -> str:
        """
        テキストを翻訳して結果を返す。

        Args:
            text: 翻訳する原文
            source: 原文の言語コード（デフォルト: "ja"）
            target: 翻訳先の言語コード（デフォルト: "en"）

        Returns:
            翻訳されたテキスト

        Raises:
            TranslationError: 翻訳に失敗した場合
        """
        pass

    @abstractmethod
    def name(self) -> str:
        """翻訳エンジンの表示名を返す"""
        pass

    @abstractmethod
    def requires_api_key(self) -> bool:
        """APIキーが必要かどうかを返す"""
        pass


class TranslationError(Exception):
    """翻訳処理中のエラーを表す例外"""
    pass
