"""
DeepL 翻訳エンジン

高品質な翻訳を提供するAPI。Free プランで月50万文字まで無料。
APIキーの取得が必要: https://www.deepl.com/pro-api
"""

import deepl
from .base import BaseTranslator, TranslationError


class DeepLTranslator(BaseTranslator):
    """DeepL API を使った翻訳エンジン"""

    # DeepL の言語コードマッピング（DeepL固有の形式に対応）
    LANG_MAP = {
        "en": "EN-US",  # DeepL は英語のバリアント指定が必要（ターゲット時）
        "ja": "JA",
    }

    def __init__(self, api_key: str = ""):
        self._api_key = api_key
        self._translator = None
        if api_key:
            self._init_client()

    def _init_client(self) -> None:
        """DeepL クライアントを初期化する"""
        try:
            self._translator = deepl.Translator(
                self._api_key,
                server_url="https://api-free.deepl.com",
            )
        except Exception as e:
            raise TranslationError(f"DeepL クライアントの初期化に失敗: {e}")

    def set_api_key(self, api_key: str) -> None:
        """APIキーを設定してクライアントを再初期化する"""
        self._api_key = api_key
        if api_key:
            self._init_client()
        else:
            self._translator = None

    def translate(self, text: str, source: str = "ja", target: str = "en") -> str:
        """DeepL API でテキストを翻訳する"""
        if not text.strip():
            return ""

        if not self._translator:
            raise TranslationError("DeepL APIキーが設定されていません。設定画面からキーを入力してください。")

        try:
            # ターゲット言語のマッピング
            target_lang = self.LANG_MAP.get(target, target.upper())
            source_lang = source.upper()

            result = self._translator.translate_text(
                text,
                source_lang=source_lang,
                target_lang=target_lang,
            )
            return result.text

        except deepl.AuthorizationException:
            raise TranslationError("DeepL: APIキーが無効です。正しいキーを設定してください。")
        except deepl.QuotaExceededException:
            raise TranslationError("DeepL: 今月の無料枠を使い切りました。")
        except deepl.ConnectionException:
            raise TranslationError("DeepL: 接続できません。ネットワークを確認してください。")
        except deepl.DeepLException as e:
            raise TranslationError(f"DeepL: {e}")
        except Exception as e:
            raise TranslationError(f"DeepL: 予期しないエラー: {e}")

    def name(self) -> str:
        return "DeepL"

    def requires_api_key(self) -> bool:
        return True
