"""
キャプチャサービス — 受信翻訳のバックグラウンドサービス

画面キャプチャ → OCR → 差分検出 → 翻訳 → UI通知 の全フローを管理する。
バックグラウンドスレッドで動作し、Qt シグナルで結果を通知する。
"""

import time
import threading
from typing import Optional

from PySide6.QtCore import QObject, Signal

from screen_capture import ScreenCapture
from ocr import create_ocr_engine
from chat_detector import ChatDetector


class CaptureService(QObject):
    """受信翻訳のバックグラウンドサービス"""

    # 新しい翻訳結果の通知（原文, 翻訳文）
    new_translation = Signal(str, str)
    # ステータス変更の通知
    status_changed = Signal(str)
    # エラーの通知
    error_occurred = Signal(str)

    def __init__(self, config, translator_factory):
        """
        Args:
            config: Config インスタンス
            translator_factory: 翻訳エンジンインスタンスを返す callable
        """
        super().__init__()
        self._config = config
        self._translator_factory = translator_factory
        self._capture: Optional[ScreenCapture] = None
        self._ocr = None
        self._detector = ChatDetector()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    @property
    def is_running(self) -> bool:
        """サービスが動作中かどうか"""
        return self._running

    def start(self, region: tuple[int, int, int, int]) -> None:
        """
        キャプチャサービスを開始する。

        Args:
            region: (left, top, right, bottom) — キャプチャ領域
        """
        if self._running:
            return

        self._region = region
        self._running = True
        self._detector.reset()

        # OCR エンジンの初期化
        engine_name = self._config.get("ocr_engine", "tesseract")
        try:
            self._ocr = create_ocr_engine(engine_name)
            if not self._ocr.is_available():
                self.error_occurred.emit(
                    f"OCR エンジン '{self._ocr.name()}' が利用できません。"
                    f"Tesseract がインストールされているか確認してください。"
                )
                self._running = False
                return
        except Exception as e:
            self.error_occurred.emit(f"OCR エンジンの初期化に失敗: {e}")
            self._running = False
            return

        # 画面キャプチャの初期化
        try:
            self._capture = ScreenCapture()
        except Exception as e:
            self.error_occurred.emit(f"画面キャプチャの初期化に失敗: {e}")
            self._running = False
            return

        # バックグラウンドスレッドを開始
        self._thread = threading.Thread(
            target=self._capture_loop,
            daemon=True,
            name="CaptureService",
        )
        self._thread.start()
        self.status_changed.emit("running")

    def stop(self) -> None:
        """キャプチャサービスを停止する"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        if self._capture:
            self._capture.release()
            self._capture = None
        self.status_changed.emit("stopped")

    def _capture_loop(self) -> None:
        """
        メインキャプチャループ。

        1. 指定エリアをキャプチャ
        2. OCR でテキスト認識
        3. 差分検出で新メッセージを抽出
        4. 新メッセージを翻訳
        5. シグナルで結果を通知
        6. 次のキャプチャまで待機
        """
        interval = self._config.get("capture_interval", 2.0)

        # OCR 言語コードを取得
        ocr_lang = self._get_ocr_lang()

        while self._running:
            try:
                # 1. 画面キャプチャ
                frame = self._capture.grab(self._region)
                if frame is None:
                    time.sleep(interval)
                    continue

                # 2. OCR
                text = self._ocr.recognize(frame, lang=ocr_lang)
                if not text.strip():
                    time.sleep(interval)
                    continue

                # 3. 差分検出
                new_messages = self._detector.detect_new_messages(text)

                # 4. 新メッセージの翻訳
                if new_messages:
                    translator = self._translator_factory()
                    source = self._config.get("source_lang", "ja")
                    target = self._config.get("target_lang", "en")

                    # 受信翻訳は送信翻訳と逆方向
                    # （相手が source 言語で書いた → target 言語に翻訳）
                    # ただし、受信翻訳専用の言語設定がある場合はそちらを使用
                    recv_source = self._config.get("recv_source_lang", target)
                    recv_target = self._config.get("recv_target_lang", source)

                    for msg in new_messages:
                        try:
                            translated = translator.translate(
                                msg,
                                source=recv_source,
                                target=recv_target,
                            )
                            # 5. 結果を通知
                            self.new_translation.emit(msg, translated)
                        except Exception as e:
                            print(f"[CaptureService] 翻訳エラー: {e}")

            except Exception as e:
                print(f"[CaptureService] キャプチャループエラー: {e}")

            # 6. 次のキャプチャまで待機
            time.sleep(interval)

    def _get_ocr_lang(self) -> str:
        """
        設定から OCR 言語コードを生成する。

        ChatBridge の翻訳言語コード（"ja", "en" 等）を
        Tesseract の言語コード（"jpn", "eng" 等）に変換する。
        """
        lang_map = {
            "ja": "jpn",
            "en": "eng",
            "zh": "chi_sim",
            "ko": "kor",
            "fr": "fra",
            "de": "deu",
            "es": "spa",
            "pt": "por",
            "ru": "rus",
        }

        # 受信翻訳の翻訳元言語を取得
        target = self._config.get("target_lang", "en")
        recv_source = self._config.get("recv_source_lang", target)

        # 複数言語を + で結合（例: "jpn+eng"）
        ocr_langs = []
        ocr_lang = lang_map.get(recv_source, "eng")
        ocr_langs.append(ocr_lang)

        # 常に英語も追加（ユーザー名やゲーム内テキストに英語が混在するため）
        if "eng" not in ocr_langs:
            ocr_langs.append("eng")

        return "+".join(ocr_langs)
