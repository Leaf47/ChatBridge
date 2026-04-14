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
    # エラーの通知（ダイアログ表示用 — 致命的なエラー）
    error_occurred = Signal(str)
    # アクティビティ更新の通知（オーバーレイのステータス表示用）
    activity_update = Signal(str)

    # キャプチャ連続失敗でエラー通知するまでの回数
    _MAX_CONSECUTIVE_FAILURES = 5

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
                    f"OCR エンジン '{self._ocr.name()}' が利用できません。\n"
                    f"Tesseract がインストールされているか確認してください。\n\n"
                    f"ダウンロード: https://github.com/UB-Mannheim/tesseract/wiki"
                )
                self._running = False
                return
        except Exception as e:
            self.error_occurred.emit(f"OCR エンジンの初期化に失敗しました:\n{e}")
            self._running = False
            return

        # 画面キャプチャの初期化
        try:
            self._capture = ScreenCapture()
        except Exception as e:
            self.error_occurred.emit(f"画面キャプチャの初期化に失敗しました:\n{e}")
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
        ocr_lang = self._get_ocr_lang()
        recv_source, recv_target = self._get_recv_langs()

        print(f"[CaptureService] ループ開始: region={self._region}, "
              f"interval={interval}s, ocr_lang={ocr_lang}, "
              f"翻訳方向={recv_source}→{recv_target}")

        self.activity_update.emit("スキャン開始...")

        loop_count = 0
        consecutive_capture_fails = 0
        consecutive_ocr_empty = 0

        while self._running:
            loop_count += 1
            try:
                # 1. 画面キャプチャ
                frame = self._capture.grab(self._region)
                if frame is None:
                    consecutive_capture_fails += 1
                    if consecutive_capture_fails == self._MAX_CONSECUTIVE_FAILURES:
                        self.error_occurred.emit(
                            f"画面キャプチャが {self._MAX_CONSECUTIVE_FAILURES} 回連続で失敗しています。\n"
                            f"ゲームが排他フルスクリーンモードで動作している可能性があります。\n"
                            f"ボーダーレスウィンドウモードに切り替えてください。"
                        )
                    self.activity_update.emit(
                        f"キャプチャ待機中... (失敗: {consecutive_capture_fails}回)"
                    )
                    time.sleep(interval)
                    continue

                # キャプチャ成功 → 連続失敗カウンタをリセット
                consecutive_capture_fails = 0

                # 2. OCR
                text = self._ocr.recognize(frame, lang=ocr_lang)
                if not text.strip():
                    consecutive_ocr_empty += 1
                    self.activity_update.emit(
                        f"スキャン中... テキスト未検出 "
                        f"(#{loop_count}, 空: {consecutive_ocr_empty}回連続)"
                    )
                    time.sleep(interval)
                    continue

                # OCR 成功 → 連続空カウンタをリセット
                consecutive_ocr_empty = 0
                line_count = len([l for l in text.strip().split("\n") if l.strip()])
                self.activity_update.emit(
                    f"スキャン中... {line_count}行検出 (#{loop_count})"
                )

                # 3. 差分検出
                new_messages = self._detector.detect_new_messages(text)

                # 4. 新メッセージの翻訳
                if new_messages:
                    self.activity_update.emit(
                        f"翻訳中... {len(new_messages)}件の新メッセージ"
                    )

                    translator = self._translator_factory()

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
                            # 翻訳エラーはオーバーレイ上に表示
                            self.activity_update.emit(f"翻訳エラー: {e}")
                            print(f"[CaptureService] 翻訳エラー: {e}")

                    self.activity_update.emit(
                        f"スキャン中... (#{loop_count})"
                    )

            except Exception as e:
                self.activity_update.emit(f"エラー: {e}")
                self.error_occurred.emit(
                    f"受信翻訳でエラーが発生しました:\n{e}"
                )
                print(f"[CaptureService] キャプチャループエラー: {e}")
                import traceback
                traceback.print_exc()

            # 6. 次のキャプチャまで待機
            time.sleep(interval)

    def _get_recv_langs(self) -> tuple[str, str]:
        """
        受信翻訳の言語ペアを返す。

        recv_source_lang / recv_target_lang が None の場合は
        送信翻訳の target / source をフォールバックとして使用する。
        """
        source = self._config.get("source_lang", "ja")
        target = self._config.get("target_lang", "en")

        recv_source = self._config.get("recv_source_lang", None)
        recv_target = self._config.get("recv_target_lang", None)

        # None の場合は送信翻訳と逆方向をデフォルトとする
        if not recv_source:
            recv_source = target
        if not recv_target:
            recv_target = source

        return recv_source, recv_target

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
        recv_source, _ = self._get_recv_langs()

        # 複数言語を + で結合（例: "jpn+eng"）
        ocr_langs = []
        ocr_lang = lang_map.get(recv_source, "eng")
        ocr_langs.append(ocr_lang)

        # 常に英語も追加（ユーザー名やゲーム内テキストに英語が混在するため）
        if "eng" not in ocr_langs:
            ocr_langs.append("eng")

        return "+".join(ocr_langs)
