"""
画面キャプチャモジュール

DXcam (DXGI Desktop Duplication) を利用した高パフォーマンスな画面キャプチャ。
指定エリアのスクリーンショットを numpy 配列として返す。

将来の macOS 対応時は native/ 抽象化レイヤーにキャプチャ機能を移設し、
ScreenCaptureKit 等のプラットフォーム固有実装に切り替え可能にする。
"""

import numpy as np
from typing import Optional


class ScreenCapture:
    """指定エリアのスクリーンキャプチャを管理する"""

    def __init__(self):
        self._camera = None

    def _ensure_camera(self) -> None:
        """カメラインスタンスを遅延初期化する"""
        if self._camera is None:
            try:
                import dxcam
                self._camera = dxcam.create(output_color="RGB")
            except Exception as e:
                print(f"[ScreenCapture] DXcam の初期化に失敗: {e}")
                raise

    def grab(self, region: tuple[int, int, int, int]) -> Optional[np.ndarray]:
        """
        指定エリアをキャプチャして numpy 配列で返す。

        Args:
            region: (left, top, right, bottom) — キャプチャ領域

        Returns:
            RGB の numpy.ndarray (H, W, 3)。失敗時は None。
        """
        self._ensure_camera()
        try:
            frame = self._camera.grab(region=region)
            return frame
        except Exception as e:
            print(f"[ScreenCapture] キャプチャ失敗: {e}")
            return None

    def release(self) -> None:
        """リソースを解放する"""
        if self._camera is not None:
            try:
                del self._camera
            except Exception:
                pass
            self._camera = None

    def __del__(self):
        self.release()
