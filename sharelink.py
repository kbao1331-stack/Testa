import time
import threading
import os
import json
import random
import re
import requests
import string
from urllib.parse import urlparse
import ssl
from typing import Optional, Callable, List
import paho.mqtt.client as mqtt
from concurrent.futures import ThreadPoolExecutor, as_completed
import gc  # Thêm import gc

clr = lambda: os.system("cls" if os.name == "nt" else "clear")

# ============================================================================
# HÀM TIỆN ÍCH CẦN THIẾT
# ============================================================================

def parse_cookie_string(cookie_string):
    """Parse cookie string into dictionary"""
    cookie_dict = {}
    for cookie in cookie_string.split(";"):
        if "=" in cookie:
            key, value = cookie.split("=", 1)
            cookie_dict[key.strip()] = value.strip()
    return cookie_dict


def json_minimal(data):
    """Get JSON data in minimal form"""
    return json.dumps(data, separators=(",", ":"))


def generate_offline_threading_id() -> str:
    """Generate offline threading ID"""
    ret = int(time.time() * 1000)
    value = random.randint(0, 4294967295)
    binary_str = format(value, "022b")[-22:]
    msgs = bin(ret)[2:] + binary_str
    return str(int(msgs, 2))


def generate_session_id():
    return random.randint(1, 2 ** 53)


def generate_client_id():
    def gen(length):
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))
    return gen(8) + '-' + gen(4) + '-' + gen(4) + '-' + gen(4) + '-' + gen(12)


def dataGetHome(cookies):
    """Lấy thông tin cần thiết từ Facebook"""
    dictValueSaved = {"cookieFacebook": cookies}
    
    try:
        c_user = re.search(r"c_user=(\d+)", cookies)
        dictValueSaved["FacebookID"] = c_user.group(1) if c_user else "0"
    except:
        dictValueSaved["FacebookID"] = "0"
    
    headers = {
        'Cookie': cookies,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
    }
    
    try:
        response = requests.get('https://www.facebook.com', headers=headers, timeout=10)
        text = response.text
        
        # Extract fb_dtsg
        fb_dtsg_match = re.search(r'"token":"(.*?)"', text) or re.search(r'name="fb_dtsg" value="(.*?)"', text)
        dictValueSaved["fb_dtsg"] = fb_dtsg_match.group(1) if fb_dtsg_match else ""
        
        # Extract jazoest
        jazoest_match = re.search(r'jazoest=(\d+)', text)
        dictValueSaved["jazoest"] = jazoest_match.group(1) if jazoest_match else ""
        
        # Extract client revision
        revision_match = re.search(r'client_revision":(\d+)', text)
        dictValueSaved["clientRevision"] = revision_match.group(1) if revision_match else "1015919737"
        
    except Exception as e:
        print(f"[!] Lỗi lấy dữ liệu: {e}")
        dictValueSaved.update({
            "fb_dtsg": "",
            "jazoest": "",
            "clientRevision": "1015919737"
        })
    
    return dictValueSaved


def load_cookies_from_file(file_path: str) -> List[str]:
    """Đọc cookies từ file, mỗi dòng 1 cookie"""
    cookies_list = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                cookie = line.strip()
                if cookie and not cookie.startswith('#'):  # Bỏ qua dòng trống và comment
                    cookies_list.append(cookie)
    except FileNotFoundError:
        print(f"[!] Không tìm thấy file: {file_path}")
        return []
    except Exception as e:
        print(f"[!] Lỗi đọc file: {e}")
        return []
    
    return cookies_list


def load_text_from_file(file_path: str) -> str:
    """Đọc text từ file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read().strip()
            return text
    except FileNotFoundError:
        print(f"[!] Không tìm thấy file text: {file_path}")
        return ""
    except Exception as e:
        print(f"[!] Lỗi đọc file text: {e}")
        return ""


# ============================================================================
# LỚP FACEBOOK MQTT SHARE LINK (TỐI ƯU)
# ============================================================================

class FacebookMQTTShareLink:
    """Facebook MQTT client for sharing link functionality"""
    
    def __init__(self, cookies: str, options: dict = None, account_index: int = 0):
        if options is None:
            options = {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
                "online": True,
            }
        
        self.cookies = cookies
        self.options = options
        self.dataFB = dataGetHome(cookies)
        self.user_id = parse_cookie_string(cookies).get("c_user", "0")
        self.account_index = account_index
        
        self.mqtt_client = None
        self.req_callbacks = {}
        self.req_id_counter = 0
        self.connected = False
        self.stop_flag = False
        self.send_count = 0
        
        # Thêm timer cho auto gc
        self.gc_timer = None
        self.start_gc_timer()

    def start_gc_timer(self):
        """Bắt đầu timer tự động thu gom rác mỗi 60 giây"""
        if self.gc_timer:
            self.gc_timer.cancel()
        
        self.gc_timer = threading.Timer(60.0, self._auto_gc)
        self.gc_timer.daemon = True
        self.gc_timer.start()
    
    def _auto_gc(self):
        """Tự động thu gom rác"""
        try:
            collected = gc.collect()
            memory_info = f"GC: {collected} objects collected"
            print(f"[GC] Account {self.account_index + 1}: {memory_info}")
        
            # Kiểm tra req_callbacks tồn tại trước khi dùng
            if hasattr(self, 'req_callbacks') and len(self.req_callbacks) > 100:
                old_callbacks = len(self.req_callbacks)
                keys_to_remove = list(self.req_callbacks.keys())[:-50]
                for key in keys_to_remove:
                    if key in self.req_callbacks:
                        del self.req_callbacks[key]
                print(f"[GC] Account {self.account_index + 1}: Cleaned {len(keys_to_remove)} old callbacks")
        except Exception as e:
            print(f"[GC] Account {self.account_index + 1}: Error - {e}")
        finally:
            if not self.stop_flag:
                self.start_gc_timer()

    def connect(self):
        """Connect to Facebook MQTT server"""
        session_id = generate_session_id()
        client_id = generate_client_id()
        
        user_config = {
            "a": self.options["user_agent"],
            "u": self.user_id,
            "s": session_id,
            "chat_on": self.options["online"],
            "fg": False,
            "d": client_id,
            "ct": "websocket",
            "aid": "219994525426954",
            "mqtt_sid": "",
            "cp": 3,
            "ecp": 10,
            "st": [],
            "pm": [],
            "dc": "",
            "no_auto_fg": True,
            "gas": None,
            "pack": [],
        }
        
        host = f"wss://edge-chat.facebook.com/chat?sid={session_id}&cid={client_id}"
        cookie_str = "; ".join([f"{k}={v}" for k, v in parse_cookie_string(self.cookies).items()])
        
        mqtt_options = {
            "client_id": "mqttwsclient",
            "username": json_minimal(user_config),
            "clean": True,
            "ws_options": {
                "headers": {
                    "Cookie": cookie_str,
                    "Origin": "https://www.facebook.com",
                    "User-Agent": self.options["user_agent"],
                    "Referer": "https://www.facebook.com/",
                    "Host": "edge-chat.facebook.com",
                },
            },
            "keepalive": 10,
        }
        
        self.mqtt_client = mqtt.Client(
            client_id=mqtt_options["client_id"],
            clean_session=mqtt_options["clean"],
            protocol=mqtt.MQTTv31,
            transport="websockets",
        )
        
        self.mqtt_client.tls_set(
            certfile=None,
            keyfile=None,
            cert_reqs=ssl.CERT_NONE,
            tls_version=ssl.PROTOCOL_TLSv1_2
        )
        self.mqtt_client.tls_insecure_set(True)
        
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        self.mqtt_client.on_disconnect = self._on_disconnect
        self.mqtt_client.username_pw_set(username=mqtt_options["username"])
        
        parsed_host = urlparse(host)
        self.mqtt_client.ws_set_options(
            path=f"{parsed_host.path}?{parsed_host.query}",
            headers=mqtt_options["ws_options"]["headers"],
        )
        
        self.mqtt_client.connect(
            host=mqtt_options["ws_options"]["headers"]["Host"],
            port=443,
            keepalive=mqtt_options["keepalive"],
        )
        
        self.mqtt_client.loop_start()
        
        # Wait for connection
        timeout = 10
        start_time = time.time()
        while not self.connected and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        
        if not self.connected:
            raise Exception(f"Account {self.account_index + 1}: Failed to connect to MQTT server")
        
        print(f"✓ Account {self.account_index + 1} (ID: {self.user_id}) connected")

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            client.subscribe("/ls_resp", qos=1)
            client.publish(
                topic="/ls_app_settings",
                payload=json_minimal({
                    "ls_fdid": "",
                    "ls_sv": "6928813347213944"
                }),
                qos=1,
                retain=False,
            )
        else:
            print(f"[!] Account {self.account_index + 1}: MQTT Connection failed: {rc}")

    def _on_message(self, client, userdata, msg):
        if msg.topic == "/ls_resp":
            try:
                parsed = json.loads(msg.payload.decode("utf-8"))
                req_id = parsed.get("request_id")
                if req_id and req_id in self.req_callbacks:
                    callback = self.req_callbacks.pop(req_id)
                    if "payload" in parsed:
                        response = json.loads(parsed["payload"])
                        if "error" in response:
                            callback(None, response["error"].get("description", "Unknown error"))
                        else:
                            callback({"success": True}, None)
                    else:
                        callback({"success": True}, None)
            except:
                pass

    def _on_disconnect(self, client, userdata, rc):
        self.connected = False

    def share_link(self, url: str, thread_id: str, text: str = "", callback: Optional[Callable] = None):
        """Share link to thread"""
        if not self.connected:
            return False
        
        self.req_id_counter += 1
        request_id = self.req_id_counter
        otid = generate_offline_threading_id()
        
        task_payload = {
            "otid": otid,
            "source": 524289,
            "sync_group": 1,
            "send_type": 6,
            "mark_thread_read": 0,
            "url": url,
            "text": text or "",
            "thread_id": thread_id,
            "initiating_source": 0
        }
        
        task = {
            "label": 46,
            "payload": json_minimal(task_payload),
            "queue_name": thread_id,
            "task_id": random.randint(0, 1000),
            "failure_count": None,
        }
        
        main_payload = {
            "tasks": [task],
            "epoch_id": generate_offline_threading_id(),
            "version_id": "7545284305482586",
        }
        
        message = {
            "app_id": "2220391788200892",
            "payload": json_minimal(main_payload),
            "request_id": request_id,
            "type": 3
        }
        
        if callback:
            self.req_callbacks[request_id] = callback
        
        try:
            result = self.mqtt_client.publish(
                topic="/ls_req",
                payload=json_minimal(message),
                qos=1,
                retain=False,
            )
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except:
            return False

    def disconnect(self):
        """Ngắt kết nối và dọn dẹp"""
        self.stop_flag = True
        
        # Hủy timer GC
        if self.gc_timer:
            self.gc_timer.cancel()
            self.gc_timer = None
        
        # Ngắt kết nối MQTT
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            self.connected = False
        
        # Dọn dẹp callbacks
        self.req_callbacks.clear()
        
        # Thu gom rác
        gc.collect()


# ============================================================================
# LỚP QUẢN LÝ ĐA COOKIE
# ============================================================================

class MultiAccountManager:
    """Quản lý nhiều tài khoản Facebook"""
    
    def __init__(self, cookies_list: List[str]):
        self.cookies_list = cookies_list
        self.accounts = []
        self.stop_flag = False
        self.total_sent = 0
        self.lock = threading.Lock()
        
        # Thêm timer cho GC toàn cục
        self.global_gc_timer = None
        self.start_global_gc()
        
        for idx, cookie in enumerate(cookies_list):
            self.accounts.append({
                'cookie': cookie,
                'client': None,
                'index': idx,
                'connected': False,
                'sent_count': 0
            })
    
    def start_global_gc(self):
        """Bắt đầu timer GC toàn cục"""
        if self.global_gc_timer:
            self.global_gc_timer.cancel()
        
        self.global_gc_timer = threading.Timer(60.0, self._global_gc)
        self.global_gc_timer.daemon = True
        self.global_gc_timer.start()
    
    def _global_gc(self):
        """GC toàn cục"""
        try:
            collected = gc.collect()
            print(f"[GC Global] Collected {collected} objects")
            
            # Force garbage collection cho từng client
            for account in self.accounts:
                if account.get('client'):
                    # Dọn dẹp req_callbacks nếu quá lớn
                    if len(account['client'].req_callbacks) > 100:
                        old_count = len(account['client'].req_callbacks)
                        keys_to_remove = list(account['client'].req_callbacks.keys())[:-50]
                        for key in keys_to_remove:
                            if key in account['client'].req_callbacks:
                                del account['client'].req_callbacks[key]
                        print(f"[GC] Account {account['index'] + 1}: Cleaned {len(keys_to_remove)} callbacks")
            
        except Exception as e:
            print(f"[GC Global] Error: {e}")
        finally:
            if not self.stop_flag:
                self.start_global_gc()
    
    def connect_all(self):
        """Kết nối tất cả tài khoản"""
        print(f"\n[+] Đang kết nối {len(self.accounts)} tài khoản...")
        
        for account in self.accounts:
            try:
                client = FacebookMQTTShareLink(
                    cookies=account['cookie'],
                    account_index=account['index']
                )
                client.connect()
                account['client'] = client
                account['connected'] = True
            except Exception as e:
                print(f"[!] Account {account['index'] + 1}: {e}")
        
        connected_count = sum(1 for acc in self.accounts if acc['connected'])
        print(f"\n[+] Kết nối thành công: {connected_count}/{len(self.accounts)} tài khoản")
        return connected_count
    
    def send_with_account(self, account: dict, url: str, thread_id: str, text: str = "", delay: float = 1.0):
        """Gửi link với một tài khoản"""
        client = account['client']
        if not client or not client.connected:
            print(f"[!] Account {account['index'] + 1}: Chưa kết nối")
            return
        
        while not self.stop_flag:
            try:
                def callback(result, error):
                    if error:
                        print(f"[!] Account {account['index'] + 1}: Lỗi - {error}")
                    else:
                        with self.lock:
                            self.total_sent += 1
                            account['sent_count'] += 1
                            print(f"[✓] Account {account['index'] + 1}: Gửi lần {account['sent_count']}")
                
                success = client.share_link(url, thread_id, text, callback)
                if not success:
                    print(f"[!] Account {account['index'] + 1}: Gửi thất bại, thử lại...")
                
                time.sleep(delay)
            except Exception as e:
                print(f"[!] Account {account['index'] + 1}: Lỗi - {e}")
                time.sleep(1)
    
    def start_sending(self, url: str, thread_id: str, text: str = "", delay: float = 1.0, threads_per_account: int = 1):
        """Bắt đầu gửi với tất cả tài khoản"""
        if not any(acc['connected'] for acc in self.accounts):
            print("[!] Không có tài khoản nào kết nối!")
            return
        
        print("\n[+] Bắt đầu gửi... (Nhấn Enter để dừng)")
        print("-" * 50)
        
        # Tạo thread cho mỗi tài khoản
        send_threads = []
        for account in self.accounts:
            if account['connected']:
                # Mỗi tài khoản có thể chạy nhiều thread
                for _ in range(threads_per_account):
                    thread = threading.Thread(
                        target=self.send_with_account,
                        args=(account, url, thread_id, text, delay),
                        daemon=True
                    )
                    send_threads.append(thread)
                    thread.start()
        
        # Keyboard listener
        input()
        self.stop_flag = True
        
        # Đợi các thread kết thúc
        for thread in send_threads:
            thread.join(timeout=1)
        
        print(f"\n[✓] Đã dừng. Tổng số lần gửi: {self.total_sent}")
        
        # Hiển thị thống kê từng tài khoản
        print("\n[+] Thống kê từng tài khoản:")
        for account in self.accounts:
            status = "✓" if account['connected'] else "✗"
            print(f"  Account {account['index'] + 1}: {status} - Đã gửi: {account['sent_count']}")
    
    def disconnect_all(self):
        """Ngắt kết nối tất cả tài khoản"""
        self.stop_flag = True
        
        # Hủy timer GC toàn cục
        if self.global_gc_timer:
            self.global_gc_timer.cancel()
            self.global_gc_timer = None
        
        # Ngắt kết nối từng account
        for account in self.accounts:
            if account['client']:
                try:
                    account['client'].disconnect()
                except:
                    pass
        
        # GC cuối cùng
        gc.collect()


# ============================================================================
# PHẦN GIAO DIỆN & ĐIỀU KHIỂN
# ============================================================================

def main():
    clr()
	
    print("\n" + "="*50)
    print("  FACEBOOK MQTT SHARE LINK")
    print("  Tool độc quyền by đức anh")
    print("="*50)
    
    try:
        # Nhập đường dẫn file cookies
        file_path = input("\n[?] File cookies : ").strip()
        if not file_path:
            print("[!] Đường dẫn file không được để trống!")
            return
        
        cookies_list = load_cookies_from_file(file_path)
        if not cookies_list:
            print("[!] Không tìm thấy cookie nào trong file!")
            return
        
        print(f"[+] Đã đọc được {len(cookies_list)} cookies")
        
        # Nhập các thông tin khác
        thread_id = input("[?] ID Box (Thread ID): ").strip()
        if not thread_id:
            print("[!] Thread ID không được để trống!")
            return
        
        url = input("[?] URL muốn gửi: ").strip()
        if not url:
            print("[!] URL không được để trống!")
            return
        
        # Nhập đường dẫn file text thay vì nhập text trực tiếp
        text_file = input("[?] File ngôn : ").strip()
        text = ""
        if text_file:
            text = load_text_from_file(text_file)
            if text:
                print(f"[+] Đã đọc text từ file: {len(text)} ký tự")
            else:
                print("[!] File text trống hoặc không đọc được, sẽ bỏ qua text")
        
        try:
            delay = float(input("[?] Delay : ").strip() or "1")
        except:
            delay = 1.0
        
        try:
            threads_per_account = int(input("[?] Số ngôn gửi 1 lần (đè): ").strip() or "1")
            if threads_per_account < 1:
                threads_per_account = 1
        except:
            threads_per_account = 1
        
        # Tạo manager và kết nối
        manager = MultiAccountManager(cookies_list)
        connected_count = manager.connect_all()
        
        if connected_count == 0:
            print("[!] Không có tài khoản nào kết nối được!")
            return
        
        # Bắt đầu gửi
        manager.start_sending(
            url=url,
            thread_id=thread_id,
            text=text,
            delay=delay,
            threads_per_account=threads_per_account
        )
        
        # Ngắt kết nối
        manager.disconnect_all()
        
    except KeyboardInterrupt:
        print("\n[!] Đã dừng chương trình.")
    except Exception as e:
        print(f"\n[!] Lỗi: {e}")


if __name__ == "__main__":
    main()