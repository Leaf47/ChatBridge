# ChatBridge ロードマップ

最終更新日: 2026-04-11

---

## 製品ビジョン

ChatBridge は、テキストのコピー＆ペーストと翻訳 API を組み合わせたリアルタイム翻訳ツールです。
主にゲーム内チャット（原神）での利用を想定していますが、
仕組み上、ゲームに限らずあらゆるアプリケーション上で汎用的に利用できます。
開発者自身の動作確認は原神のみで行っています（その他の用途は MIT ライセンスのもと自己責任）。

PC版（Windows / macOS）を起点に、モバイル版（iPadOS / iOS / Android）へ展開し、
プラットフォームを問わずシームレスな多言語コミュニケーションを実現します。

- **Windows / iPadOS / iOS**: 開発者自身が原神で利用するために開発・動作確認
- **macOS / Android**: 同じツールをより多くのプラットフォーム・ユーザーへ届けるために対応を計画

---

## プロジェクト構成

| リポジトリ | プラットフォーム | 技術スタック | 状態 |
|---|---|---|---|
| `ChatBridge` | Windows / macOS デスクトップ | Python / PySide6 / pynput | ✅ v1.0.0 (Windows)、macOS 計画中 |
| `ChatBridge-iOS` | iPadOS / iOS | Swift / SwiftUI / Xcode | 📋 計画中 |
| `ChatBridge-Android` | Android | 未定（Kotlin / Jetpack Compose 等を想定） | 🔲 未定（検証端末未確保） |

---

## Phase 1: デスクトップ版 OCR 画面翻訳（v2.0）

> **リポジトリ**: `ChatBridge`（本リポジトリ）

### 目的

現在の「送信翻訳」に加えて、画面上のチャットエリアをリアルタイムで読み取り、
受信メッセージも翻訳する機能を追加する。

### 主な機能

- **画面キャプチャ**: 指定エリアのスクリーンキャプチャ（DXGI Desktop Duplication 等）
- **OCR**: キャプチャ画像からテキストを認識（Tesseract / Windows OCR API）
- **差分検出**: 前回のOCR結果と比較し、新しいメッセージのみ翻訳
- **オーバーレイ拡張**: 翻訳結果をゲーム画面上にリアルタイム表示
- **エリア指定UI**: ユーザーが翻訳対象のチャットエリアをドラッグで指定
- **プラットフォーム抽象化**: OS固有コードを分離し、将来のmacOS対応に備える

### プラットフォーム抽象化レイヤー

現在 Windows に直接依存しているコードを `native/` モジュールとして分離する。
これにより、macOS 対応時にプラットフォーム固有モジュールを追加するだけで済む構成にする。

```
ChatBridge/
  ├── native/
  │   ├── __init__.py       # プラットフォーム検出・自動選択
  │   ├── base.py           # 抽象基底クラス（インターフェース定義）
  │   ├── windows.py        # Windows 固有実装
  │   │   ├── 管理者権限チェック / UAC 昇格
  │   │   ├── Global Mutex（二重起動防止）
  │   │   ├── タスクスケジューラ（自動起動）
  │   │   └── DXGI Desktop Duplication（画面キャプチャ）
  │   └── macos.py          # macOS 固有実装（Phase 2.5 で追加）
  │       ├── アクセシビリティ権限チェック
  │       ├── fcntl.flock（二重起動防止）
  │       ├── launchd（自動起動）
  │       └── ScreenCaptureKit（画面キャプチャ）
  ├── main.py
  ├── overlay.py            # 共通（PySide6）
  ├── hotkey_manager.py     # 共通（pynput が OS 差異を吸収）
  └── ...
```

### 技術的な検討事項

- OCRエンジンの選定と精度検証（ゲームフォントへの対応）
- キャプチャ頻度とCPU負荷のバランス
- パフォーマンス最適化（非同期処理、差分検出の効率化）
- プラットフォーム抽象化の粒度（どこまで共通化し、どこからOS固有にするか）

---

## Phase 2: iPadOS / iOS 版（ChatBridge iOS）

> **リポジトリ**: `ChatBridge-iOS`（別リポジトリ）

### 目的

iPadOS / iOS 上で原神のチャットを送受信ともに翻訳する。
デスクトップ版と同等の体験を、モバイルOSの制約内で最大限に実現する。

### アーキテクチャ

```
┌─────────────────────────────────────────────────┐
│              ChatBridge iOS                      │
│                                                  │
│  ┌──────────────┐     ┌──────────────────────┐  │
│  │ Keyboard     │     │ Main App             │  │
│  │ Extension    │     │                      │  │
│  │              │     │ ・設定画面            │  │
│  │ テキスト入力  │     │ ・チャットエリア指定   │  │
│  │ → 翻訳       │     │ ・PiP 表示エンジン    │  │
│  │ → 挿入       │     │                      │  │
│  └──────────────┘     └──────────┬───────────┘  │
│                                  │ App Groups    │
│  ┌──────────────────────────────┐│               │
│  │ Broadcast Upload Extension  ││               │
│  │                             ◄┘               │
│  │  画面キャプチャ → OCR → 翻訳                   │
│  │  → PiP 更新 or 通知発行                       │
│  └──────────────────────────────────────────────┘│
│                                                  │
│  共通: 翻訳エンジン（MyMemory / DeepL / Google）   │
└─────────────────────────────────────────────────┘
```

### コンポーネント

#### 1. Keyboard Extension（送信翻訳）

| 項目 | 内容 |
|---|---|
| 技術 | Custom Keyboard Extension (UIInputViewController) |
| 機能 | テキスト入力 → 翻訳ボタン → 翻訳結果をテキストフィールドに挿入 |
| 権限 | Full Access（ネットワーク通信に必要） |
| 実現性 | ✅ 確実 |

#### 2. Broadcast Upload Extension（受信翻訳 — キャプチャ + OCR）

| 項目 | 内容 |
|---|---|
| 技術 | ReplayKit Broadcast Upload Extension (RPBroadcastSampleHandler) |
| 機能 | 画面フレーム受信 → Apple Vision で OCR → 新メッセージ検出 → 翻訳 |
| 制約 | メモリ上限 50MB、ステータスバーに録画表示 |
| 実現性 | ✅ 技術的に可能 |

#### 3. PiP 表示エンジン（受信翻訳 — 結果表示）

| 項目 | 内容 |
|---|---|
| 技術 | AVPictureInPictureController + AVSampleBufferDisplayLayer |
| 機能 | 翻訳結果をビデオフレームとしてレンダリング → PiP ウィンドウで表示 |
| 代替手段 | ローカル通知（UNUserNotificationCenter）にフォールバック |
| Apple 審査 | ⚠️ PiP の非動画利用はグレーゾーン（リジェクト時は通知方式に切替） |
| 実現性 | ⚠️ PiP はやや不透明、通知は確実 |

### 技術的な検討事項

- Apple Vision の OCR 精度（ゲームフォント、多言語混在テキスト）
- Broadcast Extension のメモリ制約内での OCR 処理最適化
- App Groups を介した Extension ⇔ Main App 間のデータ共有
- PiP ウィンドウのバックグラウンド更新の安定性
- TestFlight / Ad Hoc 配布での個人利用を優先し、App Store 申請は後から検討

---

## Phase 2.5: macOS 対応

> **リポジトリ**: `ChatBridge`（本リポジトリ — 同一コードベース）

### 目的

Phase 1 で構築したプラットフォーム抽象化レイヤーを活用し、macOS 対応を追加する。
ChatBridge は仕組み上すでに汎用的に利用できるツールであり、この既存の価値を
macOS ユーザーにも届けることが目的。
主要ライブラリ（PySide6、pynput、pystray）はすべて macOS をサポートしているため、
プラットフォーム固有モジュール（`native/macos.py`）の実装が主な作業となる。

### 共通コード（変更不要）

| モジュール | 理由 |
|---|---|
| `overlay.py` | PySide6 がクロスプラットフォーム対応 |
| `hotkey_manager.py` | pynput が macOS 用バックエンド（Quartz）を内蔵 |
| `tray_app.py` | pystray が macOS 用バックエンド（AppKit）を内蔵 |
| `translator/` | 翻訳API呼び出しは OS 非依存 |
| `settings_ui.py` | PySide6 がクロスプラットフォーム対応 |
| `i18n.py` | 純粋な Python ロジック |

### macOS 固有の実装

| 機能 | Windows | macOS |
|---|---|---|
| 権限チェック | `IsUserAnAdmin()` + UAC | アクセシビリティ権限の確認・誘導 |
| 二重起動防止 | `Global\Mutex` (Win32) | `fcntl.flock` (POSIX) |
| 自動起動 | タスクスケジューラ | `launchd` (plist) |
| 画面キャプチャ | DXGI Desktop Duplication | `ScreenCaptureKit` |
| 画面収録権限 | 不要 | 画面収録権限の確認・誘導 |
| 配布 | PyInstaller (.exe) | PyInstaller (.app) + 公証 |

### 技術的な検討事項

- macOS の公証（Notarization）対応（未署名アプリのGatekeeper回避が必要）
- ScreenCaptureKit の Python バインディング（pyobjc 経由）
- 各種アプリケーション上でのオーバーレイ表示・ボーダーレスウィンドウとの互換性検証

---

## Phase 3: Android 版（将来）

> **状態**: 未計画

Android 版は実機検証環境が整った段階で検討する。
macOS 対応と同様に、ChatBridge の既存の価値をより幅広いユーザー層へ届けることを目指す。
技術的にはiOS版より制約が少なく（MediaProjection API、SYSTEM_ALERT_WINDOW）、
iOS版の知見を活かしてスムーズに開発できる見込み。

---

## Phase 間の依存関係

```
Phase 1 (Desktop OCR + プラットフォーム抽象化)
  │
  ├─ OCR エンジンの知見
  ├─ 差分検出アルゴリズム
  ├─ チャットエリア指定の UX
  └─ native/ 抽象化レイヤー
         │
         ├──────────────────────┐
         ▼                      ▼
Phase 2 (iPadOS / iOS)   Phase 2.5 (macOS)
  │                        │
  ├─ モバイルOCRの知見       ├─ native/macos.py 追加
  ├─ Keyboard Extension     └─ macOS 固有の権限・配布対応
  └─ PiP/通知の知見
         │
         ▼
Phase 3 (Android) — 将来
```

- Phase 1 で得た OCR・差分検出の知見は、Phase 2 の Broadcast Extension 開発に直接活きる
- Phase 1 で構築した `native/` 抽象化レイヤーにより、Phase 2.5 は最小限の実装で macOS 対応が可能
- Phase 2 と Phase 2.5 は独立しており、並行開発も可能
