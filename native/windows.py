"""
プラットフォーム抽象化 — Windows 実装

Windows 固有の処理を BasePlatform インターフェースに準拠して実装する。
main.py, settings_ui.py, overlay.py, clipboard_handler.py から移植。
"""

import sys
import os
import ctypes
import ctypes.wintypes
import subprocess
from typing import Any

from native.base import BasePlatform


# --- Win32 API 定数 ---

# SetWindowPos
HWND_TOPMOST = ctypes.wintypes.HWND(-1)
SWP_NOACTIVATE = 0x0010
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040

# 修飾キーの仮想キーコード
VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_ALT = 0x12

# タスクスケジューラのタスク名
_TASK_NAME = "ChatBridge"

# Win32 API ハンドル
_user32 = ctypes.windll.user32


class WindowsPlatform(BasePlatform):
    """Windows 固有処理の実装"""

    # --- 権限管理 ---

    def is_admin(self) -> bool:
        """現在のプロセスが管理者権限で実行されているかチェックする"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    def relaunch_as_admin(self) -> None:
        """管理者権限でアプリを再起動する（UACプロンプト表示）"""
        if getattr(sys, 'frozen', False):
            # exe の場合
            exe = sys.executable
            params = ""
        else:
            # 開発時: pythonw.exe を使ってコンソールウィンドウを出さない
            exe = sys.executable.replace("python.exe", "pythonw.exe")
            script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "main.py")
            script = os.path.normpath(script)
            params = f'"{script}"'

        # ShellExecuteW で管理者昇格して起動（UACプロンプト表示）
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", exe, params, None, 1  # 1 = SW_SHOWNORMAL
        )

    # --- 二重起動防止 ---

    def create_single_instance_lock(self) -> tuple[Any, bool]:
        """
        全権限レベルからアクセス可能な名前付きMutexを作成する。

        管理者権限で作成したMutexは、デフォルトでは通常権限プロセスから
        アクセスできない（ERROR_ACCESS_DENIED）。NULL DACL を設定した
        SECURITY_ATTRIBUTES を使うことで、全権限レベルからアクセス可能にする。

        Returns:
            (mutex_handle, already_running)
        """
        # SECURITY_ATTRIBUTES 構造体を定義
        class SECURITY_ATTRIBUTES(ctypes.Structure):
            _fields_ = [
                ("nLength", ctypes.c_ulong),
                ("lpSecurityDescriptor", ctypes.c_void_p),
                ("bInheritHandle", ctypes.c_int),
            ]

        _advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
        _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        # NULL DACL のセキュリティ記述子を作成
        # これにより全ユーザー・全権限レベルからアクセス可能になる
        sd = ctypes.c_buffer(64)  # SECURITY_DESCRIPTOR バッファ
        _advapi32.InitializeSecurityDescriptor(ctypes.byref(sd), 1)
        # NULL DACL を設定
        _advapi32.SetSecurityDescriptorDacl(ctypes.byref(sd), True, None, False)

        sa = SECURITY_ATTRIBUTES()
        sa.nLength = ctypes.sizeof(SECURITY_ATTRIBUTES)
        sa.lpSecurityDescriptor = ctypes.addressof(sd)
        sa.bInheritHandle = False

        mutex_name = "Global\\ChatBridge_SingleInstance_Mutex"
        mutex = _kernel32.CreateMutexW(ctypes.byref(sa), False, mutex_name)
        last_error = ctypes.get_last_error()

        # ERROR_ALREADY_EXISTS (183) または ERROR_ACCESS_DENIED (5)
        already_exists = (last_error == 183) or (mutex == 0 and last_error == 5)

        return mutex, already_exists

    # --- 自動起動 ---

    def get_auto_start(self) -> bool:
        """タスクスケジューラに自動起動タスクが登録されているか確認する"""
        try:
            result = subprocess.run(
                ["schtasks", "/query", "/tn", _TASK_NAME],
                capture_output=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return result.returncode == 0
        except Exception:
            return False

    def set_auto_start(self, enabled: bool) -> bool:
        """
        タスクスケジューラで管理者権限の自動起動を設定する。
        成功時True、失敗時Falseを返す。
        """
        try:
            if enabled:
                exe_path = self.get_exe_path()
                # PowerShellでタスクを作成（最上位特権 + ログオン時実行）
                ps_script = (
                    f'$action = New-ScheduledTaskAction -Execute {exe_path};'
                    f'$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME;'
                    f'$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit 0;'
                    f'$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest -LogonType Interactive;'
                    f'$task = New-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -Principal $principal;'
                    f'Register-ScheduledTask -TaskName "{_TASK_NAME}" -InputObject $task -Force'
                )
                subprocess.run(
                    ["powershell", "-Command",
                     f"Start-Process powershell -ArgumentList '-Command {ps_script}' -Verb RunAs -Wait"],
                    capture_output=True, timeout=30,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                return self.get_auto_start()
            else:
                # タスクの削除（管理者昇格）
                subprocess.run(
                    ["powershell", "-Command",
                     f'Start-Process schtasks -ArgumentList \'/delete /tn "{_TASK_NAME}" /f\' -Verb RunAs -Wait'],
                    capture_output=True, timeout=15,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                return not self.get_auto_start()
        except Exception:
            return False

    # --- ウィンドウ管理 ---

    def show_window_no_activate(self, window_handle: int) -> None:
        """Win32 API でフォーカスを奪わずにウィンドウを最前面に表示する"""
        _user32.SetWindowPos(
            window_handle,
            HWND_TOPMOST,
            0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
        )

    # --- 入力状態 ---

    def is_modifier_pressed(self) -> bool:
        """修飾キー（Ctrl/Shift/Alt）が物理的に押されているかチェック"""
        for vk in (VK_CONTROL, VK_SHIFT, VK_ALT):
            if _user32.GetAsyncKeyState(vk) & 0x8000:
                return True
        return False

    # --- ユーティリティ ---

    def get_exe_path(self) -> str:
        """実行ファイルのパスを返す"""
        if getattr(sys, 'frozen', False):
            return f'"{sys.executable}"'
        else:
            exe_path = sys.executable
            script_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "..", "main.py"
            )
            script_path = os.path.normpath(script_path)
            return f'"{exe_path}" "{script_path}"'
