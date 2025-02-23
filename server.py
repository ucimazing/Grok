import socket
import keyboard
import pyperclip
import time
import os


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(downloads_dir, exist_ok=True)

    try:
        server.bind(('0.0.0.0', 65432))
        server.listen(1)
        print("\n🖥️  Windows Keyboard Server Started")
        print("⏳ Waiting for MacBook to connect...\n")

        while True:
            conn, addr = server.accept()
            print(f"✅ MacBook connected from {addr}")

            try:
                buffer = ""
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break

                    if buffer and buffer.startswith('<FILE>'):
                        # Handle file data
                        header, buffer = buffer.split('\n', 1)
                        file_name, file_size = header[6:].split('|')
                        file_size = int(file_size)
                        file_path = os.path.join(downloads_dir, file_name)

                        with open(file_path, 'wb') as f:
                            received = len(buffer)
                            f.write(buffer.encode() if isinstance(buffer, str) else buffer)

                            while received < file_size:
                                more_data = conn.recv(1024)
                                if not more_data:
                                    break
                                f.write(more_data)
                                received += len(more_data)

                        print(f"📄 File saved: {file_path}")
                        pyperclip.copy(file_path)  # Set clipboard to file path
                        buffer = ""

                    else:
                        # Handle text or key data
                        buffer += data.decode()
                        while '\n' in buffer:
                            msg, buffer = buffer.split('\n', 1)
                            msg = msg.strip()

                            if msg:
                                print(f"📥 Received: {msg[:50]}...")

                                if msg.startswith('<CLIPBOARD>'):
                                    clipboard_content = msg[11:]
                                    pyperclip.copy(clipboard_content)
                                    print(f"📋 Clipboard updated: {clipboard_content[:50]}...")
                                elif msg.startswith('<SPECIAL>'):
                                    key_str = msg[9:]
                                    keyboard.press_and_release(key_str)
                                elif msg.startswith('<FILE>'):
                                    continue  # Wait for file data
                                else:
                                    keyboard.write(msg)

            except Exception as e:
                print(f"❌ Error: {e}")
            finally:
                print("📴 MacBook disconnected")
                conn.close()

    except Exception as e:
        print(f"❌ Server error: {e}")
    finally:
        server.close()


if __name__ == "__main__":
    while True:
        try:
            start_server()
        except Exception as e:
            print(f"❌ Server crashed: {e}")
            print("🔄 Restarting server in 5 seconds...")
            time.sleep(5)