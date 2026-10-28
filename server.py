import os
import time
import json
import threading
import socket
import sys

def check_local_ip():
    """Hàm lấy IP nội bộ của máy tính và kiểm tra"""
    try:
        # Tạo một kết nối UDP giả để lấy IP của card mạng đang dùng
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"

# Kiểm tra IP
ALLOWED_IP = "192.168.1.46"
current_ip = check_local_ip()

if current_ip != ALLOWED_IP:
    print(f"[-] CẢNH BÁO: IP của bạn là {current_ip}.")
    print(f"[-] Tool này chỉ được phép chạy trên máy có IP: {ALLOWED_IP}")
    print("[-] Đang tự động thoát...")
    time.sleep(3) # Chờ 3 giây rồi tắt
    sys.exit()
from flask import Flask, jsonify
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me")

# eventlet giúp WebSocket chạy mượt trên Render
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# ---------- LƯU TRỮ ----------
clients = {}    # client_id -> {"sid", "hostname", "os", "room", "ip", "last_seen"}
admins = set()  # set các sid admin
lock = threading.Lock()

CLIENT_TIMEOUT = 15   # giây không heartbeat = offline


# ---------- HTTP ENDPOINTS ----------
@app.route("/")
def home():
    return jsonify({
        "status": "ok",
        "clients": len(clients),
        "admins": len(admins),
    })


def snapshot_clients():
    now = time.time()
    with lock:
        return [
            {
                "client_id": cid,
                "hostname": info["hostname"],
                "os": info["os"],
                "room": info["room"],
                "ip": info["ip"],
                "online_for": round(now - info["last_seen"], 1),
            }
            for cid, info in clients.items()
            if now - info["last_seen"] <= CLIENT_TIMEOUT
        ]


def notify_admins(event, data):
    payload = {"event": event, **data}
    for sid in list(admins):
        try:
            socketio.emit("admin_event", payload, to=sid)
        except:
            admins.discard(sid)


# ---------- SOCKET EVENTS ----------
@socketio.on("connect")
def on_connect(auth):
    print(f"[+] New connection: {auth}")


@socketio.on("register")
def on_register(data):
    """Message đầu tiên client/admin gửi lên"""
    from flask import request
    sid = request.sid
    role = data.get("type")

    if role == "client":
        client_id = data["client_id"]
        info = {
            "sid": sid,
            "hostname": data.get("hostname", "?"),
            "os": data.get("os", "?"),
            "room": data.get("room", "general"),
            "ip": request.remote_addr,
            "last_seen": time.time(),
        }
        with lock:
            clients[client_id] = info
        print(f"[CLIENT+] {client_id} ({info['hostname']}) từ {info['ip']}")
        notify_admins("client_joined", {
            "client": info["hostname"],
            "client_id": client_id,
        })
        emit("registered", {"ok": True, "client_id": client_id})

    elif role == "admin":
        admins.add(sid)
        print(f"[ADMIN+] {request.remote_addr}")
        emit("registered", {"ok": True})
        emit("admin_event", {
            "event": "init",
            "clients": snapshot_clients(),
        })


@socketio.on("heartbeat")
def on_heartbeat(data):
    from flask import request
    client_id = data.get("client_id")
    with lock:
        if client_id in clients and clients[client_id]["sid"] == request.sid:
            clients[client_id]["last_seen"] = time.time()
    emit("pong", {})


@socketio.on("admin_command")
def on_admin_command(data):
    from flask import request
    if request.sid not in admins:
        return
    action = data.get("action")

    if action == "list":
        emit("admin_event", {"event": "clients", "clients": snapshot_clients()})

    elif action == "send":
        target = data.get("client_id")
        msg = data.get("message", "")
        with lock:
            c = clients.get(target)
        if c:
            socketio.emit("admin_msg", {"message": msg}, to=c["sid"])
            print(f"[ADMIN→{c['hostname']}] {msg}")
            emit("admin_event", {"event": "sent", "ok": True, "client_id": target})
        else:
            emit("admin_event", {
                "event": "sent", "ok": False, "error": "client not found"
            })


@socketio.on("disconnect")
def on_disconnect():
    from flask import request
    sid = request.sid

    # Nếu là admin
    if sid in admins:
        admins.discard(sid)
        print(f"[ADMIN-] {sid}")
        return

    # Nếu là client → tìm và xoá
    removed = None
    with lock:
        for cid, info in list(clients.items()):
            if info["sid"] == sid:
                removed = (cid, info["hostname"])
                del clients[cid]
                break
    if removed:
        print(f"[CLIENT-] {removed[1]} ({removed[0]})")
        notify_admins("client_left", {
            "client": removed[1], "client_id": removed[0]
        })


# ---------- MAIN ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port)
