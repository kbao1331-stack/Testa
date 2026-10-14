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
from urllib.parse import urlparse
import warnings

warnings.filterwarnings("ignore")

BANNER = ("""
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣼⣿⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⣴⠚⡄⢫⠉⢩⠃⠀⣰⣿⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣤⡄⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠠⡞⠳⡜⠦⠚⠘⠒⠋⠀⢰⣿⣿⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣰⣿⣿⡇⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠈⠚⠁⠀⠀⠀⠀⠀⢠⣿⣿⣿⣿⣧⠀⠀⠀⠀⠀⠀⠀⠀⢠⣾⣿⣿⣿⠁⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣼⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⣰⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢰⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⢀⣾⣿⣿⣿⣿⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣿⣿⣿⣿⣿⣿⣿⣤⣄⣀⡀⣠⣿⣿⣿⣿⣿⣿⣿⠇⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⢀⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⢸⠉⠉⢰⠂
⠀⠀⠀⠀⠀⠀⠀⠀⣾⣿⣿⠟⠛⠙⠻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡏⠀⠀⠀⠀⡇⠀⡰⠃⠀
⠀⠀⠀⠀⠀⠀⠀⢰⣿⣿⠃⠀⠀⢰⡆⢻⣿⣿⣿⣿⣿⡿⠛⠛⠻⣿⣿⣿⣿⠀⠀⠀⠀⢰⠁⡰⠁⠀⠀
⠀⠀⠀⠀⣶⣦⣤⠘⣿⣿⣆⠀⠀⢿⠇⣼⣿⣿⣿⣿⠛⢸⡇⠀⠀⠙⣿⣿⣿⣇⠀⠀⠀⠈⠒⠁⠀⠀⠀
⠀⠀⠀⠀⢀⣀⣁⠀⠻⣿⣿⣷⣦⣤⣶⣿⣿⣿⣿⣇⡀⣾⠃⠀⠀⢠⣿⣿⣿⡇⠀⡔⠒⠲⡄⠀⠀⠀⠀
⠀⠀⠀⠘⠛⠋⠉⠀⠀⠈⠻⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣶⣤⣤⣴⣾⣿⣿⠟⠀⠀⠱⠤⣀⠇⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠛⠻⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠟⠁⢀⣤⣀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠉⠉⠉⠉⠉⠀⠀⣀⡀⠀⠉⠙⠓⠀⠀⠀⠀⠀⠀⠀
⠀⡗⡤⡲⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢻⠆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⣴⣫⢸⢷⣤⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠈⠞⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
""")

UA = [
    "Mozilla/5.0 (Linux; Android 11; RMX2185) AppleWebKit/537.36 Chrome/121.0.6167.140 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; Redmi Note 11) AppleWebKit/537.36 Chrome/120.0.6099.129 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Pixel 6a) AppleWebKit/537.36 Chrome/122.0.6261.68 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; Redmi Note 8) AppleWebKit/537.36 Version/4.0 Chrome/108.0.0.0 Mobile Safari/537.36 Via/4.8.2",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
]


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
    except:
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
    except:
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
    if rc != 0:
        try:
            time.sleep(5)
            client.reconnect()
        except:
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
    except:
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
        try:
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
        except:
            pass


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def worker(session, index, thread_ids, message_text, delay, counts, lock):
    while True:
        for tid in thread_ids:
            try:
                session.NBKH(tid, message_text)
                with lock:
                    counts[index][tid] += 1
                    for i in range(len(counts)):
                        for t in thread_ids:
                            print(f" Cookie {i+1} đã gửi tin nhắn đến {t}")
            except Exception as e:
                with lock:
                    print(f" Lỗi cookie {index+1} tới box {tid}: {e}")
            time.sleep(delay)


def main():
    clear()
    print(BANNER)
    print("=" * 45)
    print("\n FB MQTT FRV ANH EM ROYALS EMPIREㅤ𔒝")
    print(" WELCOME TO USER OURS TOOL ✮˚.⋆\n")
    print("=" * 45)

    cookie_file = input("Nhập file cookies: ").strip()
    try:
        with open(cookie_file, 'r', encoding='utf-8') as f:
            cookies = [l.strip() for l in f if l.strip()]
    except Exception as e:
        print(f"Lỗi đọc file: {e}")
        return

    if not cookies:
        print("File cookie trống!")
        return

    print(f"Đang kết nối {len(cookies)} cookie...")
    sessions = []
    for i, cookie in enumerate(cookies, 1):
        s = NguyenBaoKhanhHuy(cookie)
        ok, msg = s.init()
        if not ok:
            print(f"Cookie {i}: {msg}")
            continue
        sessions.append(s)
        print(f"Cookie {i}: OK ({s.user_id})")

    if not sessions:
        print("Không có cookie hợp lệ!")
        return

    time.sleep(3)

    print("Nhập id box (done):")
    thread_ids = []
    while True:
        tid = input("> ").strip()
        if tid.lower() == 'done':
            break
        if tid.isdigit() and tid not in thread_ids:
            thread_ids.append(tid)
            pass
        elif tid:
            print("ID không hợp lệ hoặc đã tồn tại!")

    if not thread_ids:
        print("Chưa chọn box nào!")
        for s in sessions:
            s.close()
        return

    msg_file = input("Nhập file tin nhắn: ").strip()
    try:
        with open(msg_file, 'r', encoding='utf-8') as f:
            message_text = f.read().strip()
    except Exception as e:
        print(f"Lỗi đọc file: {e}")
        for s in sessions:
            s.close()
        return

    if not message_text:
        print("File tin nhắn trống!")
        for s in sessions:
            s.close()
        return

    try:
        delay = float(input("Nhập delay\n: ").strip())
        if delay < 1:
            delay = 1
    except:
        delay = 1

    counts = {i: {tid: 0 for tid in thread_ids} for i in range(len(sessions))}
    lock = threading.Lock()

    threads = []
    for i, s in enumerate(sessions):
        t = threading.Thread(target=worker, args=(s, i, thread_ids, message_text, delay, counts, lock), daemon=True)
        t.start()
        threads.append(t)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nĐã dừng!")
    finally:
        for s in sessions:
            s.close()


if __name__ == "__main__":
    main()