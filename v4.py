from __future__ import annotations

import gc
import hashlib
import json
import os
import random
import re
import ssl
import threading
import time
import warnings
from concurrent.futures import Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from threading import Event
from typing import Any
from urllib.parse import urlparse

import paho.mqtt.client as mqtt
import requests

warnings.filterwarnings("ignore")
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass


BANNER = ("""
 __     __    _     _   _  ___
 \ \   / /__ (_) __| | | |/ (_)_ __   __ _
  \ \ / / _ \| |/ _` | | ' /| | '_ \ / _` |
   \ V / (_) | | (_| | | . \| | | | | (_| |
    \_/ \___/|_|\__,_| |_|\_\_|_| |_|\__, |
                                     |___/
╭──────────────────────────────────────────╮
│     🪐  Void King Sender Mqtt Tool 💲      │
│   💻  Dev : Tr Duy An Frv Khanh Huy 💵     │
│         💸  Thank you so much 💸           │
╰──────────────────────────────────────────╯
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
acc_status: dict[str, str] = {}
acc_order:  list[str]      = []
stop_event  = threading.Event()


def clear() -> None:
    os.system('cls' if os.name == 'nt' else 'clear')


def redraw() -> None:
    if not redraw_flag.is_set():
        return
    redraw_flag.clear()
    clear()
    print(BANNER, end="")
    print(" ")
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


def gen_otid() -> str:
    return str(int(time.time() * 1000))


def gen_session_id() -> str:
    return str(int(time.time() * 1000))


def gen_client_id() -> str:
    return hashlib.md5(str(time.time()).encode()).hexdigest()[:16]


def jmin(obj) -> str:
    return json.dumps(obj, separators=(',', ':'))


@dataclass
class Account:
    cookies: str
    delay: float
    account_name: str = ""
    user_id: str = ""
    session: Any = field(default=None, repr=False)
    stop_event: Event = field(default_factory=Event)
    message_count: int = 0


class MqttV4:

    def __init__(self, cookies: str, account_name: str = "") -> None:
        self.cookies       = cookies
        self.account_name  = account_name
        self.user_id: str | None      = None
        self.mqtt_client: Any         = None
        self.last_seq_id: str | None  = None
        self.session_id: str | None   = None
        self.ws_req_number            = 0
        self.ws_task_number           = 0
        self.alive                    = False
        self._closed                  = False
        self.dead_since: float | None = None
        self._session_ref             = {'sess': self}

    def extract_user_id(self) -> str | None:
        try:
            return re.search(r"c_user=(\d+)", self.cookies).group(1)
        except Exception:
            return None

    def get_seq_id(self) -> str:
        try:
            headers = {'cookie': self.cookies, 'user-agent': random.choice(UA)}
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

    def on_connect(self, client, userdata, flags, rc) -> None:
        if rc == 0:
            self.alive = True
            client.subscribe([("/t_ms", 0)])
            queue = {
                "sync_api_version": 10,
                "max_deltas_able_to_process": 1000,
                "delta_batch_size": 500,
                "encoding": "JSON",
                "entity_fbid": self.user_id,
                "initial_titan_sequence_id": self.last_seq_id,
                "device_params": None,
            }
            client.publish("/messenger_sync_create_queue", jmin(queue),
                           qos=1, retain=False)
        else:
            self.mark_dead()

    def on_disconnect(self, client, userdata, rc) -> None:
        if rc == 0:
            self.mark_dead()
        else:
            self.alive = False
            self._closed = True

    def connect(self) -> bool:
        if not self.user_id:
            self.user_id = self.extract_user_id()
        if not self.user_id:
            return False

        self.last_seq_id = self.get_seq_id()
        self.session_id  = gen_session_id()

        user = {
            "u": self.user_id,
            "s": self.session_id,
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

        host = f"wss://edge-chat.messenger.com/chat?region=eag&sid={self.session_id}"
        ua   = random.choice(UA)

        client = mqtt.Client(
            client_id="mqttwsclient",
            clean_session=True,
            protocol=mqtt.MQTTv31,
            transport="websockets",
            userdata={
                'user_id': self.user_id,
                'last_seq_id': self.last_seq_id,
                'session_ref': self._session_ref,
            },
        )
        client.on_connect    = self.on_connect
        client.on_disconnect = self.on_disconnect
        client.tls_set_context(loc_ssl())
        client.username_pw_set(username=jmin(user))

        parsed = urlparse(host)
        client.ws_set_options(
            path=f"{parsed.path}?{parsed.query}",
            headers={
                "Cookie": self.cookies,
                "Origin": "https://www.messenger.com",
                "User-Agent": ua,
                "Referer": "https://www.messenger.com/",
                "Host": "edge-chat.messenger.com",
            },
        )

        try:
            client.connect("edge-chat.messenger.com", 443, keepalive=10)
            client.loop_start()
            self.mqtt_client = client
        except Exception:
            self.mqtt_client = None
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

    def send_message(self, text: str, thread_id: str) -> bool:
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

    def disconnect(self) -> None:
        self._close_client()
        self.alive = False

    def _close_client(self) -> None:
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

    def mark_dead(self) -> None:
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

    def mark_temp_lost(self) -> None:
        self.alive   = False
        self._closed = True
        self._close_client()

    def init(self) -> bool:
        return self.connect()

    def reinit(self) -> bool:
        self._close_client()
        self._closed     = False
        self.alive       = False
        self.dead_since  = None
        self.last_seq_id = None
        self.session_id  = None
        return self.connect()

    def close(self) -> None:
        if self._closed and self.mqtt_client is None:
            return
        self._close_client()
        self.alive = False


def session_worker(session: MqttV4,
                   thread_ids, msg_list, delay) -> None:
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
                    session.send_message(text, tid)
                except Exception:
                    pass

        if stop_event.wait(delay):
            return


def _safe_init(sess: MqttV4) -> None:
    try:
        sess.init()
    except Exception:
        try:
            sess.mark_temp_lost()
        except Exception:
            pass


def build_sessions(cookies) -> list[MqttV4]:
    raw: list[MqttV4] = []
    for c in cookies:
        s   = MqttV4(c)
        uid = s.extract_user_id()
        if not uid:
            continue
        s.user_id = uid
        raw.append(s)

    if not raw:
        return []

    with ThreadPoolExecutor(max_workers=len(raw),
                            thread_name_prefix="mqtt-init") as ex:
        futures = [ex.submit(_safe_init, s) for s in raw]
        try:
            wait(futures, timeout=CONNACK_WAIT + 10)
        except Exception:
            pass

    with state_lock:
        for s in raw:
            st = "LIVE" if s.alive else "DIE"
            acc_status[s.user_id] = st
            acc_order.append(s.user_id)

    redraw_flag.set()
    return raw


def cleanup_sessions(sessions,
                     executor: ThreadPoolExecutor | None = None) -> None:
    stop_event.set()
    for s in sessions:
        try:
            s.close()
        except Exception:
            pass
    if executor is not None:
        try:
            executor.shutdown(wait=True, cancel_futures=True)
        except Exception:
            pass
    with state_lock:
        acc_status.clear()
        acc_order.clear()
    gc.collect()


class MultiCookieManager:

    def __init__(self) -> None:
        self.accounts: list[Account]            = []
        self.sessions: list[MqttV4] = []
        self.message_stats: dict[str, int]      = {}
        self.executor: ThreadPoolExecutor | None = None
        self.futures:  list[Future]             = []

    def add_account(self, cookies: str, delay: float,
                    account_name: str = "") -> Account:
        session = MqttV4(cookies, account_name)
        uid     = session.extract_user_id() or ""
        account = Account(
            cookies=cookies,
            delay=delay,
            account_name=account_name,
            user_id=uid,
            session=session,
        )
        self.accounts.append(account)
        self.sessions.append(session)
        return account

    def worker_thread(self, account: Account,
                      thread_ids, message_content) -> None:
        if isinstance(message_content, str):
            msg_list = [message_content]
        else:
            msg_list = list(message_content)
        if isinstance(thread_ids, str):
            tids = [thread_ids]
        else:
            tids = list(thread_ids)
        session_worker(account.session, tids, msg_list, account.delay)

    def start_all(self, thread_ids,
                  message_content) -> list[Future]:
        if not self.accounts:
            return []
        if self.executor is None:
            self.executor = ThreadPoolExecutor(
                max_workers=max(1, len(self.accounts)),
                thread_name_prefix="mqtt-worker",
            )
        for account in self.accounts:
            f = self.executor.submit(
                session_worker,
                account.session, thread_ids, message_content, account.delay,
            )
            self.futures.append(f)
        return self.futures

    def stop_all(self) -> None:
        for account in self.accounts:
            account.stop_event.set()
        stop_event.set()
        for s in self.sessions:
            try:
                s.close()
            except Exception:
                pass
        if self.executor is not None:
            try:
                self.executor.shutdown(wait=True, cancel_futures=True)
            except Exception:
                pass
            self.executor = None
        self.futures.clear()

    def print_stats(self) -> None:
        redraw()


def read_message_from_file(file_path: str) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return ""


def print_header() -> None:
    clear()
    print(BANNER)


def get_multi_cookies() -> list[str]:
    cookie_file = input("[*] Nhap file cookies: ").strip()
    try:
        with open(cookie_file, 'r', encoding='utf-8') as f:
            return [l.strip() for l in f if l.strip()]
    except Exception:
        return []


def get_user_input() -> dict[str, Any]:
    print_header()

    print(" ")
    print("[*] Nhap id box (done):")
    thread_ids: list[str] = []
    while True:
        tid = input("> ").strip()
        if tid.lower() == 'done':
            break
        if tid.isdigit() and tid not in thread_ids:
            thread_ids.append(tid)

    print_header()

    print(" ")
    print("[*] Nhap file ngon (done):")
    msg_list: list[str] = []
    while True:
        path = input("> ").strip()
        if path.lower() == 'done':
            break
        txt = read_message_from_file(path)
        if txt:
            msg_list.append(txt)
        else:
            print("  [!] khong doc duoc file nhap lai")

    return {'thread_ids': thread_ids, 'messages': msg_list}


def run_once() -> None:
    stop_event.clear()
    redraw_flag.clear()
    with state_lock:
        acc_status.clear()
        acc_order.clear()

    print_header()

    cookies = get_multi_cookies()
    if not cookies:
        return

    print("[*] Dang khoi tao MQTT...")
    sessions = build_sessions(cookies)
    if not sessions:
        print("[!] khong co account hop le")
        return

    print_header()
    data = get_user_input()
    thread_ids = data['thread_ids']
    msg_list   = data['messages']

    if not thread_ids or not msg_list:
        cleanup_sessions(sessions, None)
        return

    print_header()

    print(" ")
    print("[*] Nhap delay cho tung cookie:")
    delay_map: dict[str, float] = {}
    for s in sessions:
        while True:
            try:
                d = float(input(f"-> Uid {s.user_id} delay: ").strip())
                if d < 0:
                    d = 0.0
                delay_map[s.user_id] = d
                break
            except Exception:
                print("  [!] nhap so thu lai")

    redraw_flag.set()
    redraw()

    executor = ThreadPoolExecutor(
        max_workers=max(1, len(sessions)),
        thread_name_prefix="mqtt-worker",
    )
    try:
        for s in sessions:
            d = delay_map.get(s.user_id, 1.0)
            executor.submit(session_worker, s, thread_ids, msg_list, d)

        while True:
            redraw()
            time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup_sessions(sessions, executor)


def main() -> None:
    run_once()


if __name__ == "__main__":
    main()