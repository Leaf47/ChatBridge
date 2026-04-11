# ChatBridge 仕様書

バージョン: 1.0.0
最終更新日: 2026-04-11

---

## 1. 概要

ChatBridge は、ゲーム中のチャットをリアルタイムで翻訳するための Windows デスクトップアプリケーションである。
ホットキーを押すだけで入力中のテキストを翻訳し、ゲーム画面上にオーバーレイ表示した後、そのままペーストできる。

### 1.1 対象環境

| 項目 | 内容 |
|---|---|
| OS | Windows 10 / 11（64bit） |
| 権限 | 管理者権限（ゲーム上での動作に必須） |
| ランタイム | 不要（exe 単体で動作） |
| ネットワーク | 翻訳APIへのHTTP通信に必要 |

### 1.2 配布形態

- ポータブルアプリ（単一 exe ファイル）
- インストーラー不要
- レジストリ・システムフォルダへの書き込みなし（自動起動設定を除く）

---

## 2. 機能仕様

### 2.1 ホットキー翻訳

| 項目 | 内容 |
|---|---|
| デフォルトキー | `Alt+J` |
| カスタマイズ | 設定画面で任意のキーコンビネーションに変更可能 |
| 動作 | ホットキー押下 → クリップボード経由でテキスト取得 → 翻訳 → オーバーレイ表示 |

**テキスト取得の仕組み:**
1. ホットキーを検出
2. `Ctrl+A`（全選択）→ `Ctrl+C`（コピー）を自動送信
3. クリップボードからテキストを読み取り
4. 元のクリップボード内容は操作後に復元

### 2.2 翻訳エンジン

| エンジン | 状態 | APIキー | 制限 |
|---|---|---|---|
| MyMemory | ✅ 有効 | 不要 | 5,000文字/日（メール登録で50,000文字） |
| DeepL | 🔒 準備中 | 必要 | — |
| Google | 🔒 準備中 | 必要 | — |

**対応言語（9言語）:**
日本語、英語、中国語、韓国語、フランス語、ドイツ語、スペイン語、ポルトガル語、ロシア語

### 2.3 オーバーレイ表示

翻訳結果をゲーム画面上にフローティングウィンドウとして表示する。

| 項目 | 内容 |
|---|---|
| 表示位置 | カーソル位置 / 画面中央 / 右上（選択可能） |
| 不透明度 | 30%〜100%（スライダーで調整） |
| フォーカス | ゲームのフォーカスを奪わない（WA_ShowWithoutActivating + SWP_NOACTIVATE） |
| 操作 | `Enter` → 翻訳結果をペースト、`Esc` → キャンセル |
| 自動ペースト | オプションで確認なしの即ペーストが可能 |

**ウィンドウフラグ:**
- `WindowStaysOnTopHint` — 最前面表示
- `FramelessWindowHint` — フレームなし
- `Tool` — タスクバーに表示しない
- `WA_ShowWithoutActivating` — 表示時にフォーカスを取らない
- `WA_TranslucentBackground` — 半透明背景

**Enter/Esc キーの処理:**

オーバーレイはフォーカスを持たないため、Qt の `keyPressEvent` だけでは Enter/Esc を検出できない。
そのため、HotkeyManager の統合キーボードリスナー（pynput）の `win32_event_filter` を経由してキー入力を受け取る。
詳細は「4.1 キーボードフックアーキテクチャ」を参照。

### 2.4 システムトレイ

pystray によるシステムトレイ常駐。

**メニュー項目:**
- ⚙️ 設定を開く
- 🔄 翻訳エンジン: MyMemory
- ⏸️ 一時停止 / ▶️ 再開
- ❌ 終了

### 2.5 設定画面

PySide6 ベースのダークテーマ設定ウィンドウ。

**一般タブ:**
- ホットキー設定（キーバインド記録方式）
- オーバーレイ設定（位置、不透明度）
- 自動ペースト
- 自動起動（タスクスケジューラ）
- UI 言語

**翻訳エンジンタブ:**
- 翻訳方向（言語ペア）の設定
- MyMemory メールアドレス
- 接続テスト
- 将来のエンジン選択（現在は無効化）

### 2.6 設定ファイル

アプリと同じディレクトリに `config.json` として保存。

```json
{
  "hotkey_translate": "alt+j",
  "translator": "mymemory",
  "source_lang": "ja",
  "target_lang": "en",
  "ui_lang": "ja",
  "overlay_position": "cursor",
  "overlay_opacity": 0.9,
  "auto_paste": false,
  "setup_complete": true,
  "lang_selected": true,
  "auto_start": false,
  "mymemory_email": "",
  "api_keys": {
    "deepl": "",
    "google": ""
  }
}
```

### 2.7 自動起動

Windows タスクスケジューラを使用して管理者権限での自動起動を実現。

| 項目 | 内容 |
|---|---|
| タスク名 | `ChatBridge` |
| トリガー | ログオン時 |
| 権限 | 最上位特権（RunLevel Highest） |
| UAC | タスク登録時のみ、以降の自動起動時は不要 |

**登録方法:**
PowerShell の `New-ScheduledTask` / `Register-ScheduledTask` を使用。
削除は `schtasks /delete` で実行。

### 2.8 多言語対応（i18n）

| 方式 | 内容 |
|---|---|
| 組み込み言語 | 日本語（ja）、英語（en） |
| 外部言語 | `locales/` フォルダに JSON ファイルを配置 |
| フォールバック | 日本語をベースとし、不足キーは日本語で表示 |

初回起動時に言語選択ダイアログを表示。以降の管理者チェックやセットアップダイアログも選択された言語で表示される。

---

## 3. 起動制御

### 3.1 起動フロー

```
main() 開始
  │
  ├─ 多重起動チェック（Global Mutex）
  │    └─ 既に起動中 → ダイアログ表示 → 終了
  │
  ├─ QApplication 初期化
  │
  ├─ 初回起動: 言語選択ダイアログ
  │
  ├─ 管理者権限チェック
  │    └─ 通常権限 → 昇格ダイアログ → 再起動 or 終了
  │
  ├─ ChatBridgeApp 初期化
  │    ├─ 翻訳エンジン作成
  │    ├─ オーバーレイ初期化
  │    ├─ 設定画面初期化
  │    ├─ ホットキーマネージャー開始
  │    └─ システムトレイ表示
  │
  ├─ 初回起動: 自動起動設定ダイアログ
  │
  └─ Qt イベントループ開始
```

### 3.2 二重起動防止

Windows の名前付き Mutex（`Global\ChatBridge_SingleInstance_Mutex`）を使用。

| 技術的詳細 | 内容 |
|---|---|
| 名前空間 | `Global\`（セッション横断） |
| セキュリティ | NULL DACL で全権限レベルからアクセス可能 |
| 検出方法 | `ERROR_ALREADY_EXISTS` (183) または `ERROR_ACCESS_DENIED` (5) |
| ダイアログ | `WindowStaysOnTopHint` で最前面表示 |

### 3.3 管理者権限

- `ctypes.windll.shell32.IsUserAnAdmin()` で権限チェック
- `ShellExecuteW` の `runas` 動詞で UAC 昇格再起動
- 開発時は `pythonw.exe` を使用してコンソールウィンドウを抑制

---

## 4. スレッドモデル

| スレッド | 役割 | ライブラリ |
|---|---|---|
| メインスレッド | Qt イベントループ、UI 描画 | PySide6 |
| ホットキースレッド | キーボードイベントのリスニング | pynput |
| トレイスレッド | システムトレイアイコン | pystray |
| 翻訳スレッド | API 呼び出し（ホットキースレッドから直接実行） | requests |

**スレッド間通信:**
`UIBridge`（QObject）のシグナルを介して、ホットキースレッドからメインスレッドへ安全にUI操作をディスパッチ。

```python
class UIBridge(QObject):
    show_settings_signal = Signal()
    show_overlay_loading = Signal(str, str, str)
    show_overlay_result = Signal(str, str, str, str, str)
    quit_signal = Signal()
```

### 4.1 キーボードフックアーキテクチャ

> ⚠️ **重要な設計制約**: pynput の `keyboard.Listener` はアプリ全体で **1つだけ** 使用する。
> 複数のリスナーを同時に起動してはならない。

#### なぜリスナーは1つに限定するのか

pynput の `keyboard.Listener` は Windows の低レベルキーボードフック（`SetWindowsHookEx`）を使用する。
以下の理由から、複数リスナーの同時起動は禁止される：

1. **suppress_event() の排他性**: `win32_event_filter` 内で `suppress_event()` を呼ぶと、そのキーイベントは OS の入力ストリームから完全に除去される。別のリスナーにもイベントが届かなくなる。
2. **on_press の非発火**: `suppress_event()` を呼んだリスナー自身の `on_press` コールバックも発火しなくなる（pynput の既知の動作）。
3. **フックチェーンの競合**: 複数のフックが同じキーに対して競合すると、処理順序が不定になり、予測不能な動作を引き起こす。

#### 統合アーキテクチャ

```
┌─────────────────────────────────────────────────────┐
│              HotkeyManager（唯一のリスナー）           │
│                                                     │
│  keyboard.Listener                                  │
│  ├── win32_event_filter ──┐                         │
│  │                        ├─ オーバーレイ非表示時:    │
│  │                        │   全キーをそのまま通過    │
│  │                        │                         │
│  │                        ├─ オーバーレイ表示中:      │
│  │                        │   Enter/Esc →            │
│  │                        │     suppress_event()     │
│  │                        │     + overlay.handle_key()│
│  │                        │   その他 → そのまま通過   │
│  │                        │                         │
│  ├── on_press ────────────┤                         │
│  │   （suppress されなかった │                         │
│  │     キーのみ到達）       │                         │
│  │   ホットキー照合 → コールバック実行               │
│  │                                                  │
│  └── on_release ──────── 押下キーの追跡解除          │
└─────────────────────────────────────────────────────┘
         │
         │ overlay.handle_key(vk_code)
         │ （別スレッドから呼ばれる）
         ▼
┌─────────────────────────────────────────────────────┐
│              TranslationOverlay                      │
│                                                     │
│  handle_key(vk_code)                                │
│  ├── VK_RETURN → _confirm_signal.emit()             │
│  └── VK_ESCAPE → _cancel_signal.emit()              │
│                                                     │
│  ※ Signal 経由で UI スレッドにディスパッチ           │
│  ※ overlay 自身は pynput Listener を持たない         │
└─────────────────────────────────────────────────────┘
```

#### 処理フロー（オーバーレイ表示中に Enter を押した場合）

1. ユーザーが Enter キーを押下
2. Windows が低レベルキーボードフックを呼び出す
3. `HotkeyManager._win32_key_filter()` が実行される
4. `overlay.overlay_visible` が `True` なので、Enter キーを検出
5. `suppress_event()` でゲームにキーが届かないよう抑制
6. `WM_KEYDOWN` メッセージの場合のみ `overlay.handle_key(VK_RETURN)` を呼ぶ
7. overlay が `_confirm_signal.emit()` で UI スレッドに通知
8. UI スレッドで `_do_confirm()` → 翻訳結果をペースト、オーバーレイを非表示

#### 開発時の注意事項

- **pynput Listener の新規作成禁止**: 新しい機能で `keyboard.Listener` を追加しない。HotkeyManager のリスナーに統合すること。
- **suppress_event() は例外を raise する**: `suppress_event()` は内部で `SuppressException` を raise することでキーイベントを抑制する。**suppress_event() の後に書いたコードは実行されない**。抑制するキーの処理は必ず `suppress_event()` **より前**に行うこと。
- **suppress_event() と on_press の非互換**: `suppress_event()` を呼んだキーは `on_press` に到達しない。抑制するキーの処理は必ず `win32_event_filter` 内で行うこと。
- **UI スレッドセーフティ**: `win32_event_filter` はリスナースレッド（非UIスレッド）から呼ばれる。Qt ウィジェットの直接操作は禁止。Signal 経由でディスパッチすること。

---

## 5. ファイル構成

```
ChatBridge/
├── main.py              # エントリーポイント、起動制御
├── config.py            # 設定管理（config.json の読み書き）
├── i18n.py              # 多言語対応モジュール
├── hotkey_manager.py    # ホットキー検出・管理
├── clipboard_handler.py # クリップボード操作
├── overlay.py           # 翻訳結果オーバーレイ
├── settings_ui.py       # 設定画面UI
├── tray_app.py          # システムトレイ
├── native/              # プラットフォーム抽象化レイヤー
│   ├── __init__.py      # プラットフォーム検出・自動選択
│   ├── base.py          # 抽象基底クラス（インターフェース定義）
│   └── windows.py       # Windows 固有実装
├── translator/          # 翻訳エンジン
│   ├── __init__.py      # ファクトリ関数
│   ├── base.py          # 翻訳エンジン基底クラス
│   ├── mymemory_translator.py
│   ├── deepl_translator.py
│   └── google_translator.py
├── assets/
│   ├── icon.ico         # アプリアイコン
│   ├── icon.png         # アプリアイコン（PNG）
│   └── check.svg        # チェックマークUI素材
├── config.json          # 設定ファイル（自動生成、Git管理外）
├── ChatBridge.spec      # PyInstaller ビルド設定
├── requirements.txt     # Python 依存パッケージ
├── README.md            # 日本語ドキュメント
├── README_EN.md         # 英語ドキュメント
├── LICENSE              # MIT ライセンス
└── SPEC.md              # 本仕様書
```

---

## 6. ビルド手順

### 前提条件
- Python 3.12+
- pip で依存パッケージをインストール済み

### ビルドコマンド

```bash
pip install -r requirements.txt
pip install pyinstaller
pyinstaller ChatBridge.spec
```

成果物は `dist/ChatBridge.exe` に生成される。

### ビルド設定（ChatBridge.spec）

| 項目 | 値 |
|---|---|
| 単一ファイル | はい（onefile） |
| コンソール | なし（windowed） |
| UPX 圧縮 | 有効 |
| アイコン | `assets/icon.ico` |
| 同梱データ | `assets/icon.png` |

---

## 7. 依存パッケージ

| パッケージ | バージョン | 用途 |
|---|---|---|
| PySide6 | ≥6.6.0 | Qt6 UI フレームワーク |
| pynput | ≥1.7.6 | キーボードイベントの検出・シミュレーション |
| pystray | ≥0.19.5 | システムトレイアイコン |
| Pillow | ≥10.0.0 | 画像処理（pystray 依存） |
| pyperclip | ≥1.8.2 | クリップボード操作 |
| requests | ≥2.31.0 | HTTP 通信（翻訳 API） |
| deepl | ≥1.16.0 | DeepL API クライアント（将来用） |

---

## 8. 既知の制限事項

1. **MyMemory API の制限**: 無料枠は1日5,000文字（メール登録で50,000文字）
2. **全画面排他モード**: DirectX の排他全画面モードではオーバーレイが表示されない場合がある（ボーダレスウィンドウモード推奨）
3. **テキスト取得方式**: クリップボード経由のため、一部のゲームでは `Ctrl+A/C` が機能しない場合がある
4. **アンチチート**: 一部のアンチチートソフトウェアがキー入力シミュレーションをブロックする可能性がある
