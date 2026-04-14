# ChatBridge タスクリスト

現在進行中の開発タスクを管理するファイル。  
Antigravity の `task.md` と同期される。

最終更新日: 2026-04-14

---

## 進行中: Phase 1 — OCR 受信翻訳

### 実装済（v2.0 リリース準備中）

- [x] 画面キャプチャ（DXcam / DXGI Desktop Duplication）
- [x] OCR エンジン（Tesseract + 画像前処理パイプライン）
- [x] チャットメッセージ差分検出
- [x] 受信翻訳パイプラインの統合（CaptureService）
- [x] エリア指定 UI（ドラッグ選択）
- [x] 受信翻訳オーバーレイ（時系列表示 + ステータスバー）
- [x] オーバーレイ自動非表示（ターゲットアプリ指定対応）
- [x] `recv_source_lang: null` による翻訳失敗バグの修正
- [x] エラーハンドリングの改善（ステータスバー + activity_update シグナル）
- [x] `requirements.txt` に `dxcam`, `opencv-python-headless`, `pytesseract`, `numpy` を追加

### ドキュメント

- [x] `docs/` フォルダの整備（ARCHITECTURE, TROUBLESHOOTING, DEVELOPMENT_LOG 等）
- [x] ドキュメントの命名規則統一（略語廃止: SPEC → SPECIFICATION）
- [x] docs/SPECIFICATION.md に Phase 1 の受信翻訳を反映
- [x] docs/ROADMAP.md の Phase 1 ステータスを更新

### 残課題（リリース前に必須）

- [ ] 管理者権限でアプリを起動しての実機動作確認
- [ ] ゲーム画面での OCR 精度検証・チューニング
- [ ] `ChatBridge.spec` の調整（Tesseract バイナリ + tessdata 同梱）
- [ ] `version.py` を `2.0.0` に更新
- [ ] CHANGELOG.md の [Unreleased] を [2.0.0] に変更してリリース
