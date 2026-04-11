"""
自動アップデートモジュール

GitHub Releases API を利用してバージョンチェック & 自動更新を行う。
ポータブルアプリ（単一exe）に適したバッチファイル方式を採用。

更新フロー:
  1. GitHub API で最新バージョンを取得
  2. セマンティックバージョンで比較
  3. 新しい exe を一時ファイルとしてダウンロード
  4. バッチファイルを生成（旧exe→.bak, 新exe→元の名前, 再起動, 自己削除）
  5. 現在のプロセスを終了
  6. バッチファイルが置き換え＆再起動を実行
"""

import os
import sys
import tempfile
import threading
from dataclasses import dataclass
from typing import Optional, Callable

import requests
from PySide6.QtCore import QTimer, QObject, Signal

from version import __version__, __repo__


# --- データクラス ---

@dataclass
class UpdateInfo:
    """アップデート情報"""
    version: str           # 新しいバージョン番号（例: "1.2.0"）
    download_url: str      # exe のダウンロード URL
    release_notes: str     # リリースノート
    file_size: int         # ファイルサイズ（バイト）
    html_url: str          # ブラウザで表示するリリースページURL


# --- バージョン比較 ---

def _parse_version(v: str) -> tuple[int, ...]:
    """バージョン文字列をタプルに変換（"1.2.3" → (1, 2, 3)）"""
    v = v.lstrip("vV")  # "v1.2.3" → "1.2.3"
    parts = []
    for p in v.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def _is_newer(remote: str, local: str) -> bool:
    """remote が local より新しいか判定する"""
    return _parse_version(remote) > _parse_version(local)


# --- メインクラス ---

class AutoUpdater(QObject):
    """
    GitHub Releases を利用した自動アップデート管理。

    Signals:
        update_found: 新しいバージョンが見つかったとき（UpdateInfo）
        update_not_found: 最新版を使用中のとき
        update_error: エラー発生時（エラーメッセージ）
        download_progress: ダウンロード進捗（0-100）
        update_ready: ダウンロード完了、適用準備ができたとき
    """

    # シグナル定義
    update_found = Signal(object)      # UpdateInfo
    update_not_found = Signal()
    update_error = Signal(str)         # エラーメッセージ
    download_progress = Signal(int)    # 進捗率 0-100
    update_ready = Signal()            # 適用準備完了

    # GitHub API エンドポイント
    GITHUB_API_URL = f"https://api.github.com/repos/{__repo__}/releases/latest"

    # 定期チェック間隔（デフォルト: 6時間）
    DEFAULT_CHECK_INTERVAL_MS = 6 * 60 * 60 * 1000  # ミリ秒

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer: Optional[QTimer] = None
        self._current_update: Optional[UpdateInfo] = None
        self._downloaded_path: Optional[str] = None

    # --- バージョンチェック ---

    def check_for_update(self) -> None:
        """
        最新バージョンを確認する（バックグラウンドスレッドで実行）。
        結果は update_found / update_not_found / update_error シグナルで通知。
        """
        thread = threading.Thread(target=self._do_check, daemon=True)
        thread.start()

    def _do_check(self) -> None:
        """実際のバージョンチェック処理"""
        try:
            response = requests.get(
                self.GITHUB_API_URL,
                headers={"Accept": "application/vnd.github.v3+json"},
                timeout=10,
            )
            response.raise_for_status()

            data = response.json()
            tag_name = data.get("tag_name", "")
            release_notes = data.get("body", "") or ""
            html_url = data.get("html_url", "")

            # バージョン比較
            if not _is_newer(tag_name, __version__):
                self.update_not_found.emit()
                return

            # アセット（exe ファイル）を探す
            assets = data.get("assets", [])
            exe_asset = None
            for asset in assets:
                name = asset.get("name", "").lower()
                if name.endswith(".exe"):
                    exe_asset = asset
                    break

            if not exe_asset:
                self.update_not_found.emit()
                return

            info = UpdateInfo(
                version=tag_name.lstrip("vV"),
                download_url=exe_asset["browser_download_url"],
                release_notes=release_notes,
                file_size=exe_asset.get("size", 0),
                html_url=html_url,
            )
            self._current_update = info
            self.update_found.emit(info)

        except requests.exceptions.RequestException as e:
            self.update_error.emit(str(e))
        except Exception as e:
            self.update_error.emit(str(e))

    # --- ダウンロードと適用 ---

    def download_and_apply(self) -> None:
        """
        現在のアップデート情報に基づいてダウンロード＆適用を実行する。
        バックグラウンドスレッドで実行。
        """
        if not self._current_update:
            self.update_error.emit("No update info available")
            return

        thread = threading.Thread(
            target=self._do_download,
            args=(self._current_update,),
            daemon=True,
        )
        thread.start()

    def _do_download(self, info: UpdateInfo) -> None:
        """ダウンロード処理の実体"""
        try:
            # 一時ファイルにダウンロード（アプリフォルダと同じドライブに置く）
            app_dir = self._get_app_dir()
            temp_path = os.path.join(app_dir, f"ChatBridge_{info.version}_new.exe")

            response = requests.get(info.download_url, stream=True, timeout=120)
            response.raise_for_status()

            total_size = info.file_size or int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(temp_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = int(downloaded / total_size * 100)
                            self.download_progress.emit(min(progress, 100))

            self._downloaded_path = temp_path
            self.download_progress.emit(100)
            self.update_ready.emit()

        except Exception as e:
            # ダウンロード失敗時は一時ファイルを削除
            if 'temp_path' in locals() and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            self.update_error.emit(str(e))

    def apply_update(self) -> None:
        """
        ダウンロード済みのアップデートを適用する。
        バッチファイルを生成し、現在のプロセスを終了。
        バッチファイルが exe の置き換え＆再起動を行う。

        注意: exe 実行時のみ動作。開発時（python main.py）は何もしない。
        """
        if not self._downloaded_path or not os.path.exists(self._downloaded_path):
            self.update_error.emit("Downloaded file not found")
            return

        if not getattr(sys, 'frozen', False):
            # 開発時は適用しない
            print(f"[DEV] Update downloaded to: {self._downloaded_path}")
            return

        current_exe = sys.executable
        app_dir = os.path.dirname(current_exe)
        exe_name = os.path.basename(current_exe)
        backup_name = exe_name + ".bak"
        new_exe = self._downloaded_path

        # バッチファイルを作成
        bat_path = os.path.join(app_dir, "_update.bat")
        bat_content = f"""@echo off
chcp 65001 >nul
echo ChatBridge: アップデートを適用しています...
echo 旧プロセスの終了を待機中...
timeout /t 3 /nobreak >nul

REM 旧exe をバックアップ
if exist "{backup_name}" del /f /q "{backup_name}"
ren "{exe_name}" "{backup_name}"

REM 新exe を配置
move /y "{os.path.basename(new_exe)}" "{exe_name}"

echo ChatBridge: アップデート完了。再起動します...
timeout /t 1 /nobreak >nul

REM 再起動
start "" "{exe_name}"

REM バックアップと自分自身を削除
timeout /t 3 /nobreak >nul
del /f /q "{backup_name}"
del /f /q "%~f0"
"""
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)

        # バッチファイルを実行（現在のディレクトリで）
        import subprocess
        subprocess.Popen(
            ["cmd", "/c", bat_path],
            cwd=app_dir,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

    # --- 定期チェック ---

    def start_periodic_check(self, interval_ms: int = None) -> None:
        """定期的なバージョンチェックを開始する"""
        if interval_ms is None:
            interval_ms = self.DEFAULT_CHECK_INTERVAL_MS

        self.stop_periodic_check()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.check_for_update)
        self._timer.start(interval_ms)

        # 初回は起動30秒後にチェック（UIの初期化を待つ）
        QTimer.singleShot(30_000, self.check_for_update)

    def stop_periodic_check(self) -> None:
        """定期チェックを停止する"""
        if self._timer:
            self._timer.stop()
            self._timer = None

    # --- ユーティリティ ---

    @staticmethod
    def _get_app_dir() -> str:
        """アプリケーションのディレクトリを返す"""
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            return os.path.dirname(os.path.abspath(__file__))

    @staticmethod
    def is_frozen() -> bool:
        """exe として実行されているかどうか"""
        return getattr(sys, 'frozen', False)
