import paho.mqtt.client as mqtt, json, time, threading, uuid, ssl, os, warnings, random, gc
warnings.filterwarnings("ignore")

cks, bxs, msg, dls, ck_ua, ck_uid = [], [], "", 15.0, {}, {}

clr = lambda: os.system("cls" if os.name == "nt" else "clear")
lg  = lambda t: print(f"[➤ ] {t}")

BANNER = """
██╗  ██╗  █████╗ ██╗████████╗ ██████╗
██║ ██╔╝ ██╔══██╗██║╚══██╔══╝██╔═══██╗
█████╔╝  ███████║██║   ██║   ██║   ██║
██╔═██╗  ██╔══██║██║   ██║   ██║   ██║
██║  ██╗ ██║  ██║██║   ██║   ╚██████╔╝
╚═╝  ╚═╝ ╚═╝  ╚═╝╚═╝   ╚═╝    ╚═════╝

Anh Em Royals War - Dev : Huy Kaito
====================================⠀⠀⠀⠀"""

UAS = [
    "Mozilla/5.0 (Linux; Android 11; RMX2185) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.140 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; Redmi Note 11) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.129 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; Redmi Note 8) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/108.0.0.0 Mobile Safari/537.36 Via/4.8.2",
    "Mozilla/5.0 (Linux; Android 11; V2109) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/112.0.5615.138 Mobile Safari/537.36 Via/4.9.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
]

COLORS = [(255, 215, 0), (255, 245, 100), (255, 255, 255)]
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
                lg(f"{uid_log} đang kết nối...")
                cl, tk = cmq(ck, ua)
                if cl is None:
                    stop_event.wait(5); continue
                uid = tk.split("|")[0]
                lg(f"{uid_log} kết nối OK")
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
                    lg(f"[{uid_log}] → [{bx}]")
                except Exception:
                    try: cl.loop_stop(); cl.disconnect()
                    except Exception: pass
                    clients[idx] = (None, None, None)
                    failed = True; break

            if not failed:
                stop_event.wait(max(1.0, current_dls + random.uniform(-1.0, 1.0)))

    for _, (cl, _, _) in list(clients.items()):
        if cl is not None:
            try: cl.loop_stop(); cl.disconnect()
            except Exception: pass
    lg(f"Một tiến trình cũ đã dừng và dọn dẹp")

def mn():
    global cks, bxs, msg, dls, ck_ua, ck_uid
    clr(); bnr()

    # Cài đặt ban đầu
    while True:
        f_ck = "ck.txt"
        cks = lck(f_ck)
        if cks: 
            lg(f"Tìm thấy {len(cks)} cookie.")
            break
        print("Đéo có")

    try:
        with open("delay.txt", "r") as f:
            dls = float(f.read().strip())
    except Exception:
        dls = 60.0

    while True:
        idb = "id.txt"
        bxs = lck(idb)
        if bxs: 
            lg(f"Tìm thấy {len(bxs)} id box.")
            break
        print("Đéo có")

    while True:
        try:
            with open("ngon.txt", encoding="utf-8") as f:
                msg = f.read().strip()
            if msg: break
        except Exception:
            print("Lỗi")
    
    # Khởi tạo luồng chạy đầu tiên
    ck_ua = {i: random.choice(UAS) for i in range(len(cks))}
    ck_uid = {i: (gtk(ck).split("|")[0] if gtk(ck) else f"C{i+1}") for i, ck in enumerate(cks)}
    
    current_stop_event = threading.Event()
    threading.Thread(target=wk, args=(current_stop_event, cks, ck_ua, ck_uid, dls), daemon=True).start()

    # Vòng lặp lắng nghe thay đổi file cookie / delay trực tiếp ở Main Thread
    while True:
        try:
            # Lắng nghe lệnh ẩn (Không in hướng dẫn để đỡ rác màn hình)
            new_file = input().strip()
            if not new_file: 
                continue
            
            # Kiểm tra file cookie mới nhập vào
            new_cks = lck(new_file)
            if not new_cks:
                # Nếu sai file hoặc file trống, bỏ qua không làm gì cả, không crash
                continue
                
            # Nếu file đúng, mới hiện print nhập delay mới
            try:
                with open("delay.txt", "r") as f:
                    dls = float(f.read().strip())
            except Exception:
                dls = 60.0
            
            # Chuẩn bị dữ liệu cho luồng mới
            new_ua = {i: random.choice(UAS) for i in range(len(new_cks))}
            new_uid = {i: (gtk(ck).split("|")[0] if gtk(ck) else f"C{i+1}") for i, ck in enumerate(new_cks)}
            
            # Tạo event stop riêng cho luồng mới
            next_stop_event = threading.Event()
            
            # Bật luồng mới lên chạy trước
            threading.Thread(target=wk, args=(next_stop_event, new_cks, new_ua, new_uid, new_dls), daemon=True).start()
            
            # Ra lệnh dừng luồng cũ sau khi luồng mới đã kích hoạt thành công
            current_stop_event.set()
            
            # Thay thế biến điều khiển và dọn rác hệ thống
            current_stop_event = next_stop_event
            gc.collect()
            
        except KeyboardInterrupt:
            lg("Đang dừng toàn bộ chương trình...")
            current_stop_event.set()
            time.sleep(1.5)
            break

if __name__ == "__main__":
    mn()
