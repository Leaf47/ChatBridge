# ChatBridge アーキテクチャ

最終更新日: 2026-04-15

---

## 設計思想

ChatBridge の設計は、以下の 4 つの原則に基づいている。
アーキテクチャ上のすべての判断は、これらの原則を満たすために行われた。

### 1. ゲーム体験を中断しない

最も重要な原則。翻訳のためにゲーム画面から離れる必要があってはならない。

| 原則 | 実現手段 |
|---|---|
| フォーカスを奪わない | `WA_ShowWithoutActivating` + `SWP_NOACTIVATE` でオーバーレイを表示 |
| ゲーム操作を妨げない | Enter/Esc は `win32_event_filter` で選択的に suppress し、他のキーはゲームに通す |
| 視界を遮らない | 半透明オーバーレイ（不透明度調整可）、受信翻訳は自動非表示対応 |
| 操作は最小限 | ホットキー 1 回 → 翻訳結果表示 → Enter で確定。3 ステップで完結 |

### 2. ポータブルでシンプル

ユーザーに余計な手間をかけさせない。ダウンロードしたらすぐ使える。

| 原則 | 実現手段 |
|---|---|
| インストーラー不要 | 単一 exe（PyInstaller onefile）、フォルダに置くだけ |
| 設定は自己完結 | `config.json` を exe と同じディレクトリに自動生成 |
| レジストリ・システムフォルダを汚さない | 自動起動もタスクスケジューラで実現（レジストリ不使用） |
| アンインストールはフォルダ削除のみ | 外部依存なし（自動起動タスクの削除を除く） |

### 3. 無料で即座に使える

技術的なハードルや費用が、利用の障壁になってはならない。

| 原則 | 実現手段 |
|---|---|
| API キー不要 | MyMemory API をデフォルトエンジンに採用 |
| アカウント登録不要 | メールアドレスは任意（設定すると利用枠が拡大するだけ） |
| 設定なしで動作 | デフォルト値で即座に日→英翻訳が可能 |
| 初回起動をガイド | 言語選択 → 管理者権限 → 自動起動の順に自然に誘導 |

### 4. 将来の拡張に備える

現在は Windows + MyMemory だが、設計上はプラットフォーム・エンジンを問わない。

| 原則 | 実現手段 |
|---|---|
| OS 固有処理の分離 | `native/` モジュールの抽象化レイヤー（`BasePlatform` → `WindowsPlatform`） |
| 翻訳エンジンの抽象化 | `translator/` モジュール（`BaseTranslator` → 各エンジン実装） |
| OCR エンジンの抽象化 | `ocr/` モジュール（`BaseOCR` → `TesseractOCR`） |
| UI の多言語対応 | `i18n.py`（内蔵 ja/en + 外部 JSON 拡張） |

---

## 全体構成

```
ChatBridge/
├── main.py              # エントリーポイント + アプリ統合
├── config.py            # 設定管理（config.json の読み書き）
├── i18n.py              # 多言語対応（日/英内蔵 + 外部JSON拡張可能）
├── version.py           # バージョン情報（__version__, __repo__）
├── updater.py           # 自動アップデート（GitHub Releases）
│
├── hotkey_manager.py    # ホットキー検出（統合キーボードリスナー）
├── clipboard_handler.py # クリップボード操作（Ctrl+A/C/V シミュレーション）
├── overlay.py           # 送信翻訳オーバーレイ（Enter確定/Escキャンセル）
├── settings_ui.py       # 設定画面UI（一般/翻訳エンジン/About タブ）
├── tray_app.py          # システムトレイ（pystray）
│
├── capture_service.py   # 受信翻訳パイプラインのオーケストレーション
├── screen_capture.py    # 画面キャプチャ（DXcam / DXGI）
├── chat_detector.py     # チャットメッセージ差分検出
├── area_selector.py     # エリア指定オーバーレイ（ドラッグ選択）
├── recv_overlay.py      # 受信翻訳オーバーレイ（時系列表示）
│
├── native/              # プラットフォーム抽象化レイヤー
│   ├── __init__.py      # get_platform() — シングルトン
│   ├── base.py          # BasePlatform（抽象基底クラス）
│   └── windows.py       # WindowsPlatform（Windows固有実装）
│
├── ocr/                 # OCR エンジン
│   ├── __init__.py      # ファクトリ関数（create_ocr_engine）
│   ├── base.py          # BaseOCR（抽象基底クラス）
│   └── tesseract_ocr.py # Tesseract OCR + 画像前処理パイプライン
│
├── translator/          # 翻訳エンジン
│   ├── __init__.py      # ファクトリ関数（create_translator）
│   ├── base.py          # BaseTranslator（抽象基底クラス）
│   ├── mymemory_translator.py
│   ├── deepl_translator.py    # 準備中
│   └── google_translator.py   # 準備中
│
├── assets/              # アイコン等
├── docs/                # ドキュメント（本ファイル）
├── config.json          # 設定ファイル（自動生成、Git管理外）
├── ChatBridge.spec      # PyInstaller ビルド設定
└── requirements.txt     # Python 依存パッケージ
```

---

## スレッドモデル

| スレッド | 役割 | ライブラリ |
|---|---|---|
| メインスレッド | Qt イベントループ、UI 描画 | PySide6 |
| ホットキースレッド | キーボードイベントのリスニング | pynput |
| トレイスレッド | システムトレイアイコン | pystray |
| 翻訳スレッド | API 呼び出し（ホットキースレッドから直接実行） | requests |
| アップデートスレッド | バージョンチェック・ダウンロード | threading |
| キャプチャスレッド | 受信翻訳パイプライン（OCR + 翻訳ループ） | threading |

### スレッド間通信

すべてのスレッド間通信は **Qt Signal** 経由で行う（スレッドセーフ）。

```
ホットキースレッド  ──Signal──>  メインスレッド（UI）
キャプチャスレッド  ──Signal──>  メインスレッド（UI）
アップデートスレッド ──Signal──>  メインスレッド（UI）
```

> ⚠️ **重要**: pynput の `keyboard.Listener` はアプリ全体で **1つだけ**。
> `HotkeyManager` に統合し、他のモジュールからは `set_overlay()` 等で参照を渡す。

---

## 機能アーキテクチャ

### 1. 送信翻訳（v1.0.0〜）

```
ユーザーが Alt+J 押下
  │
  ├── HotkeyManager が検出（ホットキースレッド）
  ├── Ctrl+A → Ctrl+C シミュレーション
  ├── クリップボードからテキスト取得
  ├── UIBridge 経由でオーバーレイにローディング表示
  ├── 翻訳 API 呼び出し
  ├── UIBridge 経由でオーバーレイに結果表示
  │
  └── ユーザー操作
      ├── Enter → Ctrl+V でペースト
      └── Esc  → キャンセル（クリップボード復元）
```

### 2. 受信翻訳（Phase 1）

```
CaptureService（キャプチャスレッド）
  │
  ├── 1. ScreenCapture.grab(region)
  │     └── DXcam (DXGI Desktop Duplication)
  │
  ├── 2. TesseractOCR.recognize(frame, lang)
  │     └── 前処理: グレースケール → CLAHE → 二値化 → ノイズ除去
  │
  ├── 3. ChatDetector.detect_new_messages(text)
  │     └── SequenceMatcher で前回との差分を検出
  │     └── 初回は全行スキップ（起動直後の翻訳ラッシュ防止）
  │
  ├── 4. Translator.translate(msg, source, target)
  │     └── 受信翻訳は送信翻訳と逆方向（相手の言語 → 自分の言語）
  │
  └── 5. Signal emission
        ├── new_translation  → ReceivedTranslationOverlay.add_message
        ├── activity_update  → ReceivedTranslationOverlay.update_status
        └── error_occurred   → QMessageBox（ダイアログ表示）
```

---

## プラットフォーム抽象化レイヤー

`native/` モジュールにより OS 固有の処理を抽象化。

| メソッド | Windows 実装 | macOS（将来） |
|---|---|---|
| `is_admin()` | `IsUserAnAdmin()` | アクセシビリティ権限チェック |
| `relaunch_as_admin()` | `ShellExecuteW` (runas) | — |
| `create_single_instance_lock()` | `Global\Mutex` | `fcntl.flock` |
| `set_auto_start(enabled)` | タスクスケジューラ | `launchd` |
| `show_window_no_activate(handle)` | `SWP_NOACTIVATE` | — |
| `is_modifier_pressed()` | `GetAsyncKeyState` | — |
| `get_exe_path()` | `sys.executable` | `sys.executable` |

---

## 設定ファイル (config.json)

### 送信翻訳関連

| キー | 型 | デフォルト | 説明 |
|---|---|---|---|
| `hotkey_translate` | string | `"alt+j"` | 翻訳ホットキー |
| `translator` | string | `"mymemory"` | 翻訳エンジン |
| `source_lang` | string | `"ja"` | 送信翻訳の翻訳元言語 |
| `target_lang` | string | `"en"` | 送信翻訳の翻訳先言語 |
| `overlay_position` | string | `"cursor"` | オーバーレイ位置 |
| `overlay_opacity` | float | `0.9` | 送信オーバーレイの不透明度 |
| `auto_paste` | bool | `false` | 確認なしで即ペースト |

### 受信翻訳関連

| キー | 型 | デフォルト | 説明 |
|---|---|---|---|
| `capture_region` | array\|null | `null` | キャプチャ領域 [left, top, right, bottom] |
| `capture_interval` | float | `2.0` | キャプチャ間隔（秒） |
| `capture_enabled` | bool | `false` | 受信翻訳の有効/無効 |
| `ocr_engine` | string | `"tesseract"` | OCR エンジン |
| `recv_source_lang` | string\|null | `null` | 受信翻訳の翻訳元（null = target_lang を使用） |
| `recv_target_lang` | string\|null | `null` | 受信翻訳の翻訳先（null = source_lang を使用） |
| `recv_overlay_geometry` | array\|null | `null` | オーバーレイ位置・サイズ [x, y, w, h] |
| `recv_overlay_opacity` | float | `0.85` | 受信オーバーレイの不透明度 |
| `recv_auto_hide` | bool | `true` | アプリ非アクティブ時の自動非表示 |
| `recv_target_app` | string | `""` | 監視対象アプリのウィンドウタイトル |

### システム関連

| キー | 型 | デフォルト | 説明 |
|---|---|---|---|
| `ui_lang` | string | `"ja"` | UI表示言語 |
| `auto_start` | bool | `false` | Windows起動時の自動起動 |
| `auto_update_check` | bool | `true` | 自動アップデートチェック |
| `setup_complete` | bool | `false` | 初回セットアップ完了フラグ |
| `lang_selected` | bool | `false` | 言語選択済みフラグ |
| `mymemory_email` | string | `""` | MyMemory のメールアドレス |
