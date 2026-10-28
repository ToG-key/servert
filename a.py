import socketio
import time
import os
import threading
import sys

# ---------- CẤU HÌNH ----------
SERVER_URL = os.environ.get("SERVER_URL", "https://your-app.onrender.com")

sio = socketio.Client(
    reconnection=True,
    reconnection_delay=3,
)

# Lưu danh sách client mới nhất để hiển thị
latest_clients = []


def print_clients(clients):
    print("\n" + "=" * 100)
    print(f"{'ID':<12} {'HOSTNAME':<25} {'OS':<20} {'ROOM':<12} {'IP':<16} {'ONLINE'}")
    print("-" * 100)
    for c in clients:
        print(
            f"{c['client_id']:<12} "
            f"{c.get('hostname','?'):<25} "
            f"{c.get('os','?'):<20} "
            f"{c.get('room','?'):<12} "
            f"{c.get('ip','?'):<16} "
            f"{c.get('online_for', 0)}s"
        )
    print("=" * 100)
    print(f"Tổng: {len(clients)} client online\n")


@sio.event
def connect():
    print("[ADMIN] ✅ Đã kết nối server")
    sio.emit("register", {"type": "admin"})


@sio.on("registered")
def on_registered(data):
    print(f"[ADMIN] Đăng ký OK")


@sio.on("admin_event")
def on_admin_event(msg):
    global latest_clients
    ev = msg.get("event")

    if ev in ("init", "clients"):
        latest_clients = msg.get("clients", [])
        print_clients(latest_clients)

    elif ev == "client_joined":
        print(f"\n🟢 JOIN: {msg['client']} ({msg['client_id']})")

    elif ev == "client_left":
        print(f"\n🔴 LEFT: {msg['client']} ({msg['client_id']})")

    elif ev == "sent":
        if msg.get("ok"):
            print(f"\n📤 Đã gửi tới {msg['client_id']}")
        else:
            print(f"\n⚠️  Không gửi được: {msg.get('error')}")


@sio.event
def disconnect():
    print("[ADMIN] ⚠️ Mất kết nối, đang thử lại...")


def main():
    print(f"[ADMIN] Server: {SERVER_URL}")
    print("[ADMIN] Đang kết nối...\n")

    try:
        sio.connect(SERVER_URL, transports=["websocket"])
    except Exception as e:
        print(f"[ERR] {e}")
        return

    # Chờ đăng ký xong
    time.sleep(1)

    while True:
        print("\n--- MENU ADMIN ---")
        print("1. Xem danh sách client")
        print("2. Gửi tin nhắn tới client")
        print("0. Thoát")
        choice = input("Chọn: ").strip()

        if choice == "1":
            sio.emit("admin_command", {"action": "list"})
            time.sleep(0.5)

        elif choice == "2":
            cid = input("client_id: ").strip()
            msg = input("Nội dung: ").strip()
            if cid and msg:
                sio.emit("admin_command", {
                    "action": "send",
                    "client_id": cid,
                    "message": msg,
                })
                time.sleep(0.3)

        elif choice == "0":
            sio.disconnect()
            break


if __name__ == "__main__":
    main()
