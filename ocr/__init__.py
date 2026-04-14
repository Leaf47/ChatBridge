"""
OCR エンジン — ファクトリモジュール

利用可能な OCR エンジンの自動選択・生成を行う。
translator/ と同様のファクトリパターンを採用し、将来のエンジン追加に対応。

現在サポートしているエンジン:
  - tesseract: Tesseract OCR（デフォルト、exe に同梱）

将来追加予定:
  - paddleocr: PaddleOCR（ユーザーが別途インストール）
"""

from typing import Optional

from ocr.base import BaseOCR


def create_ocr_engine(engine_name: str = "tesseract", **kwargs) -> BaseOCR:
    """
    OCR エンジンのインスタンスを作成する。

    Args:
        engine_name: エンジン名（"tesseract" など）
        **kwargs: エンジン固有のオプション

    Returns:
        BaseOCR の具象インスタンス

    Raises:
        ValueError: 未対応のエンジン名が指定された場合
    """
    if engine_name == "tesseract":
        from ocr.tesseract_ocr import TesseractOCR
        return TesseractOCR(**kwargs)
    else:
        raise ValueError(
            f"未対応の OCR エンジン: {engine_name}\n"
            f"利用可能なエンジン: tesseract"
        )


def get_available_engines() -> list[tuple[str, str]]:
    """
    利用可能な OCR エンジンの一覧を返す。

    Returns:
        (キー, 表示名) のリスト
    """
    engines = [("tesseract", "Tesseract OCR")]

    # 将来: PaddleOCR がインストールされていれば追加
    # try:
    #     from paddleocr import PaddleOCR
    #     engines.append(("paddleocr", "PaddleOCR"))
    # except ImportError:
    #     pass

    return engines
