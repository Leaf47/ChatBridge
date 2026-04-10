"""
MyMemory 翻訳エンジン

無料で使える翻訳API。APIキー不要。
制限: 1日1000リクエスト（ゲームチャットなら十分）
"""

import requests
from .base import BaseTranslator, TranslationError


class MyMemoryTranslator(BaseTranslator):
    """MyMemory API を使った翻訳エンジン"""

    API_URL = "https://api.mymemory.translated.net/get"

    def translate(self, text: str, source: str = "ja", target: str = "en") -> str:
        """MyMemory API でテキストを翻訳する"""
        if not text.strip():
            return ""

        try:
            params = {
                "q": text,
                "langpair": f"{source}|{target}",
            }
            response = requests.get(self.API_URL, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # レスポンスのステータスチェック
            if data.get("responseStatus") != 200:
                error_msg = data.get("responseDetails", "不明なエラー")
                raise TranslationError(f"MyMemory API エラー: {error_msg}")

            translated = data.get("responseData", {}).get("translatedText", "")
            if not translated:
                raise TranslationError("翻訳結果が空です")

            return translated

        except requests.exceptions.Timeout:
            raise TranslationError("MyMemory API: 接続がタイムアウトしました")
        except requests.exceptions.ConnectionError:
            raise TranslationError("MyMemory API: 接続できません。ネットワークを確認してください")
        except requests.exceptions.RequestException as e:
            raise TranslationError(f"MyMemory API: リクエストエラー: {e}")
        except (KeyError, ValueError) as e:
            raise TranslationError(f"MyMemory API: レスポンスの解析に失敗: {e}")

    def name(self) -> str:
        return "MyMemory"

    def requires_api_key(self) -> bool:
        return False
