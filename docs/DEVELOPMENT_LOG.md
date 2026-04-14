# ChatBridge 開発ログ

---

## 2026-04-14: 受信翻訳パイプラインのデバッグと修正

### 問題

受信翻訳をオンにするとオーバーレイウィンドウは表示されるが、
翻訳結果が一切表示されない。

### 調査

デバッグスクリプトで受信翻訳パイプラインの各段階を個別テストした。

| 段階 | 結果 |
|---|---|
| 1. 画面キャプチャ (DXcam) | ✅ 正常（850x658 フレーム取得） |
| 2. Tesseract OCR | ✅ 正常（インストール済み、パス探索OK） |
| 3. 差分検出 (ChatDetector) | ✅ 正常 |
| 4. 翻訳 (MyMemory API) | ❌ — `source=None` が渡されていた |

### 根本原因

`config.json` に `"recv_source_lang": null` が保存されていた。

`Config.get("recv_source_lang", target)` は、キーが存在するため
デフォルト値 `target` を使わず `None` をそのまま返す。
この `None` が翻訳 API に `source=None` として渡され、翻訳が失敗していた。

```python
# 旧コード（バグあり）
recv_source = self._config.get("recv_source_lang", target)  # → None
recv_target = self._config.get("recv_target_lang", source)  # → None

# 翻訳 API には source=None, target=None が渡される
translator.translate(msg, source=None, target=None)  # 失敗
```

### 修正内容

#### 1. `capture_service.py` — 言語フォールバックの修正

`_get_recv_langs()` メソッドを新設。`None` や空文字の場合は
送信翻訳と逆方向にフォールバックする。

```python
def _get_recv_langs(self) -> tuple[str, str]:
    source = self._config.get("source_lang", "ja")
    target = self._config.get("target_lang", "en")
    recv_source = self._config.get("recv_source_lang", None)
    recv_target = self._config.get("recv_target_lang", None)

    # None の場合は送信翻訳と逆方向をデフォルトとする
    if not recv_source:
        recv_source = target
    if not recv_target:
        recv_target = source

    return recv_source, recv_target
```

#### 2. `capture_service.py` — エラーの可視化

- `activity_update` シグナルを追加
- パイプラインの各段階の状態をリアルタイムで通知
- 連続失敗時の `error_occurred` シグナル発行
- ループ内の例外にスタックトレース出力を追加

#### 3. `recv_overlay.py` — ステータスバー追加

オーバーレイ下部にステータスバーを追加。
`activity_update` シグナルの内容をリアルタイム表示する。

表示例:
- `スキャン開始...`
- `スキャン中... 5行検出 (#12)`
- `テキスト未検出 (空: 3回連続)`
- `翻訳中... 2件の新メッセージ`
- `翻訳エラー: ...`
- `キャプチャ待機中... (失敗: 3回)`

#### 4. `main.py` — シグナル接続

`activity_update` シグナルを `recv_overlay.update_status` に接続。

#### 5. オーバーレイ自動非表示 + ターゲットアプリ指定

- `recv_auto_hide` 設定: 特定のアプリがアクティブな時のみオーバーレイを表示
- `recv_target_app` 設定: 監視対象アプリのウィンドウタイトル（自動検出 + 手動変更可）
- 受信翻訳開始時にフォアグラウンドアプリを自動検出

### 変更ファイル

| ファイル | 変更内容 |
|---|---|
| `capture_service.py` | 全面改修（言語バグ修正 + エラー可視化） |
| `recv_overlay.py` | ステータスバー追加 |
| `main.py` | `activity_update` シグナル接続 + 自動非表示ロジック |
| `settings_ui.py` | 自動非表示チェックボックス + ターゲットアプリ入力欄 |
| `config.py` | `recv_auto_hide`, `recv_target_app` デフォルト追加 |
| `i18n.py` | 関連 UI 文言の日英追加 |
| `requirements.txt` | `dxcam`, `opencv-python-headless`, `pytesseract`, `numpy` 追加 |

### 検証

```
[旧] config.get(recv_source_lang, en) = None   ← バグ
[新] _get_recv_langs() = ('en', 'ja')           ← 正常
```

### 残課題

- [ ] 管理者権限でアプリを起動しての実機動作確認
- [ ] ゲーム画面での OCR 精度検証・チューニング
