"""
Tesseract OCR エンジン

pytesseract ラッパー。画像の前処理（グレースケール、二値化、
コントラスト強調）を行い、Tesseract OCR でテキストを認識する。

exe ビルド時は Tesseract バイナリと traineddata を同梱する。
開発時はシステムにインストールされた Tesseract を使用する。
"""

import os
import sys

import cv2
import numpy as np

from ocr.base import BaseOCR


class TesseractOCR(BaseOCR):
    """Tesseract OCR エンジン"""

    # Tesseract のデフォルトインストールパス（Windows）
    _DEFAULT_PATHS = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]

    def __init__(self):
        self._configure_tesseract()

    def _configure_tesseract(self) -> None:
        """Tesseract のパスを設定する"""
        import pytesseract

        # 1. exe ビルド時: 同梱された Tesseract を使用
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
            tesseract_cmd = os.path.join(
                base_path, "Tesseract-OCR", "tesseract.exe"
            )
            tessdata_dir = os.path.join(
                base_path, "Tesseract-OCR", "tessdata"
            )
            if os.path.exists(tesseract_cmd):
                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
                os.environ["TESSDATA_PREFIX"] = tessdata_dir
                return

        # 2. 開発時: システムのデフォルトパスを探索
        for path in self._DEFAULT_PATHS:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                return

        # 3. PATH に含まれている場合はそのまま使える（設定不要）

    def recognize(self, image: np.ndarray, lang: str = "eng") -> str:
        """
        画像からテキストを認識する。

        前処理パイプライン:
          1. グレースケール変換
          2. コントラスト強調（CLAHE）
          3. 二値化（Otsu's method）
          4. ノイズ除去

        Args:
            image: RGB の numpy 配列 (H, W, 3)
            lang: Tesseract 言語コード（例: "eng", "jpn", "jpn+eng"）

        Returns:
            認識されたテキスト文字列（空行除去済み）
        """
        import pytesseract

        # 前処理パイプライン
        processed = self._preprocess(image)

        # Tesseract でテキスト認識
        # PSM 6: 単一のテキストブロックと仮定（チャットエリア向き）
        custom_config = r"--oem 3 --psm 6"
        text = pytesseract.image_to_string(
            processed, lang=lang, config=custom_config
        )

        # 結果のクリーンアップ
        return self._cleanup(text)

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        OCR 精度を高めるための画像前処理パイプライン。

        Args:
            image: RGB の numpy 配列

        Returns:
            前処理済みのグレースケール画像
        """
        # 1. グレースケール変換
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

        # 2. コントラスト強調（CLAHE — 局所的な適応ヒストグラム均等化）
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # 3. 二値化（Otsu's method — 背景とテキストの分離に最適）
        _, binary = cv2.threshold(
            enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        # 4. ノイズ除去（中央値フィルタ）
        denoised = cv2.medianBlur(binary, 3)

        return denoised

    @staticmethod
    def _cleanup(text: str) -> str:
        """
        OCR 結果のクリーンアップ。

        - 空行を除去
        - 前後の空白をトリム
        - 1 文字だけの行を除去（ノイズ対策）
        """
        lines = text.strip().split("\n")
        cleaned = []
        for line in lines:
            line = line.strip()
            if len(line) > 1:  # 1文字だけの行はノイズとして除去
                cleaned.append(line)
        return "\n".join(cleaned)

    def name(self) -> str:
        return "Tesseract OCR"

    def is_available(self) -> bool:
        """Tesseract が利用可能かチェックする"""
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False
