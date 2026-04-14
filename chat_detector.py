"""
チャットメッセージ差分検出モジュール

前回の OCR 結果と現在の OCR 結果を比較し、新しいメッセージのみを抽出する。
OCR のノイズを考慮し、完全一致ではなく類似度ベースの比較を行う。
"""

from difflib import SequenceMatcher


class ChatDetector:
    """チャットメッセージの差分検出"""

    # 類似度がこの閾値以上なら「同じ行」と見なす
    SIMILARITY_THRESHOLD = 0.75

    # この文字数以下の行はノイズとして除外
    MIN_LINE_LENGTH = 2

    def __init__(self):
        self._previous_lines: list[str] = []

    def detect_new_messages(self, current_text: str) -> list[str]:
        """
        前回の結果と比較し、新しいメッセージ行を返す。

        戦略:
        1. テキストを行分割し、短すぎる行を除外
        2. 現在の各行を前回の行リストと類似度比較
        3. 前回に類似する行がなければ「新しいメッセージ」とする
        4. 前回の行リストを更新

        Args:
            current_text: 現在の OCR 結果テキスト

        Returns:
            新しいメッセージ行のリスト
        """
        # 現在のテキストを行分割してフィルタリング
        current_lines = self._filter_lines(current_text)

        # 初回は全行を「新しい」として返すが、
        # 起動直後に大量の翻訳が走るのを避けるためスキップ
        if not self._previous_lines:
            self._previous_lines = current_lines.copy()
            return []

        # テキストが全く変わっていない場合はスキップ
        if current_lines == self._previous_lines:
            return []

        # 新しい行を検出
        new_messages = []
        for line in current_lines:
            if not self._has_similar_line(line, self._previous_lines):
                new_messages.append(line)

        # 前回の行リストを更新
        self._previous_lines = current_lines.copy()

        return new_messages

    def _filter_lines(self, text: str) -> list[str]:
        """
        テキストを行分割し、ノイズ行を除去する。

        - 空行を除去
        - 短すぎる行を除去
        - 前後の空白をトリム
        """
        lines = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if len(line) > self.MIN_LINE_LENGTH:
                lines.append(line)
        return lines

    def _has_similar_line(self, target: str, line_list: list[str]) -> bool:
        """
        行リスト内に target と類似する行が存在するか判定する。

        SequenceMatcher で類似度を計算し、閾値以上なら「同じ」と見なす。
        OCR の微妙な認識揺れ（句読点の有無、スペースの違い等）を吸収する。
        """
        for line in line_list:
            ratio = SequenceMatcher(None, target, line).ratio()
            if ratio >= self.SIMILARITY_THRESHOLD:
                return True
        return False

    def reset(self) -> None:
        """前回の検出結果をリセットする（エリア変更時などに呼ぶ）"""
        self._previous_lines = []
