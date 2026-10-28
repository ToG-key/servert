import socketio
import time
import platform
import uuid
import os
import socket

# ---------- CẤU HÌNH ----------
# Sửa domain Render của bạn
SERVER_URL = os.environ.get("SERVER_URL", "https://your-app.onrender.com")

ID_FILE = ".client_id"
if os.path.exists(ID_FILE):
    CLIENT_ID = open(ID_FILE).read().strip()
else:
    CLIENT_ID = str(uuid.uuid4())[:8]
    open(ID_FILE, "w").write(CLIENT_ID)

HOSTNAME = socket.gethostname()
OS = f"{platform.system()} {platform.release()}"
ROOM = os.environ.get("ROOM", "general")

sio = socketio.Client(
    reconnection=True,
    reconnection_delay=3,
    reconnection_delay_max=10,
)


@sio.event
def connect():
    print("[CLIENT] ✅ Đã kết nối server")
    sio.emit("register", {
        "type": "client",
        "client_id": CLIENT_ID,
        "hostname": HOSTNAME,
        "os": OS,
        "room": ROOM,
    })


@sio.on("registered")
def on_registered(data):
    print(f"[CLIENT] Đăng ký OK: {data}")


@sio.on("admin_msg")
def on_admin_msg(data):
    print(f"\n📨 [ADMIN] {data['message']}")


@sio.event
def disconnect():
    print("[CLIENT] ⚠️ Mất kết nối, đang thử lại...")


def heartbeat_loop():
    while True:
        if sio.connected:
            try:
                sio.emit("heartbeat", {"client_id": CLIENT_ID})
            except:
                pass
        time.sleep(5)


def main():
    print(f"[CLIENT] ID={CLIENT_ID} | Host={HOSTNAME} | OS={OS} | Room={ROOM}")
    print(f"[CLIENT] Server: {SERVER_URL}")
    print("[CLIENT] Đang kết nối...\n")

    # thread heartbeat
    import threading
    threading.Thread(target=heartbeat_loop, daemon=True).start()

    try:
        sio.connect(SERVER_URL, transports=["websocket"])
        sio.wait()
    except KeyboardInterrupt:
        print("\n[CLIENT] Thoát.")
        sio.disconnect()


if __name__ == "__main__":
    main()
