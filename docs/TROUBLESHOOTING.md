# ChatBridge トラブルシューティングガイド

最終更新日: 2026-04-14

---

## 受信翻訳（OCR 画面翻訳）

### オーバーレイが表示されるが翻訳結果が出ない

受信翻訳のパイプラインは以下の 5 段階で動作する。
ステータスバー（オーバーレイ下部）を確認して、どこで止まっているか特定する。

```
1. 画面キャプチャ  → 「キャプチャ待機中...」が表示され続ける場合
2. OCR             → 「テキスト未検出」が表示され続ける場合
3. 差分検出        → 「スキャン中... N行検出」と出るが翻訳されない場合
4. 翻訳            → 「翻訳エラー: ...」が表示される場合
5. シグナル通知    → 上記すべて正常なのに表示されない場合
```

#### 1. キャプチャが失敗する場合

**症状**: ステータスバーに「キャプチャ待機中... (失敗: N回)」と表示される

**原因と対処**:
- ゲームが **排他フルスクリーンモード** で動作している
  → **ボーダーレスウィンドウモード** に変更する
- DXcam が初期化に失敗している
  → アプリを再起動する

#### 2. OCR でテキストが認識されない場合

**症状**: ステータスバーに「テキスト未検出 (空: N回連続)」と表示される

**原因と対処**:

| 原因 | 確認方法 | 対処 |
|---|---|---|
| Tesseract 未インストール | エラーダイアログが表示される | [Tesseract をインストール](https://github.com/UB-Mannheim/tesseract/wiki) |
| 言語データ不足 | Tesseract に必要な言語がない | Tesseract インストーラで `jpn`, `eng` 等を追加 |
| キャプチャ範囲が不適切 | 設定画面でエリアを再指定 | チャット欄だけを正確に囲む |
| ゲームフォントが認識困難 | テスト用にメモ帳等で試す | 前処理パラメータの調整が必要 |

**Tesseract のインストール確認**:
```powershell
# インストール先の確認
Test-Path "C:\Program Files\Tesseract-OCR\tesseract.exe"

# バージョン確認
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --version

# 利用可能な言語
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --list-langs
```

#### 3. テキストは検出されるが新メッセージとして認識されない場合

**症状**: ステータスバーに「スキャン中... N行検出」と表示されるが翻訳が出ない

**原因と対処**:
- **初回スキャン**: 最初の 1 回は意図的にスキップされる（起動直後の翻訳ラッシュ防止）
  → 新しいメッセージが送信されるのを待つ
- **チャット内容が変化していない**: 差分検出は前回との比較なので、同じ内容では反応しない
  → 新しいメッセージを送ってもらう
- **OCR 結果が毎回異なる**: ノイズが多いと毎回「新メッセージ」と誤検出される可能性がある
  → キャプチャ範囲をテキストだけに絞る

#### 4. 翻訳エラーが発生する場合

**症状**: ステータスバーに「翻訳エラー: ...」と表示される

**原因と対処**:
- **API 制限**: MyMemory の 1 日 5,000 文字制限に達した
  → 設定でメールアドレスを登録する（50,000 文字に増加）
- **ネットワークエラー**: インターネット接続を確認
- **`recv_source_lang` が null**: 初期実装時のバグ。`_get_recv_langs()` のフォールバック処理で修正済み

---

### 受信翻訳の言語方向について

受信翻訳は **送信翻訳と逆方向** がデフォルト。

| 設定 | 送信翻訳 | 受信翻訳 |
|---|---|---|
| `source_lang: ja`, `target_lang: en` | 日→英 | 英→日 |
| `source_lang: ja`, `target_lang: zh` | 日→中 | 中→日 |

`recv_source_lang` / `recv_target_lang` を明示的に設定すれば、
送信翻訳とは独立した言語方向にカスタマイズ可能。

---

## 送信翻訳

### ホットキーが反応しない

- **管理者権限**: ChatBridge は管理者権限で起動する必要がある
- **キー競合**: 他のアプリが同じホットキーを使っていないか確認
- **一時停止**: トレイメニューで「一時停止」していないか確認

### オーバーレイが表示されない

- **画面モード**: ゲームをボーダーレスウィンドウモードに変更
- **フォーカス**: ゲーム画面がアクティブか確認

### 翻訳結果が空 / 文字化けする

- **Ctrl+A/C が効かないゲーム**: テキスト取得方式の制約（クリップボード経由）
- **チャット欄が空**: 何か入力してからホットキーを押す

---

## 一般的な問題

### 二重起動の警告が出る

前回の ChatBridge が正常に終了していない可能性がある。
タスクマネージャーで `ChatBridge.exe` や `python.exe` を終了してから再起動する。

### 自動起動が機能しない

タスクスケジューラの登録状態を確認:
```powershell
Get-ScheduledTask -TaskName "ChatBridge" -ErrorAction SilentlyContinue
```

### 設定がリセットされた

`config.json` が破損した場合、デフォルト設定で上書きされる。
バックアップがない場合は設定画面から再設定する。

---

## デバッグ方法

### コンソールログの確認

開発時（`python main.py`）はコンソールにパイプラインの状態が出力される。

```
[CaptureService] ループ開始: region=(277, 158, 1127, 816), interval=2.0s, ocr_lang=eng
```

### パイプラインの個別テスト

各段階を個別にテストするスクリプト例:

```python
# 1. キャプチャテスト
from screen_capture import ScreenCapture
cap = ScreenCapture()
frame = cap.grab((277, 158, 1127, 816))
print(f"shape: {frame.shape}" if frame is not None else "FAILED")

# 2. OCR テスト
from ocr import create_ocr_engine
ocr = create_ocr_engine("tesseract")
print(f"available: {ocr.is_available()}")
text = ocr.recognize(frame, lang="eng")
print(f"result: {repr(text[:200])}")

# 3. 差分検出テスト
from chat_detector import ChatDetector
detector = ChatDetector()
result = detector.detect_new_messages(text)  # 初回は空
# テキストを変更して再度呼ぶと差分が検出される

# 4. 翻訳テスト
from translator import create_translator
t = create_translator("mymemory", {})
print(t.translate("Hello", source="en", target="ja"))
```
