import paho.mqtt.client as mqtt
import httpx
import requests
import time
import json
import ssl
import hashlib
import os
import sys
import random
import string
import uuid
import base64
import io
import struct
import gc
import re
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional
import warnings
from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes

RESET = "\033[0m"

STOPS = [
    (100, 180, 230),
    (130, 200, 240),
    (160, 215, 245),
    (190, 230, 250),
    (210, 240, 255),
    (230, 248, 255),
    (210, 240, 255),
    (190, 230, 250),
    (160, 215, 245),
    (130, 200, 240),
    (100, 180, 230),
]

def _mix(c1, c2, t):
    return tuple(round(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

def _gradient_color(pos):
    n = len(STOPS) - 1
    pos = pos % 1.0
    seg = pos * n
    i = int(seg)
    t = seg - i
    if i >= n:
        i, t = n - 1, 1.0
    return _mix(STOPS[i], STOPS[i + 1], t)

def _render_frame(text, phase, spread):
    length = len(text)
    out = []
    for idx, ch in enumerate(text):
        if ch == " ":
            out.append(" ")
            continue
        pos = phase + (idx / max(length, 1)) * spread
        r, g, b = _gradient_color(pos)
        out.append(f"\033[38;2;{r};{g};{b}m{ch}")
    return "".join(out) + RESET

_state = {"frame": 0}

def cprint(text, step=0.08, spread=0.7, end="\n"):
    if len(text) == 0:
        print(end=end)
        return
    phase = (_state["frame"] * step) % 1.0
    colored_text = _render_frame(text, phase, spread)
    print(colored_text, end=end)
    _state["frame"] += 1

def cinput(prompt="", step=0.08, spread=0.7):
    if len(prompt) > 0:
        phase = (_state["frame"] * step) % 1.0
        colored_prompt = _render_frame(prompt, phase, spread)
        _state["frame"] += 1
        return input(colored_prompt)
    else:
        return input()

warnings.filterwarnings("ignore")

def auto_gc(interval=60):
    def run_gc():
        gc.collect()
        threading.Timer(interval, run_gc).start()
    run_gc()

class FacebookPasswordEncryptor:
    @staticmethod
    def get_public_key():
        try:
            url = 'https://b-graph.facebook.com/pwd_key_fetch'
            params = {
                'version': '2',
                'flow': 'CONTROLLER_INITIALIZATION',
                'method': 'GET',
                'fb_api_req_friendly_name': 'pwdKeyFetch',
                'fb_api_caller_class': 'com.facebook.auth.login.AuthOperations',
                'access_token': '438142079694454|fc0a7caa49b192f64f6f5a6d9643bb28'
            }
            response = requests.post(url, params=params, timeout=5).json()
            return response.get('public_key'), str(response.get('key_id', '25'))
        except Exception as e:
            raise Exception(f"Khong the lay public key: {e}")

    @staticmethod
    def encrypt(password, public_key=None, key_id="25"):
        if public_key is None:
            public_key, key_id = FacebookPasswordEncryptor.get_public_key()
        try:
            rand_key = get_random_bytes(32)
            iv = get_random_bytes(12)
            pubkey = RSA.import_key(public_key)
            cipher_rsa = PKCS1_v1_5.new(pubkey)
            encrypted_rand_key = cipher_rsa.encrypt(rand_key)
            cipher_aes = AES.new(rand_key, AES.MODE_GCM, nonce=iv)
            current_time = int(time.time())
            cipher_aes.update(str(current_time).encode("utf-8"))
            encrypted_passwd, auth_tag = cipher_aes.encrypt_and_digest(password.encode("utf-8"))
            buf = io.BytesIO()
            buf.write(bytes([1, int(key_id)]))
            buf.write(iv)
            buf.write(struct.pack("<h", len(encrypted_rand_key)))
            buf.write(encrypted_rand_key)
            buf.write(auth_tag)
            buf.write(encrypted_passwd)
            encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
            return f"#PWD_FB4A:2:{current_time}:{encoded}"
        except Exception as e:
            raise Exception(f"Loi khi ma hoa mat khau: {e}")

class FacebookLogin:
    API_URL = "https://b-graph.facebook.com/auth/login"
    ACCESS_TOKEN = "350685531728|62f8ce9f74b12f84c123cc23437a4a32"
    API_KEY = "882a8490361da98702bf97a021ddc14d"
    SIG = "214049b9f17c38bd767de53752b53946"
    
    BASE_HEADERS = {
        "content-type": "application/x-www-form-urlencoded",
        "x-fb-net-hni": "45201",
        "zero-rated": "0",
        "x-fb-sim-hni": "45201",
        "x-fb-connection-quality": "EXCELLENT",
        "x-fb-friendly-name": "authenticate",
        "x-fb-connection-bandwidth": "78032897",
        "x-tigon-is-retry": "False",
        "authorization": "OAuth null",
        "x-fb-connection-type": "WIFI",
        "x-fb-device-group": "3342",
        "priority": "u=3,i",
        "x-fb-http-engine": "Liger",
        "x-fb-client-ip": "True",
        "x-fb-server-cluster": "True"
    }
    
    def __init__(self, uid_phone_mail, password, twwwoo2fa=""):
        self.uid_phone_mail = uid_phone_mail
        self.twwwoo2fa = twwwoo2fa.replace(" ", "") if twwwoo2fa else ""
        if password.startswith("#PWD_FB4A"):
            self.password = password
        else:
            self.password = FacebookPasswordEncryptor.encrypt(password)
        self.session = requests.Session()
        self.device_id = str(uuid.uuid4())
        self.adid = str(uuid.uuid4())
        self.secure_family_device_id = str(uuid.uuid4())
        self.machine_id = ''.join(random.choices(string.ascii_letters + string.digits, k=24))
        self.jazoest = ''.join(random.choices(string.digits, k=5))
        self.sim_serial = ''.join(random.choices(string.digits, k=20))
        self.headers = self._build_headers()
        self.data = self._build_data()
    
    def _build_headers(self):
        headers = self.BASE_HEADERS.copy()
        headers.update({
            "x-fb-request-analytics-tags": '{"network_tags":{"product":"350685531728","retry_attempt":"0"},"application_tags":"unknown"}',
            "user-agent": "Dalvik/2.1.0 (Linux; U; Android 9; 23113RKC6C Build/PQ3A.190705.08211809) [FBAN/FB4A;FBAV/417.0.0.33.65;FBPN/com.facebook.katana;FBLC/vi_VN;FBBV/480086274;FBCR/MobiFone;FBMF/Redmi;FBBD/Redmi;FBDV/23113RKC6C;FBSV/9;FBCA/x86:armeabi-v7a;FBDM/{density=1.5,width=1280,height=720};FB_FW/1;FBRV/0;]"
        })
        return headers
    
    def _build_data(self):
        return {
            "format": "json",
            "email": self.uid_phone_mail,
            "password": self.password,
            "credentials_type": "password",
            "generate_session_cookies": "1",
            "locale": "vi_VN",
            "client_country_code": "VN",
            "api_key": self.API_KEY,
            "access_token": self.ACCESS_TOKEN,
            "adid": self.adid,
            "device_id": self.device_id,
            "generate_analytics_claim": "1",
            "community_id": "",
            "linked_guest_account_userid": "",
            "cpl": "true",
            "try_num": "1",
            "family_device_id": self.device_id,
            "secure_family_device_id": self.secure_family_device_id,
            "sim_serials": f'["{self.sim_serial}"]',
            "openid_flow": "android_login",
            "openid_provider": "google",
            "openid_tokens": "[]",
            "account_switcher_uids": f'["{self.uid_phone_mail}"]',
            "fb4a_shared_phone_cpl_experiment": "fb4a_shared_phone_nonce_cpl_at_risk_v3",
            "fb4a_shared_phone_cpl_group": "enable_v3_at_risk",
            "enroll_misauth": "false",
            "error_detail_type": "button_with_disabled",
            "source": "login",
            "machine_id": self.machine_id,
            "jazoest": self.jazoest,
            "meta_inf_fbmeta": "V2_UNTAGGED",
            "advertiser_id": self.adid,
            "encrypted_msisdn": "",
            "currently_logged_in_userid": "0",
            "fb_api_req_friendly_name": "authenticate",
            "fb_api_caller_class": "Fb4aAuthHandler",
            "sig": self.SIG
        }
    
    def login(self):
        try:
            response = self.session.post(self.API_URL, headers=self.headers, data=self.data, timeout=5)
            response_json = response.json()
            if 'access_token' in response_json:
                cookies_dict = {}
                cookies_string = ""
                if 'session_cookies' in response_json:
                    for cookie in response_json['session_cookies']:
                        cookies_dict[cookie['name']] = cookie['value']
                        cookies_string += f"{cookie['name']}={cookie['value']}; "
                return {
                    'success': True,
                    'cookies_dict': cookies_dict,
                    'cookies_string': cookies_string.rstrip('; '),
                    'uid': cookies_dict.get('c_user', '')
                }
            if 'error' in response_json:
                return {'success': False, 'error': response_json['error'].get('message', 'Unknown error')}
            return {'success': False, 'error': 'Khong xac dinh duoc response'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

def create_ssl_context():
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    context.options |= ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_3
    context.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20:ECDHE+AES:RSA+AESGCM:RSA+AES:!aNULL:!eNULL:!MD5:!DSS")
    return context

def extract_user_id(cookie):
    try:
        match = re.search(r"c_user=(\d+)", cookie)
        return match.group(1) if match else None
    except:
        return None

def extract_fb_dtsg(cookie):
    try:
        ssl_context = create_ssl_context()
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.9,vi;q=0.8',
            'cookie': cookie,
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        }
        with httpx.Client(verify=ssl_context, timeout=10.0, http2=True, follow_redirects=True) as client:
            endpoints = ['https://www.facebook.com/', 'https://mbasic.facebook.com/', 'https://m.facebook.com/']
            patterns = [
                r'"DTSGInitialData",\[\],{"token":"([^"]+)"',
                r'"token":"([^"]+)"',
                r'{"name":"fb_dtsg","value":"([^"]+)"',
                r'name="fb_dtsg"\s+value="([^"]+)"'
            ]
            for url in endpoints:
                try:
                    res = client.get(url, headers=headers)
                    if res.status_code == 200:
                        for pattern in patterns:
                            m = re.search(pattern, res.text)
                            if m:
                                return m.group(1)
                except:
                    continue
        return None
    except:
        return None

def get_last_seq_id(cookie):
    try:
        ssl_context = create_ssl_context()
        headers = {
            'cookie': cookie,
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        with httpx.Client(verify=ssl_context, timeout=30.0, http2=True) as client:
            response = client.get('https://www.facebook.com/', headers=headers)
            if response.status_code == 200:
                match = re.search(r'"sync_sequence_id":"?(\d+)"?', response.text) or re.search(r'"lastSeqId":"?(\d+)"?', response.text)
                if match:
                    return match.group(1)
        return str(int(time.time() * 1000))
    except:
        return str(int(time.time() * 1000))

def generate_offline_threading_id():
    return str(int(time.time() * 1000))

def generate_session_id():
    return str(int(time.time() * 1000))

def generate_client_id():
    return hashlib.md5(str(time.time()).encode()).hexdigest()[:16]

def json_minimal(obj):
    return json.dumps(obj, separators=(',', ':'))

mqtt_lock = threading.Lock()

@dataclass
class CookieSession:
    cookie: str
    user_id: Optional[str] = None
    mqtt_client: Optional[mqtt.Client] = None
    last_seq_id: Optional[str] = None
    session_id: Optional[str] = None
    ws_req_number: int = 0
    ws_task_number: int = 0
    lock: threading.RLock = field(default_factory=threading.RLock)
    is_connected: bool = False
    account_name: str = ""
    account_index: int = 0
    login_info: Optional[dict] = None
    has_login_info: bool = False
    cookie_file: str = "cknew.txt"
    _disconnected_logged: bool = field(default=False, repr=False)
    cooldown_until: Optional[datetime] = None
    refresh_fail_count: int = 0
    is_active: bool = True
    delay: float = 1.0
    refresh_success_time: Optional[datetime] = None
    cooldown_after_refresh: bool = False
    reconnect_attempts: int = 0
    max_reconnect_attempts: int = 5
    _cooldown_printed: bool = field(default=False, repr=False)
    _refresh_printed: bool = field(default=False, repr=False)
    
    def initialize(self):
        uid = extract_user_id(self.cookie)
        if uid:
            self.user_id = uid
            return True
        return False
    
    def save_cookie_to_file(self):
        try:
            with open(self.cookie_file, 'a', encoding='utf-8') as f:
                f.write(self.cookie + '\n')
            return True
        except:
            return False

    def close_mqtt(self, log_reason=True):
        with self.lock:
            if self.mqtt_client:
                try:
                    self.mqtt_client.loop_stop()
                    self.mqtt_client.disconnect()
                except Exception:
                    pass
                self.mqtt_client = None
            self.is_connected = False
            if log_reason and not self._disconnected_logged and self.is_active:
                cprint(f"Acc {self.account_index} mat ket noi")
                self._disconnected_logged = True

    def refresh_cookie(self):
        if not self.has_login_info or not self.login_info or not self.is_active:
            return False
        
        with self.lock:
            # Reset flag để cho phép in lại khi cần
            if self.cooldown_until and datetime.now() < self.cooldown_until:
                if not self._cooldown_printed:
                    cprint(f"Acc {self.account_index} dang cho 2 ngay")
                    self._cooldown_printed = True
                return False
            
            if self.cooldown_after_refresh and self.refresh_success_time:
                wait_time = datetime.now() - self.refresh_success_time
                if wait_time.days < 2:
                    if not self._cooldown_printed:
                        cprint(f"Acc {self.account_index} dang cho 2 ngay")
                        self._cooldown_printed = True
                    return False
                else:
                    self.cooldown_after_refresh = False
                    self.refresh_success_time = None
                    self.cooldown_until = None
                    self._cooldown_printed = False
                    self._refresh_printed = False
        
        try:
            self.close_mqtt(log_reason=False)
            
            retry_count = 0
            max_retries = 3
            while retry_count < max_retries:
                fb_login = FacebookLogin(
                    uid_phone_mail=self.login_info['email'],
                    password=self.login_info['password'],
                    twwwoo2fa=self.login_info.get('2fa', '')
                )
                result = fb_login.login()
                
                if result.get('success'):
                    new_cookie = result.get('cookies_string', '')
                    if new_cookie and new_cookie != self.cookie:
                        self.cookie = new_cookie
                        if self.initialize():
                            self.save_cookie_to_file()
                            with self.lock:
                                self.refresh_success_time = datetime.now()
                                self.cooldown_after_refresh = True
                                self.refresh_fail_count = 0
                                self.reconnect_attempts = 0
                                self._cooldown_printed = False
                                self._refresh_printed = False
                            if not self._refresh_printed:
                                cprint(f"Acc {self.account_index}: Da lay cookie moi")
                                self._refresh_printed = True
                            return True
                    else:
                        with self.lock:
                            self.cooldown_until = datetime.now() + timedelta(days=2)
                            self.refresh_fail_count += 1
                            self._cooldown_printed = False
                            self._refresh_printed = False
                        cprint(f"Acc {self.account_index}: Cookie moi khong hop le")
                        return False
                
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(5 * retry_count)
            
            with self.lock:
                self.cooldown_until = datetime.now() + timedelta(days=2)
                self.refresh_fail_count += 1
                self._cooldown_printed = False
                self._refresh_printed = False
            cprint(f"Acc {self.account_index}: Refresh that bai")
            return False
        except Exception as e:
            with self.lock:
                self.cooldown_until = datetime.now() + timedelta(days=2)
                self.refresh_fail_count += 1
                self._cooldown_printed = False
                self._refresh_printed = False
            cprint(f"Acc {self.account_index}: Loi refresh: {e}")
            return False
    
    def connect_mqtt(self):
        if not self.is_active:
            return False
        
        with self.lock:
            # Reset flag để cho phép in lại khi cần
            if self.cooldown_until and datetime.now() < self.cooldown_until:
                if not self._cooldown_printed:
                    cprint(f"Acc {self.account_index} dang cho 2 ngay")
                    self._cooldown_printed = True
                return False
            
            if self.cooldown_after_refresh and self.refresh_success_time:
                wait_time = datetime.now() - self.refresh_success_time
                if wait_time.days < 2:
                    if not self._cooldown_printed:
                        cprint(f"Acc {self.account_index} dang cho 2 ngay")
                        self._cooldown_printed = True
                    return False
                else:
                    self.cooldown_after_refresh = False
                    self.refresh_success_time = None
                    self._cooldown_printed = False
                    self._refresh_printed = False
        
        self.close_mqtt(log_reason=False)
        self.last_seq_id = get_last_seq_id(self.cookie)
        if not self.last_seq_id:
            cprint(f"Acc {self.account_index}: Khong lay duoc last_seq_id")
            return False
        
        self.session_id = generate_session_id()
        self.mqtt_client = connect_mqtt(self.cookie, self.user_id, self.last_seq_id, self.session_id, self)
        
        if not self.mqtt_client:
            with self.lock:
                self.is_connected = False
                self.reconnect_attempts += 1
                if self.reconnect_attempts >= self.max_reconnect_attempts:
                    self.is_active = False
                    cprint(f"Acc {self.account_index}: Bi vo hieu hoa sau {self.max_reconnect_attempts} lan ket noi that bai")
            return False
        
        with self.lock:
            self.is_connected = True
            self._disconnected_logged = False
            self.reconnect_attempts = 0
            self._cooldown_printed = False
            self._refresh_printed = False
        return True

    def get_cooldown_status(self):
        with self.lock:
            if self.cooldown_until and datetime.now() < self.cooldown_until:
                return "dang cho 2 ngay"
            elif self.cooldown_after_refresh and self.refresh_success_time:
                wait_time = datetime.now() - self.refresh_success_time
                if wait_time.days < 2:
                    return "dang cho 2 ngay"
            return "San sang"

    def is_available(self):
        with self.lock:
            if not self.is_active:
                return False
            if self.cooldown_until and datetime.now() < self.cooldown_until:
                return False
            if self.cooldown_after_refresh and self.refresh_success_time:
                wait_time = datetime.now() - self.refresh_success_time
                if wait_time.days < 2:
                    return False
            return True

def send_message(cookie_session, thread_id, message_text):
    try:
        with cookie_session.lock:
            if not cookie_session.is_connected or not cookie_session.is_active:
                return False
            
            cookie_session.ws_req_number += 1
            cookie_session.ws_task_number += 1
            
            content = {
                "app_id": "2220391788200892",
                "payload": {
                    "data_trace_id": None,
                    "epoch_id": int(generate_offline_threading_id()),
                    "tasks": [],
                    "version_id": "7545284305482586",
                },
                "request_id": cookie_session.ws_req_number,
                "type": 3,
            }
            
            task_payload = {
                "initiating_source": 0,
                "multitab_env": 0,
                "otid": generate_offline_threading_id(),
                "send_type": 1,
                "skip_url_preview_gen": 0,
                "source": 0,
                "sync_group": 1,
                "text": message_text,
                "text_has_links": 0,
                "thread_id": int(thread_id),
            }
            
            task = {
                "failure_count": None,
                "label": "46",
                "payload": json.dumps(task_payload, separators=(",", ":")),
                "queue_name": str(thread_id),
                "task_id": cookie_session.ws_task_number,
            }
            
            content["payload"]["tasks"].append(task)
            
            cookie_session.ws_task_number += 1
            task_mark_payload = {
                "last_read_watermark_ts": int(time.time() * 1000),
                "sync_group": 1,
                "thread_id": int(thread_id),
            }
            
            task_mark = {
                "failure_count": None,
                "label": "21",
                "payload": json.dumps(task_mark_payload, separators=(",", ":")),
                "queue_name": str(thread_id),
                "task_id": cookie_session.ws_task_number,
            }
            
            content["payload"]["tasks"].append(task_mark)
            content["payload"] = json.dumps(content["payload"], separators=(",", ":"))
            
            with mqtt_lock:
                if not cookie_session.mqtt_client:
                    return False
                msg_info = cookie_session.mqtt_client.publish(
                    topic="/ls_req",
                    payload=json.dumps(content, separators=(",", ":")),
                    qos=1,
                    retain=False,
                )
                if msg_info.rc != mqtt.MQTT_ERR_SUCCESS:
                    cookie_session.close_mqtt(log_reason=True)
                    return False
            return True
    except Exception as e:
        cookie_session.close_mqtt(log_reason=True)
        return False

def on_connect_mqtt(client, userdata, flags, rc):
    session = userdata.get('session')
    if rc == 0:
        if session:
            with session.lock:
                session.is_connected = True
                session._disconnected_logged = False
        client.subscribe([("/t_ms", 0)])
        
        queue = {
            "sync_api_version": 10,
            "max_deltas_able_to_process": 1000,
            "delta_batch_size": 500,
            "encoding": "JSON",
            "entity_fbid": userdata['user_id'],
            "initial_titan_sequence_id": userdata['last_seq_id'],
            "device_params": None
        }
        
        try:
            client.publish(
                "/messenger_sync_create_queue",
                json_minimal(queue),
                qos=1,
                retain=False,
            )
        except Exception:
            pass
    else:
        if session:
            session.close_mqtt(log_reason=True)

def on_disconnect_mqtt(client, userdata, rc):
    session = userdata.get('session')
    if session:
        session.close_mqtt(log_reason=True)

def connect_mqtt(cookie, user_id, last_seq_id, session_id, session_obj=None):
    chat_on = json_minimal(True)
    user = {
        "u": user_id,
        "s": session_id,
        "chat_on": chat_on,
        "fg": False,
        "d": generate_client_id(),
        "ct": "websocket",
        "aid": 219994525426954,
        "mqtt_sid": "",
        "cp": 3,
        "ecp": 10,
        "st": ["/t_ms", "/messenger_sync_get_diffs", "/messenger_sync_create_queue"],
        "pm": [],
        "dc": "",
        "no_auto_fg": True,
        "gas": None,
        "pack": [],
    }
    
    userdata = {
        'user_id': user_id, 
        'last_seq_id': last_seq_id,
        'session': session_obj,
        'account_name': session_obj.account_name if session_obj else "Unknown"
    }
    
    mqtt_client = mqtt.Client(
        client_id="mqttwsclient",
        clean_session=True,
        protocol=mqtt.MQTTv31,
        transport="websockets",
        userdata=userdata
    )
    
    ssl_ctx = create_ssl_context()
    mqtt_client.tls_set_context(ssl_ctx)
    mqtt_client.on_connect = on_connect_mqtt
    mqtt_client.on_disconnect = on_disconnect_mqtt
    mqtt_client.username_pw_set(username=json_minimal(user))
    mqtt_client.ws_set_options(
        path="/chat",
        headers={
            "Cookie": cookie,
            "Origin": "https://www.messenger.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.messenger.com/",
            "Host": "edge-chat.messenger.com",
        },
    )
    
    try:
        mqtt_client.connect(
            host="edge-chat.messenger.com",
            port=443,
            keepalive=10,
        )
        mqtt_client.loop_start()
        
        wait_time = 0
        while wait_time < 10:
            if session_obj:
                with session_obj.lock:
                    if session_obj.is_connected:
                        return mqtt_client
                if mqtt_client.is_connected():
                    if session_obj:
                        with session_obj.lock:
                            session_obj.is_connected = True
                    return mqtt_client
            time.sleep(0.5)
            wait_time += 0.5
        
        if session_obj:
            session_obj.close_mqtt(log_reason=True)
        return None
    except Exception as e:
        if session_obj:
            session_obj.close_mqtt(log_reason=True)
        return None

BANNER = """
 ██╗  ██╗  █████╗ ██╗████████╗ ██████╗
 ██║ ██╔╝ ██╔══██╗██║╚══██╔══╝██╔═══██╗
 █████╔╝  ███████║██║   ██║   ██║   ██║
 ██╔═██╗  ██╔══██║██║   ██║   ██║   ██║
 ██║  ██╗ ██║  ██║██║   ██║   ╚██████╔╝
 ╚═╝  ╚═╝ ╚═╝  ╚═╝╚═╝   ╚═╝    ╚═════╝

 Anh Em Royals War V2 - Huy Kaito Yeu Em 🪽
========================================⠀⠀⠀⠀"""

auto_gc(60)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def load_data_from_file(filename):
    data_list = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split('|')
                if len(parts) == 1:
                    data_list.append({'type': 'cookie_only', 'cookie': parts[0].strip()})
                elif len(parts) >= 4:
                    data_list.append({
                        'type': 'cookie_account',
                        'cookie': parts[0].strip(),
                        'email': parts[1].strip(),
                        'password': parts[2].strip(),
                        '2fa': parts[3].strip().replace(" ", "") if len(parts) > 3 else ''
                    })
                elif len(parts) == 3:
                    data_list.append({
                        'type': 'cookie_account',
                        'cookie': parts[0].strip(),
                        'email': parts[1].strip(),
                        'password': parts[2].strip(),
                        '2fa': ''
                    })
        return data_list
    except Exception as e:
        return None

def read_message_from_file(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except:
        return None

def send_worker(session, box_ids, message, stop_event):
    while not stop_event.is_set():
        try:
            if not session.is_available():
                if not session.is_active:
                    break
                time.sleep(60)
                continue

            with session.lock:
                if not session.is_connected:
                    if session.has_login_info:
                        if session.refresh_fail_count >= 3:
                            session.is_active = False
                            cprint(f"Acc {session.account_index}: Bi vo hieu hoa sau 3 lan refresh that bai")
                            break
            
            if not session.is_connected:
                if session.has_login_info:
                    if session.refresh_cookie():
                        time.sleep(60)
                        continue
                    else:
                        time.sleep(60)
                        continue
                else:
                    if session.connect_mqtt():
                        cprint(f"Acc {session.account_index}: Ket noi lai thanh cong")
                    else:
                        time.sleep(session.delay)
                        continue
            
            if not session.is_available() or not session.is_connected:
                time.sleep(session.delay)
                continue
            
            for box_id in box_ids:
                if stop_event.is_set():
                    break
                
                if not session.is_available() or not session.is_connected:
                    break
                
                success = send_message(session, box_id, message)
                if success:
                    cprint(f"Acc {session.account_index} -> {box_id}")
                else:
                    session.close_mqtt(log_reason=True)
                    break
                
                time.sleep(session.delay)
                
        except Exception as e:
            cprint(f"Acc {session.account_index}: Loi {e}")
            time.sleep(session.delay)

def main():
    clear_screen()
    cprint(BANNER, step=0.05, spread=0.5)
    
    while True:
        filename = cinput("File cookies: ").strip() or "data.txt"
        data_list = load_data_from_file(filename)
        if data_list:
            cprint(f"Da doc {len(data_list)} tai khoan")
            break
        cprint("File khong hop le!")

    sessions = []
    
    for idx, data in enumerate(data_list, 1):
        if data['type'] == 'cookie_only':
            session = CookieSession(data['cookie'])
            session.has_login_info = False
            session.account_index = idx
            if session.initialize():
                session.account_name = f"Acc {idx}"
                sessions.append(session)
            else:
                cprint(f"Acc {idx}: Cookie khong hop le")
        else:
            acc = {'email': data['email'], 'password': data['password'], '2fa': data.get('2fa', '')}
            session = CookieSession(data['cookie'])
            session.login_info = acc
            session.has_login_info = True
            session.cookie_file = "acc1.txt"
            session.account_index = idx
            
            if session.initialize():
                session.account_name = f"Acc {idx}"
                sessions.append(session)
            else:
                if session.refresh_cookie():
                    session.account_name = f"Acc {idx}"
                    sessions.append(session)
                else:
                    cprint(f"Acc {idx}: Khong the refresh cookie")

    if not sessions:
        cprint("Khong co session nao hoat dong!")
        return

    # Reset flags và hiển thị trạng thái ban đầu
    for session in sessions:
        session._cooldown_printed = False
        session._refresh_printed = False
        status = session.get_cooldown_status()
        if status == "dang cho 2 ngay":
            cprint(f"Acc {session.account_index}: dang cho 2 ngay")
            session._cooldown_printed = True

    cprint("Nhap ID box (done de ket thuc):")
    box_ids = []
    while True:
        box_id = cinput("> ").strip()
        if box_id.lower() == 'done':
            break
        if box_id.isdigit():
            box_ids.append(box_id)
        else:
            cprint("Vui long nhap so hoac 'done'")

    if not box_ids:
        cprint("Chua nhap box nao!")
        return

    while True:
        msg_file = cinput("File tin nhan: ").strip()
        message = read_message_from_file(msg_file)
        if message:
            break
        cprint("File tin nhan khong hop le!")

    mode = cinput("Che do (1-Song song / 2-Luan phien): ").strip()
    mode = 1 if mode not in ('1','2') else int(mode)

    if mode == 2:
        while True:
            try:
                delay = float(cinput("Delay : ").strip())
                break
            except:
                cprint("Nhap so hop le!")
        for session in sessions:
            session.delay = delay
    else:
        for session in sessions:
            while True:
                try:
                    delay = float(cinput(f"Acc {session.account_index} delay: ").strip())
                    session.delay = delay
                    break
                except:
                    cprint("Nhap so hop le!")

    cprint("Dang ket noi MQTT...")
    for session in sessions:
        if session.connect_mqtt():
            cprint(f"Acc {session.account_index}: Ket noi thanh cong")
        else:
            cprint(f"Acc {session.account_index}: Khong the ket noi")

    time.sleep(5)

    stop_event = threading.Event()

    try:
        if mode == 1:
            threads = []
            for session in sessions:
                if session.is_active and session.is_available():
                    thread = threading.Thread(
                        target=send_worker,
                        args=(session, box_ids, message, stop_event)
                    )
                    thread.daemon = True
                    thread.start()
                    threads.append(thread)
            
            for thread in threads:
                thread.join()
                
        else:
            while True:
                # Reset flags và kiểm tra trạng thái cooldown
                for s in sessions:
                    if s.is_active and not s.is_available():
                        status = s.get_cooldown_status()
                        if status == "dang cho 2 ngay" and not s._cooldown_printed:
                            cprint(f"Acc {s.account_index}: dang cho 2 ngay")
                            s._cooldown_printed = True
                    elif s.is_active and s.is_available():
                        # Reset flag khi đã sẵn sàng
                        s._cooldown_printed = False
                
                dead_sessions = [s for s in sessions if s.is_active and not s.is_connected]
                for s in dead_sessions:
                    if not s.is_available():
                        continue
                        
                    if s.has_login_info:
                        with s.lock:
                            if s.refresh_fail_count >= 3:
                                s.is_active = False
                                s.close_mqtt(log_reason=False)
                                cprint(f"Acc {s.account_index}: Bi vo hieu hoa sau 3 lan refresh that bai")
                                continue
                        
                        if s.refresh_cookie():
                            pass  # refresh_cookie đã tự in thông báo
                    else:
                        if s.connect_mqtt():
                            cprint(f"Acc {s.account_index}: Ket noi lai thanh cong")

                active_sessions = [s for s in sessions if s.is_active and s.is_connected and s.is_available()]
                if not active_sessions:
                    # Kiểm tra xem có session nào đang trong cooldown không
                    has_cooldown = False
                    for s in sessions:
                        if s.is_active and not s.is_available():
                            status = s.get_cooldown_status()
                            if status == "dang cho 2 ngay" and not s._cooldown_printed:
                                cprint(f"Acc {s.account_index}: dang cho 2 ngay")
                                s._cooldown_printed = True
                                has_cooldown = True
                    if not has_cooldown:
                        cprint("Khong con tai khoan hoat dong!")
                    time.sleep(60)
                    continue

                for box_id in box_ids:
                    for session in active_sessions:
                        if not session.is_available() or not session.is_connected:
                            continue
                        success = send_message(session, box_id, message)
                        if success:
                            cprint(f"Acc {session.account_index} -> {box_id}")
                        else:
                            session.close_mqtt(log_reason=True)
                        time.sleep(session.delay)

    except KeyboardInterrupt:
        cprint("\nDang dung chuong trinh...")
        stop_event.set()
        cprint("\nDa dung chuong trinh!")
    finally:
        stop_event.set()
        for s in sessions:
            s.close_mqtt(log_reason=False)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        cprint(f"Loi: {e}")