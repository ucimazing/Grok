from pynput import keyboard
import socket
import time
import pyperclip
from AppKit import NSPasteboard, NSFilenamesPboardType  # For file detection


class KeyboardClient:
    def __init__(self):
        self.host = '192.168.0.62'  # Replace with your Windows PC's IP
        self.port = 65432
        self.enabled = False
        self.socket = None
        self.holding_keys = set()
        self.pasteboard = NSPasteboard.generalPasteboard()  # macOS clipboard access
        self.setup_connection()

        # Define special key mappings
        self.special_keys = {
            keyboard.Key.space: 'space',
            keyboard.Key.enter: 'enter',
            keyboard.Key.backspace: 'backspace',
            keyboard.Key.delete: 'delete',
            keyboard.Key.tab: 'tab',
            keyboard.Key.left: 'left',
            keyboard.Key.right: 'right',
            keyboard.Key.up: 'up',
            keyboard.Key.down: 'down',
            keyboard.Key.home: 'home',
            keyboard.Key.end: 'end',
            keyboard.Key.page_up: 'pageup',
            keyboard.Key.page_down: 'pagedown',
            keyboard.Key.esc: 'esc',
            keyboard.Key.caps_lock: 'capslock',
        }

    def setup_connection(self):
        while True:
            try:
                if self.socket:
                    self.socket.close()
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((self.host, self.port))
                print("✅ Connected to Windows PC")
                break
            except Exception as e:
                print(f"❌ Connection failed: {e}")
                print("Retrying in 5 seconds...")
                time.sleep(5)

    def send_data(self, message):
        try:
            self.socket.send(message.encode() if isinstance(message, str) else message)
            return True
        except Exception as e:
            print(f"Error sending data, reconnecting... ({e})")
            self.setup_connection()
            return False

    def send_key(self, key_str, is_special=False):
        try:
            if not key_str:
                return
            if is_special:
                key_str = f"<SPECIAL>{key_str}"
            self.send_data(f"{key_str}\n")
            print(f"Sent: {key_str}")
            return True
        except Exception as e:
            print(f"Error in send_key: {e}")
            return False

    def send_clipboard(self):
        # Check if clipboard has a file
        pb_types = self.pasteboard.types()
        if NSFilenamesPboardType in pb_types:
            file_paths = self.pasteboard.propertyListForType_(NSFilenamesPboardType)
            if file_paths and len(file_paths) > 0:
                file_path = file_paths[0]  # Handle first file
                print(f"Detected file: {file_path}")

                # Read file as binary
                with open(file_path, 'rb') as f:
                    file_data = f.read()

                # Send file metadata and content
                file_name = file_path.split('/')[-1]
                file_size = len(file_data)
                header = f"<FILE>{file_name}|{file_size}\n"
                self.send_data(header)
                self.send_data(file_data)
                print(f"Sent file: {file_name} ({file_size} bytes)")
            else:
                print("No valid file in clipboard")
        else:
            # Handle text clipboard
            clipboard_content = pyperclip.paste()
            if clipboard_content:
                self.send_data(f"<CLIPBOARD>{clipboard_content}\n")
                print(f"Sent text clipboard: {clipboard_content[:50]}...")
            else:
                print("Clipboard is empty")

    def run_listener(self):
        def on_press(key):
            # Add key to holding keys
            key_str = str(key)
            self.holding_keys.add(key_str)

            # Check for clipboard sharing (Control + Option + C)
            if ("Key.ctrl" in self.holding_keys and
                    "Key.alt" in self.holding_keys and  # Option is alt in pynput
                    "'c'" in self.holding_keys):
                self.send_clipboard()
                self.holding_keys.clear()
                return True

            # Check for toggle combination (Command + Shift + Space)
            if ("Key.cmd" in self.holding_keys and
                    "Key.shift" in self.holding_keys and
                    "Key.space" in self.holding_keys):
                self.enabled = not self.enabled
                print(f"Keyboard sharing: {'ON' if self.enabled else 'OFF'}")
                self.holding_keys.clear()
                return True

            # If sharing is enabled, send key to Windows
            if self.enabled:
                try:
                    if key in self.special_keys:
                        self.send_key(self.special_keys[key], is_special=True)
                    elif hasattr(key, 'char') and key.char:
                        self.send_key(key.char)
                    else:
                        key_str = str(key).replace('Key.', '')
                        self.send_key(key_str, is_special=True)
                    return False  # Block on Mac when enabled
                except Exception as e:
                    print(f"Error handling key: {e}")
                    return False
            return True  # Allow normal operation when disabled

        def on_release(key):
            key_str = str(key)
            self.holding_keys.discard(key_str)
            if self.enabled:
                return False
            return True

        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()

    def run(self):
        print("Starting keyboard client...")
        print("Press Command + Shift + Space to toggle keyboard sharing")
        print("Press Control + Option + C to share clipboard (text or file)")
        print("Current status: OFF")

        while True:
            try:
                self.run_listener()
            except Exception as e:
                print(f"Error in listener: {e}")
                print("Restarting listener...")
                time.sleep(1)


if __name__ == "__main__":
    while True:
        try:
            client = KeyboardClient()
            client.run()
        except Exception as e:
            print(f"Program error: {e}")
            print("Restarting program...")
            time.sleep(3)