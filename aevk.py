import paho.mqtt.client as mqtt
import requests
import time
import json
import ssl
import hashlib
import os
import re
import threading
import random
import gc
import ctypes
from urllib.parse import urlparse
import warnings

from pystyle import Colors, Colorate

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

warnings.filterwarnings("ignore")


def log(text):
    """Log có màu bằng pystyle"""
    print(Colorate.Horizontal(Colors.rainbow, str(text), 1))


BANNER = ("""
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣴⡆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣾⣿⡾⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠠⣿⡿⠟⢀⣀⢤⡀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⡼⠟⠛⠛⠓⠙⠚⢡⣀⣀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡾⠋⠀⠀⠀⠀⠀⠀⠀⠀⢫⣍⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡾⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢻⡆⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢀⡶⠛⣶⡼⠃⠀⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣇⡀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⣾⠀⣀⣿⠀⠀⠘⠋⠀⣀⠀⠀⠀⠀⠀⠀⣠⡿⠙⣽⣷⣦⡀⠀
⠀⠀⠀⠀⠀⣿⣿⣿⣿⣧⡀⠀⠀⠈⠛⠃⠀⢾⠇⠀⠰⠾⠁⠀⠈⠻⢿⣿⡀
⠀⠀⠀⠀⠀⢸⣿⣿⣿⣿⣿⡳⡤⢀⡀⠀⠀⠀⠀⠀⣶⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢠⣿⣿⣿⣿⣿⣿⣶⣬⣽⣿⣶⣶⣶⣟⠙⠳⣦⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⣰⣿⣿⣿⣿⣷⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣇⣠⠟⠀⠀⠀⠀⠀⠀
⠀⠀⠀⢰⡏⠉⠉⠉⠉⠉⠛⠛⠻⠿⣽⣿⣿⣿⡛⠛⠉⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⡀⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠙⣿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⢠⡟⠉⠀⠀⠀⢰⡶⣤⣄⣀⣀⣀⣀⣀⠀⠀⠈⠉⠳⣆⠀⠀⠀⠀⠀⠀⠀⠀
⠛⠛⠒⠒⠒⠒⠛⠛⠀⠈⠉⠉⠉⠙⠓⠒⠲⠶⠖⠒⠓⠀⠀⠀⠀⠀⠀⠀⠀
╔═══════════════════════════════════════════╗
║ Tool Sender Facebook Mqtt Frv Void King 🪐 
║Owner : Tran Duy An w Khanh Huy w Long Nhat
╚═══════════════════════════════════════════╝
""")

UA = [
    "Mozilla/5.0 (Linux; Android 11; RMX2185) AppleWebKit/537.36 Chrome/121.0.6167.140 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; Redmi Note 11) AppleWebKit/537.36 Chrome/120.0.6099.129 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Pixel 6a) AppleWebKit/537.36 Chrome/122.0.6261.68 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; Redmi Note 8) AppleWebKit/537.36 Version/4.0 Chrome/108.0.0.0 Mobile Safari/537.36 Via/4.8.2",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
]

CK_FILE = "ck.txt"

# ==========================================================
# ==================== RAM CLEANER =========================
# ==========================================================

def _get_process():
    if _HAS_PSUTIL:
        try:
            return psutil.Process(os.getpid())
        except Exception:
            return None
    return None

_PROCESS = _get_process()


def _trim_malloc():
    """Trả bộ nhớ heap về OS (glibc - Linux)"""
    try:
        libc = ctypes.CDLL("libc.so.6")
        libc.malloc_trim(0)
    except Exception:
        pass


def _empty_working_set():
    """Windows: EmptyWorkingSet để giảm RAM thực tế"""
    try:
        if os.name == 'nt':
            psapi = ctypes.WinDLL('psapi.dll')
            kernel32 = ctypes.WinDLL('kernel32.dll')
            handle = kernel32.GetCurrentProcess()
            psapi.EmptyWorkingSet(handle)
    except Exception:
        pass


def get_ram_mb():
    try:
        if _PROCESS is not None:
            return _PROCESS.memory_info().rss / 1024 / 1024
    except Exception:
        pass
    return 0.0


def clean_ram(deep=False):
    """
    Dọn RAM:
    - gc.collect() nhiều gen
    - malloc_trim (Linux)
    - EmptyWorkingSet (Windows)
    - deep=True: dọn cả 3 gen + return
    """
    try:
        gc.collect(0)
        gc.collect(1)
        if deep:
            gc.collect(2)
            gc.collect()
    except Exception:
        pass
    _trim_malloc()
    _empty_working_set()


def start_ram_monitor(interval=30, threshold_mb=400):
    """
    Thread nền tự dọn RAM định kỳ.
    Nếu RAM vượt threshold => dọn sâu + log.
    """
    stop_flag = {"stop": False}

    def _loop():
        while not stop_flag["stop"]:
            time.sleep(interval)
            if stop_flag["stop"]:
                return
            try:
                ram = get_ram_mb()
                deep = ram > threshold_mb
                clean_ram(deep=deep)
                if deep:
                    log(f"[CLEAN] {ram:.1f}MB > {threshold_mb}MB "
                        f"(còn {get_ram_mb():.1f}MB)")
            except Exception:
                pass

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    return stop_flag, t

# ==================== END RAM CLEANER =====================
# ==========================================================


def loc_ssl():
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    context.set_ciphers(
        "ECDHE+AESGCM:ECDHE+CHACHA20:ECDHE+AES:RSA+AESGCM:RSA+AES:!aNULL:!eNULL:!MD5:!DSS"
    )
    return context


def extract_user_id(cookie):
    try:
        return re.search(r"c_user=(\d+)", cookie).group(1)
    except Exception:
        return None


def get_last_seq_id(cookie):
    try:
        headers = {
            'cookie': cookie,
            'user-agent': random.choice(UA),
        }
        r = requests.get('https://www.facebook.com/', headers=headers,
                         timeout=30, verify=False)
        if r.status_code == 200:
            m = re.search(r'"sync_sequence_id":"?(\d+)"?', r.text)
            if m:
                return m.group(1)
            m = re.search(r'"lastSeqId":"?(\d+)"?', r.text)
            if m:
                return m.group(1)
        return str(int(time.time() * 1000))
    except Exception:
        return str(int(time.time() * 1000))


def gen_otid():
    return str(int(time.time() * 1000))


def gen_session_id():
    return str(int(time.time() * 1000))


def gen_client_id():
    return hashlib.md5(str(time.time()).encode()).hexdigest()[:16]


def jmin(obj):
    return json.dumps(obj, separators=(',', ':'))


mqtt_lock = threading.Lock()


def on_connect_mqtt(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe([("/t_ms", 0)])
        queue = {
            "sync_api_version": 10,
            "max_deltas_able_to_process": 1000,
            "delta_batch_size": 500,
            "encoding": "JSON",
            "entity_fbid": userdata['user_id'],
            "initial_titan_sequence_id": userdata['last_seq_id'],
            "device_params": None,
        }
        client.publish("/messenger_sync_create_queue", jmin(queue),
                       qos=1, retain=False)


def on_disconnect_mqtt(client, userdata, rc):
    # Không reconnect (tránh leak + tốn RAM), chỉ dọn gc nhẹ
    if rc != 0:
        try:
            gc.collect(0)
        except Exception:
            pass


def connect_mqtt(cookie, user_id, last_seq_id, session_id):
    user = {
        "u": user_id,
        "s": session_id,
        "chat_on": jmin(True),
        "fg": False,
        "d": gen_client_id(),
        "ct": "websocket",
        "aid": 219994525426954,
        "mqtt_sid": "",
        "cp": 3,
        "ecp": 10,
        "st": ["/t_ms", "/messenger_sync_get_diffs",
               "/messenger_sync_create_queue"],
        "pm": [],
        "dc": "",
        "no_auto_fg": True,
        "gas": None,
        "pack": [],
    }

    host = f"wss://edge-chat.messenger.com/chat?region=eag&sid={session_id}"
    ua = random.choice(UA)

    client = mqtt.Client(
        client_id="mqttwsclient",
        clean_session=True,
        protocol=mqtt.MQTTv31,
        transport="websockets",
        userdata={'user_id': user_id, 'last_seq_id': last_seq_id},
    )

    client.tls_set_context(loc_ssl())
    client.on_connect = on_connect_mqtt
    client.on_disconnect = on_disconnect_mqtt
    client.username_pw_set(username=jmin(user))

    parsed = urlparse(host)
    client.ws_set_options(
        path=f"{parsed.path}?{parsed.query}",
        headers={
            "Cookie": cookie,
            "Origin": "https://www.messenger.com",
            "User-Agent": ua,
            "Referer": "https://www.messenger.com/",
            "Host": "edge-chat.messenger.com",
        },
    )

    try:
        client.connect("edge-chat.messenger.com", 443, keepalive=10)
        client.loop_start()
        return client
    except Exception:
        return None


class NguyenBaoKhanhHuy:
    def __init__(self, cookie):
        self.cookie = cookie
        self.user_id = None
        self.mqtt_client = None
        self.last_seq_id = None
        self.session_id = None
        self.ws_req_number = 0
        self.ws_task_number = 0
        self.alive = True

    def init(self):
        self.user_id = extract_user_id(self.cookie)
        if not self.user_id:
            return False, "Không trích xuất được user_id"

        self.last_seq_id = get_last_seq_id(self.cookie)
        if not self.last_seq_id:
            return False, "Không lấy được last_seq_id"

        self.session_id = gen_session_id()
        self.mqtt_client = connect_mqtt(
            self.cookie, self.user_id, self.last_seq_id, self.session_id
        )
        if not self.mqtt_client:
            return False, "Không kết nối được MQTT"

        return True, "OK"

    def NBKH(self, thread_id, text):
        if not self.alive:
            return
        self.ws_req_number += 1
        self.ws_task_number += 1

        content = {
            "app_id": "2220391788200892",
            "payload": {
                "data_trace_id": None,
                "epoch_id": int(gen_otid()),
                "tasks": [],
                "version_id": "7545284305482586",
            },
            "request_id": self.ws_req_number,
            "type": 3,
        }

        task_payload = {
            "initiating_source": 0,
            "multitab_env": 0,
            "otid": gen_otid(),
            "send_type": 1,
            "skip_url_preview_gen": 0,
            "source": 0,
            "sync_group": 1,
            "text": text,
            "text_has_links": 0,
            "thread_id": int(thread_id),
        }
        content["payload"]["tasks"].append({
            "failure_count": None,
            "label": "46",
            "payload": jmin(task_payload),
            "queue_name": str(thread_id),
            "task_id": self.ws_task_number,
        })

        self.ws_task_number += 1
        mark_payload = {
            "last_read_watermark_ts": int(time.time() * 1000),
            "sync_group": 1,
            "thread_id": int(thread_id),
        }
        content["payload"]["tasks"].append({
            "failure_count": None,
            "label": "21",
            "payload": jmin(mark_payload),
            "queue_name": str(thread_id),
            "task_id": self.ws_task_number,
        })

        content["payload"] = jmin(content["payload"])

        with mqtt_lock:
            self.mqtt_client.publish(
                "/ls_req", jmin(content), qos=1, retain=False
            )

    def close(self):
        """Giải phóng mạnh: MQTT client, socket, ref, gc"""
        self.alive = False
        try:
            if self.mqtt_client:
                try:
                    self.mqtt_client.loop_stop()
                except Exception:
                    pass
                try:
                    self.mqtt_client.disconnect()
                except Exception:
                    pass
                # Giải phóng socket buffer
                try:
                    sock = getattr(self.mqtt_client, '_sock', None)
                    if sock is not None:
                        try:
                            sock.close()
                        except Exception:
                            pass
                    self.mqtt_client._sock = None
                except Exception:
                    pass
                try:
                    self.mqtt_client._sock_close()
                except Exception:
                    pass
                self.mqtt_client = None
        except Exception:
            pass

        # Xoá ref lớn
        self.cookie = None
        self.last_seq_id = None
        self.session_id = None

        try:
            gc.collect(0)
        except Exception:
            pass


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def save_cookie_file(cookie_entries):
    """Lưu danh sách (cookie, delay) ra ck.txt"""
    try:
        with open(CK_FILE, 'w', encoding='utf-8') as f:
            for cookie, delay in cookie_entries:
                f.write(f"{cookie}|{delay}\n")
        return True
    except Exception as e:
        log(f"Lỗi ghi {CK_FILE}: {e}")
        return False


def load_cookie_file():
    """Đọc ck.txt. Trả về list (cookie, delay) đã lọc (bỏ dòng rc=...)"""
    entries = []
    try:
        with open(CK_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if "rc =" in line or "rc=" in line:
                    continue
                parts = line.split("|")
                if len(parts) < 2:
                    continue
                cookie = parts[0].strip()
                try:
                    delay = float(parts[1].strip())
                except ValueError:
                    continue
                if cookie:
                    entries.append((cookie, delay))
    except FileNotFoundError:
        return None
    except Exception as e:
        log(f"Lỗi đọc {CK_FILE}: {e}")
        return None
    return entries


def mark_cookie_rc(cookie, rc_value):
    """Đánh dấu cookie chết trong ck.txt: cookie|delay -> rc = {e}"""
    try:
        with open(CK_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        new_lines = []
        for line in lines:
            raw = line.rstrip('\n')
            if raw.strip() == "":
                continue
            if "rc =" in raw or "rc=" in raw:
                new_lines.append(raw)
                continue
            parts = raw.split("|")
            if parts and parts[0].strip() == cookie.strip():
                new_lines.append(f"rc = {rc_value}")
            else:
                new_lines.append(raw)

        with open(CK_FILE, 'w', encoding='utf-8') as f:
            f.write("\n".join(new_lines) + "\n")
    except Exception as e:
        log(f"Lỗi cập nhật {CK_FILE}: {e}")


def worker(session, index, thread_ids, messages, delay, lock, cleanup_every=50):
    """
    Mỗi worker (cookie) chạy vòng lặp:
    - Gửi tất cả các ngôn (messages) vào mỗi box trong thread_ids
    - delay => sang box kế tiếp
    - hết box => quay lại box 1
    - Tự dọn gc mỗi cleanup_every lần gửi để tránh tích rác
    """
    counter = 0
    while session.alive:
        for tid in thread_ids:
            if not session.alive:
                return
            for msg in messages:
                if not session.alive:
                    return
                try:
                    session.NBKH(tid, msg)
                except Exception as e:
                    with lock:
                        log(f"[SEND] | COOKIE {index+1} lỗi box {tid}: {e}")
                counter += 1
                if counter >= cleanup_every:
                    counter = 0
                    try:
                        gc.collect(0)
                    except Exception:
                        pass
            with lock:
                log(f"[SEND] | COOKIE {index+1} | BOX {tid} | OK")
            if delay > 0:
                time.sleep(delay)


def main():
    clear()
    log(BANNER)
    clean_ram(deep=True)

    cookie_entries = []  # list of (cookie, delay)

    # ===== Thử đọc ck.txt trước =====
    loaded = load_cookie_file()
    if loaded:
        log(f"Phát hiện {CK_FILE} có {len(loaded)} cookie còn sống.")
        ans = input("Dùng lại danh sách cookie này? (y/n): ").strip().lower()
        if ans == 'y':
            cookie_entries = loaded
            log(f"Đã nạp {len(cookie_entries)} cookie từ {CK_FILE}.")
        else:
            cookie_entries = []

    # ===== Nếu không dùng file => nhập tay =====
    if not cookie_entries:
        log("\nNhập cookies (gõ 'done' để kết thúc).")
        idx = 0
        while True:
            idx += 1
            cookie = input(f"Cookie {idx}: ").strip()
            if cookie.lower() == 'done':
                break
            if not cookie:
                idx -= 1
                continue

            while True:
                try:
                    d_input = input(f"  → Delay cho cookie {idx} (giây): ").strip()
                    delay = float(d_input)
                    if delay < 0:
                        log("Delay phải >= 0!")
                        continue
                    break
                except ValueError:
                    log("Delay không hợp lệ, nhập lại!")

            cookie_entries.append((cookie, delay))
            log(f"Đã thêm cookie {idx} (delay: {delay}s)")

        if not cookie_entries:
            log("Chưa có cookie nào!")
            return

        if save_cookie_file(cookie_entries):
            log(f"Đã lưu danh sách cookie vào {CK_FILE}.")

    # ===== Kết nối từng cookie =====
    log(f"\nĐang kết nối {len(cookie_entries)} cookie...")
    sessions = []      # list of (session, delay)
    dead_cookies = []  # cookie die ngay khi init

    for i, (cookie, delay) in enumerate(cookie_entries, 1):
        s = NguyenBaoKhanhHuy(cookie)
        ok, msg = s.init()
        if not ok:
            log(f"Cookie {i}: {msg}")
            dead_cookies.append(cookie)
            continue
        sessions.append((s, delay))
        log(f"Cookie {i}: OK ({s.user_id}) delay {delay}s")

    for ck in dead_cookies:
        mark_cookie_rc(ck, "init_fail")

    if not sessions:
        log("Không có cookie hợp lệ!")
        clean_ram(deep=True)
        return

    time.sleep(3)

    # ===== Nhập thread ids =====
    log("\nNhập id box (gõ 'done' để kết thúc):")
    thread_ids = []
    while True:
        tid = input("> ").strip()
        if tid.lower() == 'done':
            break
        if tid.isdigit() and tid not in thread_ids:
            thread_ids.append(tid)
        elif tid:
            log("ID không hợp lệ hoặc đã tồn tại!")

    if not thread_ids:
        log("Chưa chọn box nào!")
        for s, _ in sessions:
            s.close()
        sessions.clear()
        clean_ram(deep=True)
        return

    # ===== Nhập NHIỀU file ngôn =====
    log("\nNhập các file ngôn (gõ 'done' để kết thúc).")
    messages = []
    file_idx = 0
    while True:
        fname = input(f"> ").strip()
        if fname.lower() == 'done':
            break
        if not fname:
            continue
        try:
            with open(fname, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            if content:
                messages.append(content)
                file_idx += 1
            else:
                log(f"  ! File '{fname}' rỗng, bỏ qua")
        except Exception as e:
            log(f"  ! Lỗi đọc '{fname}': {e}")

    if not messages:
        log("Không có nội dung tin nhắn nào!")
        for s, _ in sessions:
            s.close()
        sessions.clear()
        thread_ids.clear()
        clean_ram(deep=True)
        return

    lock = threading.Lock()

    # Gắn callback kiểm tra rc vào từng client
    for s, _ in sessions:
        def make_on_disconnect(session=s):
            def _on_disconnect(client, userdata, rc):
                if rc != 0:
                    with lock:
                        if session.alive:
                            log(f"[!] Cookie {session.user_id} mất kết nối "
                                f"(rc={rc}) → dừng.")
                            session.alive = False
                            mark_cookie_rc(session.cookie, rc)
                    try:
                        gc.collect(0)
                    except Exception:
                        pass
            return _on_disconnect
        try:
            s.mqtt_client.on_disconnect = make_on_disconnect()
        except Exception:
            pass

    # ===== Bật monitor RAM =====
    ram_stop, _ram_thread = start_ram_monitor(interval=30, threshold_mb=400)

    # ===== Khởi chạy thread =====
    threads = []
    for i, (s, delay) in enumerate(sessions):
        t = threading.Thread(
            target=worker,
            args=(s, i, thread_ids, messages, delay, lock),
            daemon=True,
        )
        t.start()
        threads.append(t)

    try:
        while True:
            time.sleep(1)
            if not any(s.alive for s, _ in sessions):
                log("Tất cả cookie đã die, thoát.")
                break
    except KeyboardInterrupt:
        log("\nĐã dừng!")
    finally:
        # Dừng monitor
        ram_stop["stop"] = True

        # Đóng tất cả session
        for s, _ in sessions:
            try:
                s.close()
            except Exception:
                pass

        sessions.clear()
        messages.clear()
        thread_ids.clear()
        cookie_entries.clear()
        threads.clear()

        # Dọn RAM sâu cuối cùng
        clean_ram(deep=True)
        log(f"[RAM] Sau khi dọn: {get_ram_mb():.1f}MB")


if __name__ == "__main__":
    main()