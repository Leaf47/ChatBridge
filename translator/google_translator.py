"""
Google Cloud Translation 翻訳エンジン

Google Cloud Translation API v2 を使用。
APIキーの取得が必要: https://cloud.google.com/translate/docs/setup
"""

import requests
from .base import BaseTranslator, TranslationError


class GoogleTranslator(BaseTranslator):
    """Google Cloud Translation API を使った翻訳エンジン"""

    API_URL = "https://translation.googleapis.com/language/translate/v2"

    def __init__(self, api_key: str = ""):
        self._api_key = api_key

    def set_api_key(self, api_key: str) -> None:
        """APIキーを設定する"""
        self._api_key = api_key

    def translate(self, text: str, source: str = "ja", target: str = "en") -> str:
        """Google Cloud Translation API でテキストを翻訳する"""
        if not text.strip():
            return ""

        if not self._api_key:
            raise TranslationError(
                "Google Cloud APIキーが設定されていません。設定画面からキーを入力してください。"
            )

        try:
            params = {
                "q": text,
                "source": source,
                "target": target,
                "key": self._api_key,
                "format": "text",
            }
            response = requests.post(self.API_URL, data=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            translations = data.get("data", {}).get("translations", [])

            if not translations:
                raise TranslationError("Google: 翻訳結果が空です")

            return translations[0].get("translatedText", "")

        except requests.exceptions.Timeout:
            raise TranslationError("Google: 接続がタイムアウトしました")
        except requests.exceptions.ConnectionError:
            raise TranslationError("Google: 接続できません。ネットワークを確認してください")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                raise TranslationError("Google: APIキーが無効です。正しいキーを設定してください。")
            raise TranslationError(f"Google: HTTPエラー: {e}")
        except requests.exceptions.RequestException as e:
            raise TranslationError(f"Google: リクエストエラー: {e}")
        except (KeyError, ValueError) as e:
            raise TranslationError(f"Google: レスポンスの解析に失敗: {e}")

    def name(self) -> str:
        return "Google"

    def requires_api_key(self) -> bool:
        return True
