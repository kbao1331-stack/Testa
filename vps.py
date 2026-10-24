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
from urllib.parse import urlparse
import warnings

warnings.filterwarnings("ignore")
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass

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
⠀⠈⠞⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
╔═══════════════════════════════════════════╗
║ Tool Sender Facebook Mqtt Frv Void King 🪐 
╚═══════════════════════════════════════════╝
""")

UA = [
    "Mozilla/5.0 (Linux; Android 11; RMX2185) AppleWebKit/537.36 Chrome/121.0.6167.140 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; Redmi Note 11) AppleWebKit/537.36 Chrome/120.0.6099.129 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Pixel 6a) AppleWebKit/537.36 Chrome/122.0.6261.68 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; Redmi Note 8) AppleWebKit/537.36 Version/4.0 Chrome/108.0.0.0 Mobile Safari/537.36 Via/4.8.2",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
]

MAX_DEAD_TIME  = 24 * 3600
RETRY_INTERVAL = 60
CONNACK_WAIT   = 10.0

mqtt_lock   = threading.Lock()
redraw_flag = threading.Event()
state_lock  = threading.Lock()
acc_status  = {}
acc_order   = []
stop_event  = threading.Event()


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def redraw():
    if not redraw_flag.is_set():
        return
    redraw_flag.clear()
    clear()
    print(BANNER, end="")          # <-- thêm end="" ở đây
    with state_lock:
        for uid in acc_order:
            st = acc_status.get(uid, "?")
            print(f"[SENDING] UID:{uid} | {st}")


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
        headers = {'cookie': cookie, 'user-agent': random.choice(UA)}
        r = requests.get('https://www.facebook.com/', headers=headers,
                         timeout=30, verify=False)
        if r.status_code == 200:
            m = re.search(r'"sync_sequence_id":"?(\d+)"?', r.text)
            if m:
                return m.group(1)
            m = re.search(r'"lastSeqId":"?(\d+)"?', r.text)
            if m:
                return m.group(1)
    except Exception:
        pass
    return str(int(time.time() * 1000))


def gen_otid():
    return str(int(time.time() * 1000))


def gen_session_id():
    return str(int(time.time() * 1000))


def gen_client_id():
    return hashlib.md5(str(time.time()).encode()).hexdigest()[:16]


def jmin(obj):
    return json.dumps(obj, separators=(',', ':'))


def connect_mqtt(cookie, user_id, last_seq_id, session_id, session_ref):
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
    ua   = random.choice(UA)

    client = mqtt.Client(
        client_id="mqttwsclient",
        clean_session=True,
        protocol=mqtt.MQTTv31,
        transport="websockets",
        userdata={
            'user_id': user_id,
            'last_seq_id': last_seq_id,
            'session_ref': session_ref,
        },
    )

    def on_connect(c, u, flags, rc):
        sess = u['session_ref'].get('sess')
        if rc == 0:
            if sess:
                sess.alive = True
            c.subscribe([("/t_ms", 0)])
            queue = {
                "sync_api_version": 10,
                "max_deltas_able_to_process": 1000,
                "delta_batch_size": 500,
                "encoding": "JSON",
                "entity_fbid": u['user_id'],
                "initial_titan_sequence_id": u['last_seq_id'],
                "device_params": None,
            }
            c.publish("/messenger_sync_create_queue", jmin(queue),
                      qos=1, retain=False)
        else:
            if sess:
                sess.mark_dead()

    def on_disconnect(c, u, rc):
        sess = u['session_ref'].get('sess')
        if sess is None:
            return
        if rc == 0:
            sess.mark_dead()
        else:
            sess.alive = False
            sess._closed = True

    client.on_connect    = on_connect
    client.on_disconnect = on_disconnect
    client.tls_set_context(loc_ssl())
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


class MqttNBKHV3:
    def __init__(self, cookie):
        self.cookie          = cookie
        self.user_id         = None
        self.mqtt_client     = None
        self.last_seq_id     = None
        self.session_id      = None
        self.ws_req_number   = 0
        self.ws_task_number  = 0
        self.alive           = False
        self._closed         = False
        self.dead_since      = None
        self._session_ref    = {'sess': self}

    def _close_client(self):
        self._closed = True
        try:
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
        except Exception:
            pass
        try:
            if self.mqtt_client:
                self.mqtt_client.disconnect()
        except Exception:
            pass
        self.mqtt_client = None

    def mark_dead(self):
        with state_lock:
            if self._closed:
                return
            self._closed = True
            self.alive   = False
            if self.user_id:
                acc_status[self.user_id] = "DIE"
            if self.dead_since is None:
                self.dead_since = time.time()
        redraw_flag.set()
        self._close_client()

    def mark_temp_lost(self):
        self.alive   = False
        self._closed = True
        self._close_client()

    def init(self):
        if not self.user_id:
            self.user_id = extract_user_id(self.cookie)
        if not self.user_id:
            return False

        self.last_seq_id = get_last_seq_id(self.cookie)
        self.session_id  = gen_session_id()
        self.mqtt_client = connect_mqtt(
            self.cookie, self.user_id, self.last_seq_id,
            self.session_id, self._session_ref,
        )
        if not self.mqtt_client:
            self.mark_temp_lost()
            return False

        deadline = time.time() + CONNACK_WAIT
        while time.time() < deadline:
            if self.alive:
                return True
            if self._closed:
                return False
            time.sleep(0.1)

        self.mark_temp_lost()
        return False

    def reinit(self):
        self._close_client()
        self._closed     = False
        self.alive       = False
        self.dead_since  = None
        self.last_seq_id = None
        self.session_id  = None
        return self.init()

    def send_message(self, thread_id, text):
        if self._closed or not self.alive:
            return False

        self.ws_req_number  += 1
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

        try:
            with mqtt_lock:
                info = self.mqtt_client.publish(
                    "/ls_req", jmin(content), qos=1, retain=False
                )
            if info.rc != mqtt.MQTT_ERR_SUCCESS:
                self.mark_temp_lost()
                return False
        except Exception:
            self.mark_temp_lost()
            return False
        return True

    def close(self):
        if self._closed and self.mqtt_client is None:
            return
        self._close_client()
        self.alive = False


def session_worker(session, thread_ids, msg_list, delay):
    last_retry = 0.0

    while not stop_event.is_set():

        if session._closed or not session.alive:
            now = time.time()

            if session.dead_since is not None:
                if now - session.dead_since >= MAX_DEAD_TIME:
                    with state_lock:
                        if session.user_id in acc_order:
                            acc_order.remove(session.user_id)
                        acc_status.pop(session.user_id, None)
                    session.close()
                    redraw_flag.set()
                    return

            if now - last_retry >= RETRY_INTERVAL:
                last_retry = now
                prev_was_dead = session.dead_since is not None
                try:
                    ok = session.reinit()
                except Exception:
                    ok = False
                if ok and prev_was_dead:
                    with state_lock:
                        if session.user_id:
                            acc_status[session.user_id] = "LIVE"
                    redraw_flag.set()

            if stop_event.wait(2.0):
                return
            continue

        if not thread_ids or not msg_list:
            if stop_event.wait(1.0):
                return
            continue

        for text in msg_list:
            if stop_event.is_set() or session._closed or not session.alive:
                break
            if not text:
                continue
            for tid in thread_ids:
                if stop_event.is_set() or session._closed or not session.alive:
                    break
                try:
                    session.send_message(tid, text)
                except Exception:
                    pass

        if stop_event.wait(delay):
            return


def build_sessions(cookies):
    raw = []
    for c in cookies:
        uid = extract_user_id(c)
        if not uid:
            continue
        s = MqttNBKHV3(c)
        s.user_id = uid
        raw.append(s)

    if not raw:
        return []

    threads = []
    for s in raw:
        def _init(sess=s):
            try:
                sess.init()
            except Exception:
                try:
                    sess.mark_temp_lost()
                except Exception:
                    pass
        t = threading.Thread(target=_init, daemon=True)
        t.start()
        threads.append(t)

    for t in threads:
        try:
            t.join(timeout=CONNACK_WAIT + 5)
        except Exception:
            pass

    with state_lock:
        for s in raw:
            st = "LIVE" if s.alive else "DIE"
            acc_status[s.user_id] = st
            acc_order.append(s.user_id)

    redraw_flag.set()
    return raw


def cleanup_sessions(sessions, threads):
    stop_event.set()
    for s in sessions:
        try:
            s.close()
        except Exception:
            pass
    for t in threads:
        try:
            t.join(timeout=3)
        except Exception:
            pass
    with state_lock:
        acc_status.clear()
        acc_order.clear()
    gc.collect()


def run_once():
    redraw_flag.clear()
    with state_lock:
        acc_status.clear()
        acc_order.clear()

    clear()
    print(BANNER)

    cookie_file = input("nhap file cookies: ").strip()
    try:
        with open(cookie_file, 'r', encoding='utf-8') as f:
            cookies = [l.strip() for l in f if l.strip()]
    except Exception:
        return
    if not cookies:
        return

    print("[*] dang khoi tao MQTT...")
    sessions = build_sessions(cookies)
    if not sessions:
        print("[!] khong co account hop le")
        return

    clear()
    print(BANNER)

    print("\nnhap id box (done):")
    thread_ids = []
    while True:
        tid = input("> ").strip()
        if tid.lower() == 'done':
            break
        if tid.isdigit() and tid not in thread_ids:
            thread_ids.append(tid)

    if not thread_ids:
        cleanup_sessions(sessions, [])
        return

    clear()
    print(BANNER)
    print("\nnhap file ngon (done):")
    msg_list = []
    while True:
        path = input(f"> ").strip()
        if path.lower() == 'done':
            break
        try:
            with open(path, 'r', encoding='utf-8') as f:
                txt = f.read().strip()
            if txt:
                msg_list.append(txt)
            else:
                print("  [!] file rong nhap lai")
        except Exception:
            print("  [!] khong doc duoc file nhap lai")

    if not msg_list:
        cleanup_sessions(sessions, [])
        return

    clear()
    print(BANNER)
    print("\nnhap delay cho tung cookie:")
    delay_map = {}
    for s in sessions:
        while True:
            try:
                d = float(input(f"UID {s.user_id} -> delay: ").strip())
                if d < 0:
                    d = 0
                delay_map[s.user_id] = d
                break
            except Exception:
                print("  [!] nhap so thu lai")

    redraw_flag.set()
    redraw()

    threads = []
    for s in sessions:
        d = delay_map.get(s.user_id, 1.0)
        t = threading.Thread(
            target=session_worker,
            args=(s, thread_ids, msg_list, d),
            daemon=True,
        )
        t.start()
        threads.append(t)

    try:
        while True:
            redraw()
            time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup_sessions(sessions, threads)


def main():
    run_once()


if __name__ == "__main__":
    main()