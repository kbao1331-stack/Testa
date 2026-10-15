import paho.mqtt.client as mqtt
import json
import time
import threading
import uuid
import ssl
import os
import sys
import warnings
from pystyle import Colors, Colorate

warnings.filterwarnings("ignore")

FB_DOMAIN = "edge-chat.facebook.com"
FB_PORT = 443
FB_AID = 219994525426954
CONNECT_TIMEOUT = 7
TOPIC_SEND = "/send_message2"


def clear():
    os.system("cls" if os.name == "nt" else "clear")

BANNER = """
⠀⠀⠀⠀⠀⠀⠀⢀⣠⣤⣤⣄⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⡼⣟⣯⡷⣿⡽⣟⣷⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢀⢄⢄⢀⠙⢯⣿⠻⠙⠓⠀⢀⢀⡀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣠⣠⣀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠸⡸⡸⡸⠀⢀⣠⣴⣾⣻⣟⣿⣻⣟⣿⣻⣟⣷⣶⣤⣄⡀⠀⠰⣟⣯⣿⣽⣯⡿⣆⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠣⠃⣠⡾⣟⣯⡷⣿⣽⣯⣿⣽⣯⣿⣽⣯⡷⣿⢾⣯⡿⣷⣦⡈⠳⢿⢾⠳⠛⠙⠂⠀⠀⠀
⠀⠀⠀⠀⠀⠀⢀⣴⣟⣿⢯⣿⣻⣽⡾⣷⢿⡾⣷⢿⡾⣷⣟⣿⣻⡷⣟⣿⢾⡿⣆⠈⢀⢔⢔⢲⠂⠀⠀⠀
⠀⠀⠀⠀⠀⢀⣾⣯⡿⣾⣻⣽⢿⣾⣻⣟⣿⣻⣟⣿⣻⣯⣿⣽⣯⣿⣻⣽⣟⣿⣻⣷⠀⢱⢱⠑⠁⠀⠀⠀
⠀⠀⠀⠀⠀⢼⡷⣿⡽⣿⣽⢾⣿⣽⣯⣿⣽⣯⣿⣽⣯⡷⣿⢾⡷⣿⣽⡷⣿⣽⣟⣾⣇⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⢀⣿⣻⣽⢿⣽⣾⣻⢷⡿⣾⢷⡿⣾⢷⡿⣾⣟⣿⣻⣟⣿⢾⣟⣿⢾⣯⣷⢿⡀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⢐⣿⣽⢾⣻⣷⠋⠉⠉⢻⣟⣿⣻⣟⣿⣻⣯⣿⣽⣯⠿⠽⢻⣯⣿⣻⡷⣿⣻⡂⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠐⣿⢾⣿⣽⢾⡀⠀⠀⣰⣿⣽⣿⠟⠛⢿⣷⡿⣞⠇⠀⠀⠈⣷⢿⣽⣟⣿⣽⠂⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢹⣟⣷⢿⣻⣟⣯⡿⣯⣿⣿⠿⠂⠀⢾⣿⣿⡿⣷⣤⠤⠐⠛⠫⢷⡿⣽⡞⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠙⣿⣻⣽⣯⣷⢿⣯⣿⣯⣤⣶⣧⣄⣼⣿⣟⣿⠎⢠⡺⡿⣦⠈⣿⡯⠃⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠑⠿⢾⣯⡿⣷⢿⣾⣻⣟⣿⣻⣯⡷⡿⠙⣁⣸⡻⣿⣎⡀⠙⠁⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢉⠉⠋⠓⠻⠽⠯⠷⠻⠽⠀⣼⣝⠟⠻⣾⣮⡻⡷⣦⣀⢤⢤⡀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣻⣟⣷⢶⣖⣆⠀⠒⠀⠐⣝⣟⢧⢴⠝⢻⢿⢿⣮⣻⡻⡷⠁⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣿⣽⣯⢿⣻⣽⣯⡿⣿⢶⡀⠈⠻⣷⣤⡂⢸⣷⣀⣸⡻⡇⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠰⣿⣞⣯⣿⣻⡚⠳⠿⡻⠿⠁⣸⡢⣄⠉⠻⠷⣷⣝⡟⠟⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠨⣿⢾⣷⣻⣽⣷⣶⡆⢀⢶⣮⣯⡻⣮⣟⣖⢦⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠨⣿⢯⡷⣟⣷⢿⣽⣇⣈⣁⣄⠙⠻⢾⣮⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠹⣟⣿⠤⠀⠀⠀⠈⠀⠀⠀⠸⡀⠙⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠈⠀
🌟 TOOL TREO NGÔN MESS : Ma Bao Nam
👑 Admin : Ma Bao Nam
📱 Thông Tin Liên Hệ
• Zalo : 0993692060
========================================="""


def log(t):
    ln = f"[~] {t}"
    print(Colorate.Horizontal(Colors.rainbow, ln))


clear()


def load_cookies(file):
    data = []
    try:
        with open(file, "r", encoding="utf-8") as f:
            for line in f:
                c = line.strip()
                if c and "=" in c:
                    data.append(c)
    except FileNotFoundError:
        log(f"Không tìm thấy file: {file}")
    except Exception as e:
        log(f"Lỗi đọc file cookie: {e}")
    return data


def get_token(cookie):
    c_user = None
    xs = None
    for p in cookie.split(";"):
        p = p.strip()
        if not p or "=" not in p:
            continue
        key, _, val = p.partition("=")
        key = key.strip()
        if key == "c_user":
            c_user = val.strip()
        elif key == "xs":
            xs = val.strip()
    if c_user and xs:
        return c_user, xs
    return None, None


class FBClient:

    def __init__(self, cookie):
        self.cookie = cookie
        self.uid = None
        self.client = None
        self.connected = False
        self._conn_event = threading.Event()
        self._lock = threading.Lock()

    def _on_connect(self, client, userdata, flags, rc):
        if rc in (0, 24, 2):
            self.connected = True
            pass
        else:
            self.connected = False
            log(f"Connect thất bại cho uid {self.uid}")
        self._conn_event.set()

    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        if rc in (0, 24, 2):
            pass
        else:
            log(f"Disconnect bất thường uid {self.uid} (rc={rc})")

    def _on_publish(self, client, userdata, mid):
        pass

    def connect(self):
        c_user, xs = get_token(self.cookie)
        if not c_user or not xs:
            log("Cookie thiếu c_user hoặc xs")
            return False
        self.uid = c_user

        try:
            client = mqtt.Client(
                client_id=f"mqtt_{uuid.uuid4().hex[:8]}",
                transport="websockets",
                protocol=mqtt.MQTTv31,
                clean_session=True,
            )
            client.username_pw_set(
                username=json.dumps({
                    "u": c_user,
                    "s": 1,
                    "chat_on": True,
                    "fg": True,
                    "d": str(uuid.uuid4()),
                    "ct": "websocket",
                    "aid": FB_AID,
                }),
                password="",
            )
            client.tls_set(cert_reqs=ssl.CERT_NONE)
            client.tls_insecure_set(True)
            client.ws_set_options(
                path="/chat",
                headers={
                    "Cookie": self.cookie,
                    "Origin": "https://www.facebook.com",
                    "User-Agent": "Mozilla/5.0",
                },
            )
            client.on_connect = self._on_connect
            client.on_disconnect = self._on_disconnect
            client.on_publish = self._on_publish

            client.connect(FB_DOMAIN, FB_PORT, keepalive=60)
            client.loop_start()
            self.client = client

            if not self._conn_event.wait(CONNECT_TIMEOUT):
                log(f"Timeout kết nối uid {c_user}")
                self.close()
                return False

            return self.connected
        except Exception as e:
            log(f"Lỗi kết nối uid {c_user}: {e}")
            self.close()
            return False

    def publish(self, topic, payload):
        if not self.client or not self.connected:
            return False
        with self._lock:
            try:
                info = self.client.publish(topic, payload, qos=0)
                return info.rc == mqtt.MQTT_ERR_SUCCESS
            except Exception as e:
                log(f"Publish lỗi uid {self.uid}: {e}")
                return False

    def close(self):
        try:
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()
        except Exception:
            pass
        self.client = None
        self.connected = False


def prompt_input(prompt, validator=None, err="Giá trị không hợp lệ"):
    while True:
        v = input(prompt).strip()
        if validator is None or validator(v):
            return v
        log(err)


def build_payload(uid, box, message):
    msg_id = str(int(time.time() * 1000))
    return json.dumps({
        "body": message,
        "msgid": msg_id,
        "sender_fbid": uid,
        "to": box,
        "offline_threading_id": msg_id,
    })


def main():
    print(Colorate.Horizontal(Colors.rainbow, BANNER))
    cookie_file = prompt_input(
        "File cookies: ",
        validator=lambda x: os.path.isfile(x),
        err="File không tồn tại, thử lại",
    )
    cookies = load_cookies(cookie_file)
    if not cookies:
        log("Không có cookie nào.")
        return

    clients = []
    for c in cookies:
        fc = FBClient(c)
        if fc.connect():
            clients.append(fc)
        else:
            fc.close()

    log(f"{len(clients)}/{len(cookies)} cookies live")
    if not clients:
        log("Không có cookie nào live. Dừng.")
        return

    idbox = prompt_input(
        "ID box : ",
        validator=lambda x: len([i for i in x.split(",") if i.strip()]) > 0,
        err="Cần ít nhất 1 ID box",
    )
    idbox = [x.strip() for x in idbox.split(",") if x.strip()]

    msg_file = prompt_input(
        "File nội dung : ",
        validator=lambda x: os.path.isfile(x),
        err="File không tồn tại, thử lại",
    )
    try:
        with open(msg_file, "r", encoding="utf-8") as f:
            message = f.read().strip()
    except Exception as e:
        log(f"Lỗi đọc file nội dung: {e}")
        return
    if not message:
        log("File nội dung rỗng.")
        return

    def valid_delay(x):
        try:
            return float(x) >= 0
        except ValueError:
            return False

    delay = float(prompt_input(
        "Delay (giây) : ",
        validator=valid_delay,
        err="Delay phải là số >= 0",
    ))

    stop_event = threading.Event()

    def send_loop():
        while not stop_event.is_set():
            for fc in clients:
                if stop_event.is_set():
                    break
                if not fc.connected:
                    log(f"uid {fc.uid} mất kết nối")
                    continue
                for box in idbox:
                    if stop_event.is_set():
                        break
                    payload = build_payload(fc.uid, box, message)
                    ok = fc.publish(TOPIC_SEND, payload)
                    if ok:
                        log(f"{fc.uid} send to {box}")
                    else:
                        log(f"Gửi thất bại {fc.uid} -> {box}")
                if stop_event.wait(delay):
                    return

    worker = threading.Thread(target=send_loop, daemon=True)
    worker.start()

    try:
        while worker.is_alive():
            worker.join(timeout=1)
    except KeyboardInterrupt:
        log("Đang dừng...")
        stop_event.set()
        worker.join(timeout=5)
    finally:
        for fc in clients:
            fc.close()
        log("Đã đóng tất cả kết nối. Bye!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"Lỗi không mong đợi: {e}")
        sys.exit(1)
