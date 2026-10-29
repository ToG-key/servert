import os
import time
import json
import threading
from flask import Flask, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit

app = Flask(__name__, static_folder='.', static_url_path='')
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me")

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

clients = {}
admins = set()
lock = threading.Lock()
CLIENT_TIMEOUT = 15

@app.route("/")
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route("/status")
def home():
    return jsonify({"status": "ok", "clients": len(clients), "admins": len(admins)})

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

# Luồng tự động đẩy (dự phòng)
def auto_realtime_loop():
    while True:
        if admins:
            payload = {"event": "clients", "clients": snapshot_clients()}
            for sid in list(admins):
                try:
                    socketio.emit("admin_event", payload, to=sid)
                except:
                    admins.discard(sid)
        time.sleep(2) # 2 giây/lần

@socketio.on("connect")
def on_connect(auth):
    pass

@socketio.on("register")
def on_register(data):
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
        notify_admins("client_joined", {
            "client": info["hostname"],
            "client_id": client_id,
        })
        emit("registered", {"ok": True, "client_id": client_id})

    elif role == "admin":
        admins.add(sid)
        emit("registered", {"ok": True})
        emit("admin_event", {"event": "init", "clients": snapshot_clients()})

@socketio.on("heartbeat")
def on_heartbeat(data):
    client_id = data.get("client_id")
    with lock:
        if client_id in clients and clients[client_id]["sid"] == request.sid:
            clients[client_id]["last_seen"] = time.time()
    emit("pong", {})

@socketio.on("admin_command")
def on_admin_command(data):
    if request.sid not in admins:
        return
    action = data.get("action")

    if action == "list":
        # Trả lời NGAY LẬP TỨC khi Web hỏi (Polling 1s)
        emit("admin_event", {"event": "clients", "clients": snapshot_clients()})

    elif action == "send":
        target = data.get("client_id")
        msg = data.get("message", "")
        with lock:
            c = clients.get(target)
        if c:
            socketio.emit("admin_msg", {"message": msg}, to=c["sid"])
            emit("admin_event", {"event": "sent", "ok": True, "client_id": target})
        else:
            emit("admin_event", {"event": "sent", "ok": False, "error": "client not found"})
    
    elif action == "broadcast":
        msg = data.get("message", "")
        if msg:
            for cid, info in clients.items():
                socketio.emit("admin_msg", {"message": f"[THÔNG BÁO] {msg}"}, to=info["sid"])
            notify_admins("broadcast_sent", {"message": msg})
            emit("admin_event", {"event": "broadcast_sent", "ok": True, "message": msg})

    elif action == "exec":
        target = data.get("client_id")
        cmd = data.get("command", "")
        with lock:
            c = clients.get(target)
        if c:
            socketio.emit("exec_command", {"command": cmd, "admin_sid": request.sid}, to=c["sid"])
            emit("admin_event", {"event": "exec_sent", "ok": True, "client_id": target})
        else:
            emit("admin_event", {"event": "exec_sent", "ok": False, "error": "client not found"})

@socketio.on("exec_result")
def on_exec_result(data):
    admin_sid = data.get("admin_sid")
    if admin_sid:
        socketio.emit("admin_event", {
            "event": "exec_result",
            "output": data.get("output", ""),
            "client_id": data.get("client_id", "")
        }, to=admin_sid)

@socketio.on("disconnect")
def on_disconnect():
    sid = request.sid
    if sid in admins:
        admins.discard(sid)
        return

    removed = None
    with lock:
        for cid, info in list(clients.items()):
            if info["sid"] == sid:
                removed = (cid, info["hostname"])
                del clients[cid]
                break
    if removed:
        notify_admins("client_left", {
            "client": removed[1], "client_id": removed[0]
        })

if __name__ == "__main__":
    # Khởi động luồng đẩy dữ liệu (dự phòng)
    threading.Thread(target=auto_realtime_loop, daemon=True).start()
    
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port)
