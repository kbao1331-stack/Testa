import base64, datetime, json, os, random, re, sys, time, uuid, threading
import gc
import httpx
from termcolor import colored
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.backends import default_backend

# ======================== CẤU HÌNH ========================
IM_AID = "1988"
SEND_URL = "https://im-api-sg.tiktok.com/v1/message/send"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

# ======================== PROTOBUF HELPERS ========================
def ev(n):
    b = n & 0xFFFFFFFFFFFFFFFF
    o = bytearray()
    while b >= 0x80:
        o.append((b & 0x7F) | 0x80)
        b >>= 7
    o.append(b & 0x7F)
    return bytes(o)

def et(fn, wt):
    return ev((fn << 3) | wt)

def pbv(fn, v):
    return b"" if not v else et(fn, 0) + ev(v)

def pbb(fn, d):
    return b"" if not d else et(fn, 2) + ev(len(d)) + d

def pbs(fn, t):
    return b"" if not t else pbb(fn, t.encode("utf-8"))

def pbkv(k, v):
    return pbb(15, pbs(1, k) + pbs(2, v))

# ======================== DPoP ========================
def b64url(b):
    return base64.urlsafe_b64encode(b).decode().rstrip("=")

def gen_key():
    return ec.generate_private_key(ec.SECP256R1(), default_backend())

def pub_point(priv):
    n = priv.public_key().public_numbers()
    return b"\x04" + n.x.to_bytes(32, "big") + n.y.to_bytes(32, "big")

def build_dpop(priv, htm, htu):
    n = priv.public_key().public_numbers()
    jwk = {"crv": "P-256", "kty": "EC", "x": b64url(n.x.to_bytes(32, "big")), "y": b64url(n.y.to_bytes(32, "big"))}
    h = json.dumps({"alg": "ES256", "typ": "dpop+jwt", "jwk": jwk}, separators=(",", ":")).encode()
    p = json.dumps({"jti": b64url(os.urandom(32)), "htm": htm, "htu": htu, "iat": int(time.time())}, separators=(",", ":")).encode()
    si = f"{b64url(h)}.{b64url(p)}"
    sig = priv.sign(si.encode(), ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(sig)
    return f"{si}.{b64url(r.to_bytes(32, 'big') + s.to_bytes(32, 'big'))}"

# ======================== COOKIE & META ========================
def extract_cookie(cs, name):
    for p in cs.split(";"):
        kv = p.strip().split("=", 1)
        if len(kv) == 2 and kv[0].strip() == name:
            return kv[1].strip()
    return ""

def get_device(cs):
    return extract_cookie(cs, "s_v_web_id") or "verify_msodzfdz_LM6w5Wfo_LJer_4bBr_8hqT_IC0ULF1Unn72"

def rand_bogus():
    return "".join(random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(32))

def build_meta(device_id, ms_token, verify_fp, pubkey, ua):
    pairs = [("aid", IM_AID), ("app_name", "tiktok_web"), ("channel", "web"),
             ("device_platform", "web_pc"), ("device_id", device_id), ("region", "VN"),
             ("priority_region", "VN"), ("os", "windows"), ("referer", "https://www.tiktok.com/messages"),
             ("root_referer", ""), ("cookie_enabled", "true"), ("screen_width", "1920"),
             ("screen_height", "1080"), ("browser_language", "vi-VN"), ("browser_platform", "Win32"),
             ("browser_name", "Mozilla"), ("browser_version", ua), ("browser_online", "true")]
    if verify_fp:
        pairs.append(("verifyFp", verify_fp))
    pairs.extend([("app_language", "vi-VN"), ("webcast_language", "vi-VN"), ("tz_name", "Asia/Ho_Chi_Minh"),
                  ("is_page_visible", "true"), ("focus_state", "true"), ("is_fullscreen", "false"),
                  ("history_len", "2"), ("user_is_login", "true"), ("data_collection_enabled", "true"),
                  ("from_appID", IM_AID), ("locale", "vi-VN"), ("tt-ticket-guard-public-key", pubkey),
                  ("tt-ticket-guard-client-data", ""), ("tt-ticket-guard-version", "2"),
                  ("tt-ticket-guard-iteration-version", "0"), ("tt-ticket-guard-web-version", "1"),
                  ("user_agent", ua)])
    if ms_token:
        pairs.append(("Web-Sdk-Ms-Token", ms_token))
    out = b""
    for k, v in pairs:
        out += pbkv(k, v)
    return out

# ======================== PARSE GROUPS ========================
def dv(data, i):
    r = 0
    sh = 0
    while True:
        b = data[i]
        i += 1
        r |= (b & 0x7F) << sh
        if not (b & 0x80):
            break
        sh += 7
    return r, i

def parse(data):
    fields = []
    i = 0
    n = len(data)
    while i < n:
        tag, i = dv(data, i)
        fn = tag >> 3
        wt = tag & 7
        if wt == 0:
            v, i = dv(data, i)
            fields.append((fn, wt, v))
        elif wt == 2:
            l, i = dv(data, i)
            fields.append((fn, wt, data[i:i+l]))
            i += l
        elif wt == 1:
            i += 8
        elif wt == 5:
            i += 4
        else:
            break
    return fields

def looks_like_title(s):
    if not s:
        return False
    s = s.replace("\u2068", "").replace("\u2069", "").strip()
    if len(s) < 2 or len(s) > 80 or s.isdigit():
        return False
    bad = ("aweType", "client_message_id", "source_aid", "im_callback", "avatar",
           "group_type", "deprecated", "conv_set_notification", "involved_user",
           "was_minor_group", "tt-ticket", "Web-Sdk", "device_id", "msToken",
           "verify_", "tos-", "http", "AAA", "BAA", "LMS", "s_v_web", "MS4wLjAB")
    low = s.lower()
    if any(b.lower() in low for b in bad):
        return False
    if len(s) > 28 and " " not in s and sum(c.isalnum() or c in "_-" for c in s) / max(len(s), 1) > 0.92:
        viet = "àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"
        if not any(c in viet for c in low):
            return False
    return True

def extract_groups(data):
    cand = []
    def walk(blob, d=0):
        if d > 15 or not blob or len(blob) < 3:
            return
        fields = parse(blob)
        ids = []
        titles = []
        typ = 0
        src = 0
        for fn, wt, val in fields:
            if wt == 0:
                if fn in (2, 5, 6) and val in (1, 2, 3):
                    typ = val
                if fn == 5 and isinstance(val, int) and val > 10**13:
                    src = val
            elif wt == 2 and isinstance(val, bytes):
                s = val.decode("utf-8", errors="ignore").strip()
                sc = s.replace("\u2068", "").replace("\u2069", "").strip()
                if s.isdigit() and 15 <= len(s) <= 22:
                    ids.append(s)
                elif looks_like_title(sc):
                    titles.append(sc)
                walk(val, d+1)
        for cid in ids:
            title = titles[0] if titles else ""
            cand.append((cid, title, typ, src or int(cid)))
    walk(data)
    raw = data.decode("latin-1", errors="ignore")
    for m in re.finditer(r"(?<!\d)(\d{15,22})(?!\d)", raw):
        cand.append((m.group(1), "", 0, int(m.group(1))))
    best = {}
    for cid, title, typ, src in cand:
        if cid not in best:
            best[cid] = {"id": cid, "source_id": src, "type": typ, "name": title or f"Box {cid[-8:]}"}
        else:
            if title and (best[cid]["name"].startswith("Box ") or len(title) > len(best[cid]["name"])):
                best[cid]["name"] = title
            if typ and not best[cid]["type"]:
                best[cid]["type"] = typ
    groups = list(best.values())
    groups.sort(key=lambda g: (0 if not g["name"].startswith("Box ") else 1, g["name"].lower()))
    return groups

# ======================== CLIENT ========================
class TClient:
    def __init__(self, cookie):
        self.cookie = cookie.strip()
        self.ua = USER_AGENT
        self.headers = {
            "Cookie": self.cookie,
            "User-Agent": self.ua,
            "Accept-Language": "vi-VN,vi;q=0.9",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.tiktok.com/",
            "Origin": "https://www.tiktok.com"
        }
        self.im_client = httpx.Client(base_url="https://im-api-sg.tiktok.com", headers=self.headers, timeout=20)

    def _req(self, method, url, **kw):
        client = self.im_client
        resp = getattr(client, method.lower())(url, **kw)
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}")
        return resp

    def get_groups(self):
        dev = get_device(self.cookie)
        ms = extract_cookie(self.cookie, "msToken")
        vf = extract_cookie(self.cookie, "s_v_web_id")
        payload = (
            et(1, 0) + ev(203) + et(2, 0) + ev(10002) + pbs(3, "1.6.0") +
            et(4, 2) + ev(0) + et(5, 0) + ev(3) + et(6, 0) + ev(1) +
            pbb(8, b"\xda\x0c\x02\x08\x00") + pbs(9, dev) + pbs(11, "web") +
            build_meta(dev, ms, vf, "", self.ua) + et(18, 0) + ev(1) +
            pbb(100, pbb(1, et(1, 0) + ev(0)))
        )
        headers = {"Accept": "application/x-protobuf", "Content-Type": "application/x-protobuf",
                   "Referer": "https://www.tiktok.com/messages"}
        r = self._req("POST", "https://im-api-sg.tiktok.com/v2/message/get_by_user_init",
                      headers=headers, params={"aid": IM_AID, "version_code": "1.0.0",
                                               "app_name": "tiktok_web", "device_platform": "web_pc",
                                               "msToken": ms, "X-Bogus": rand_bogus()},
                      content=payload)
        return extract_groups(r.content)

    def send(self, cid, src, text):
        dev = get_device(self.cookie)
        ms = extract_cookie(self.cookie, "msToken")
        vf = extract_cookie(self.cookie, "s_v_web_id")
        priv = gen_key()
        pub = base64.b64encode(pub_point(priv)).decode()
        dpop = build_dpop(priv, "POST", SEND_URL)
        cmid = str(uuid.uuid4())
        t1 = pbb(5, pbs(1, "s:mentioned_users"))
        t2 = pbb(5, pbs(1, "s:client_message_id") + pbb(2, cmid.encode()))
        body = (pbs(1, cid) + pbv(2, 2) + pbv(3, src) +
                pbb(4, json.dumps({"aweType": 0, "text": text}).encode()) +
                t1 + t2 + pbv(6, 7) + pbs(7, "deprecated") + pbs(8, cmid))
        payload = (et(1, 0) + ev(100) + et(2, 0) + ev(10014) + pbs(3, "1.6.0") +
                   et(4, 2) + ev(0) + et(5, 0) + ev(3) + et(6, 0) + ev(1) +
                   et(7, 2) + ev(0) + pbb(8, pbb(100, body)) +
                   pbs(9, dev) + pbs(11, "web") +
                   build_meta(dev, ms, vf, pub, self.ua) +
                   et(18, 0) + ev(1))
        headers = {"Accept": "application/x-protobuf", "Content-Type": "application/x-protobuf",
                   "Cache-Control": "no-cache", "Origin": "https://www.tiktok.com",
                   "Referer": "https://www.tiktok.com/messages",
                   "tt-ticket-guard-iteration-version": "0", "tt-ticket-guard-public-key": pub,
                   "tt-ticket-guard-version": "2", "tt-ticket-guard-web-version": "1", "DPoP": dpop}
        params = {"aid": IM_AID, "version_code": "1.0.0", "app_name": "tiktok_web",
                  "device_platform": "web_pc", "ztca-version": "1", "ztca-dpop": dpop,
                  "msToken": ms, "X-Bogus": rand_bogus()}
        r = self._req("POST", SEND_URL, headers=headers, params=params, content=payload)
        return cmid

# ======================== MAIN ========================
def clear():
    os.system("cls" if os.name == "nt" else "clear")

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

def main():
    clear()
    bnr()

    cookie_file = input("File cookies : ").strip()
    with open(cookie_file, "r", encoding="utf-8") as f:
        raw_cookies = [line.strip() for line in f if line.strip()]
    if not raw_cookies:
        print("Không có cookie.")
        return

    print(f"Đã đọc {len(raw_cookies)} cookies.")

    # Lấy danh sách box từ cookie đầu tiên
    first_client = TClient(raw_cookies[0])
    groups = first_client.get_groups()
    if not groups:
        print("Không tìm thấy box.")
        return

    print("Danh sách box:")
    for idx, g in enumerate(groups, 1):
        print(f"  {idx}. {g['name']} (id: {g['id']})")

    choice = input("Nhập STT box hoặc ID box: ").strip()
    selected_box = None
    if choice.isdigit() and 1 <= int(choice) <= len(groups):
        selected_box = groups[int(choice) - 1]
    else:
        for g in groups:
            if g['id'] == choice:
                selected_box = g
                break
    if not selected_box:
        print("Box không hợp lệ.")
        return

    text_file = input("Nhập file ngôn : ").strip()
    with open(text_file, "r", encoding="utf-8") as f:
        message = f.read().strip()
    if not message:
        print("Nội dung rỗng.")
        return

    try:
        delay = float(input("Nhập delay : ").strip())
    except:
        delay = 10

    # Đã xoá bước xác nhận y/n, bắt đầu chạy ngay
    stop_event = threading.Event()
    threads = []

    def worker(client, box, content, delay, stop_event, idx):
        print(colored(f"Bản quyền tool by Ntan.","cyan"))
        count = 0
        last_gc = time.time()
        while not stop_event.is_set():
            try:
                client.send(box['id'], box['source_id'], content)
                count += 1
                now = datetime.datetime.now().strftime("%H:%M:%S")
                print(colored(f"[{now}] C{idx} Message sent successfully. #{count} ", "red"))
            except Exception as e:
                now = datetime.datetime.now().strftime("%H:%M:%S")
                print(colored(f"[{now}] C{idx} LỖI: {e}", "blue"))
            # Auto GC mỗi 30 giây
            if time.time() - last_gc >= 30:
                gc.collect()
                last_gc = time.time()
            time.sleep(delay)

    for i, ck in enumerate(raw_cookies, 1):
        try:
            cl = TClient(ck)
            t = threading.Thread(target=worker, args=(cl, selected_box, message, delay, stop_event, i), daemon=True)
            t.start()
            threads.append(t)
        except Exception as e:
            print(f"[Thread {i}] Khởi tạo thất bại: {e}")

    print("\nĐang chạy... Nhấn Enter để dừng.")
    try:
        input()
    except KeyboardInterrupt:
        pass
    stop_event.set()
    for t in threads:
        t.join(timeout=1)
    print("Đã dừng.")

if __name__ == "__main__":
    main()