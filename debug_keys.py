"""
ホットキーのデバッグ用スクリプト
Ctrl+J を押したときに pynput がどんなキー情報を受け取るか確認する。
Ctrl+C で終了。
"""

from pynput import keyboard

def on_press(key):
    try:
        # KeyCode の場合
        if isinstance(key, keyboard.KeyCode):
            print(f"[PRESS] KeyCode: char={key.char!r}, vk={key.vk}")
        else:
            # Key (修飾キー等) の場合
            print(f"[PRESS] Key: {key}, value={key.value}")
    except Exception as e:
        print(f"[PRESS] Error: {e}")

def on_release(key):
    try:
        if isinstance(key, keyboard.KeyCode):
            print(f"[RELEASE] KeyCode: char={key.char!r}, vk={key.vk}")
        else:
            print(f"[RELEASE] Key: {key}")
    except Exception as e:
        print(f"[RELEASE] Error: {e}")

    # Esc で終了
    if key == keyboard.Key.esc:
        print("--- 終了 ---")
        return False

print("=== キー入力デバッグ ===")
print("キーを押すと情報が表示されます。")
print("Ctrl+J を押してみてください。")
print("Esc で終了します。")
print("========================")

with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()
