"""
翻訳エンジンパッケージ

ファクトリパターンで設定に応じたエンジンを生成する。
"""

from .base import BaseTranslator, TranslationError
from .mymemory_translator import MyMemoryTranslator
from .deepl_translator import DeepLTranslator
from .google_translator import GoogleTranslator

# 利用可能な翻訳エンジンの一覧
AVAILABLE_TRANSLATORS = {
    "mymemory": MyMemoryTranslator,
    "deepl": DeepLTranslator,
    "google": GoogleTranslator,
}


def create_translator(
    engine_name: str,
    api_keys: dict = None,
    mymemory_email: str = "",
) -> BaseTranslator:
    """
    設定に応じた翻訳エンジンのインスタンスを生成する。

    Args:
        engine_name: エンジン名（mymemory / deepl / google）
        api_keys: APIキーの辞書 {"deepl": "xxx", "google": "xxx"}
        mymemory_email: MyMemory用メールアドレス（使用量10倍）

    Returns:
        翻訳エンジンのインスタンス

    Raises:
        ValueError: 不明なエンジン名の場合
    """
    if api_keys is None:
        api_keys = {}

    engine_name = engine_name.lower()

    if engine_name not in AVAILABLE_TRANSLATORS:
        raise ValueError(
            f"不明な翻訳エンジン: {engine_name}\n"
            f"利用可能なエンジン: {', '.join(AVAILABLE_TRANSLATORS.keys())}"
        )

    translator_class = AVAILABLE_TRANSLATORS[engine_name]

    # エンジンごとに適切なパラメータを渡して初期化
    if engine_name == "mymemory":
        return translator_class(email=mymemory_email)
    elif engine_name == "deepl":
        return translator_class(api_key=api_keys.get("deepl", ""))
    elif engine_name == "google":
        return translator_class(api_key=api_keys.get("google", ""))
    else:
        return translator_class()


def get_translator_names() -> list[tuple[str, str]]:
    """
    利用可能な翻訳エンジンの (キー名, 表示名) リストを返す。
    設定画面のドロップダウン用。
    """
    result = []
    for key, cls in AVAILABLE_TRANSLATORS.items():
        # 一時インスタンスを作って表示名を取得
        if key == "mymemory":
            instance = cls()
        elif key == "deepl":
            instance = cls(api_key="")
        elif key == "google":
            instance = cls(api_key="")
        else:
            instance = cls()
        result.append((key, instance.name()))
    return result


__all__ = [
    "BaseTranslator",
    "TranslationError",
    "MyMemoryTranslator",
    "DeepLTranslator",
    "GoogleTranslator",
    "create_translator",
    "get_translator_names",
    "AVAILABLE_TRANSLATORS",
]
