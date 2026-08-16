import base64,datetime,json,os,random,re,sys,time,uuid,threading,gc,httpx
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.backends import default_backend
try:
    import psutil
    HAS_PSUTIL = True
except:
    HAS_PSUTIL = False

if hasattr(sys.stdout,"reconfigure"): sys.stdout.reconfigure(encoding="utf-8")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]
DEFAULT_USER_AGENT = USER_AGENTS[0]
IM_AID="1988"; SEND_MSG_FULL_URL="https://im-api-sg.tiktok.com/v1/message/send"
PASSWORD = "xt"
R="\033[91m";G="\033[92m";Y="\033[93m";B="\033[94m";M="\033[95m";C="\033[96m";W="\033[97m";BOLD="\033[1m";RST="\033[0m"
active_tasks=[]; task_lock=threading.Lock()

def auto_gc():
    while True:
        time.sleep(60); gc.collect()
        if HAS_PSUTIL:
            try:
                p=psutil.Process()
                if os.name=="nt":
                    import ctypes
                    ctypes.windll.kernel32.SetProcessWorkingSetSize(p._handle,-1,-1)
            except: pass
threading.Thread(target=auto_gc, daemon=True).start()

def ev(n):
    b=n&0xFFFFFFFFFFFFFFFF; o=bytearray()
    while b>=0x80: o.append((b&0x7F)|0x80); b>>=7
    o.append(b&0x7F); return bytes(o)
def et(fn,wt): return ev((fn<<3)|wt)
def pbv(fn,v): return b"" if not v else et(fn,0)+ev(v)
def pbb(fn,d): return b"" if not d else et(fn,2)+ev(len(d))+d
def pbs(fn,t): return b"" if not t else pbb(fn,t.encode("utf-8"))
def pbkv(k,v): return pbb(15,pbs(1,k)+pbs(2,v))

def dv(data,i):
    r=0; sh=0
    while True:
        if i>=len(data): raise IndexError
        b=data[i]; i+=1; r|=(b&0x7F)<<sh
        if not (b&0x80): break
        sh+=7
    return r,i

def parse(data):
    fields=[]; i=0; n=len(data)
    while i<n:
        try:
            tag,i=dv(data,i); fn=tag>>3; wt=tag&7
            if wt==0: v,i=dv(data,i); fields.append((fn,wt,v))
            elif wt==2: l,i=dv(data,i); fields.append((fn,wt,data[i:i+l])); i+=l
            elif wt==1: i+=8
            elif wt==5: i+=4
            else: break
        except: break
    return fields

def looks_like_title(s):
    if not s: return False
    s=s.replace("\u2068","").replace("\u2069","").strip()
    if len(s)<2 or len(s)>80 or s.isdigit(): return False
    bad=("aweType","client_message_id","source_aid","im_callback","avatar","group_type","deprecated","conv_set_notification","involved_user","was_minor_group","tt-ticket","Web-Sdk","device_id","msToken","verify_","tos-","http","AAA","BAA","LMS","s_v_web","MS4wLjAB")
    low=s.lower()
    if any(b.lower() in low for b in bad): return False
    if len(s)>28 and " " not in s and sum(c.isalnum() or c in "_-" for c in s)/max(len(s),1)>0.92:
        viet="àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"
        if not any(c in viet for c in low): return False
    return True

def extract_groups(data):
    cand=[]
    def walk(blob,d=0):
        if d>15 or not blob or len(blob)<3: return
        fields=parse(blob); ids=[]; titles=[]; typ=0; src=0
        for fn,wt,val in fields:
            if wt==0:
                if fn in(2,5,6) and val in(1,2,3): typ=val
                if fn==5 and isinstance(val,int) and val>10**13: src=val
            elif wt==2 and isinstance(val,bytes):
                try:
                    s=val.decode("utf-8",errors="ignore").strip(); sc=s.replace("\u2068","").replace("\u2069","").strip()
                    if s.isdigit() and 15<=len(s)<=22: ids.append(s)
                    elif looks_like_title(sc): titles.append(sc)
                except: pass
                walk(val,d+1)
        for cid in ids:
            title=titles[0] if titles else ""
            cand.append((cid,title,typ,src or int(cid)))
    walk(data)
    try:
        raw=data.decode("latin-1",errors="ignore")
        for m in re.finditer(r"(?<!\d)(\d{15,22})(?!\d)",raw):
            cand.append((m.group(1),"",0,int(m.group(1))))
    except: pass
    best={}
    for cid,title,typ,src in cand:
        if cid not in best: best[cid]={"id":cid,"source_id":src,"type":typ,"name":title or f"Box {cid[-8:]}"}
        else:
            if title and (best[cid]["name"].startswith("Box ") or len(title)>len(best[cid]["name"])): best[cid]["name"]=title
            if typ and not best[cid]["type"]: best[cid]["type"]=typ
    groups=list(best.values())
    groups.sort(key=lambda g:(0 if not g["name"].startswith("Box ") else 1,g["name"].lower()))
    return groups

def rand_bogus(): return "".join(random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(32))
def extract_cookie(cs,name):
    for p in cs.split(";"):
        kv=p.strip().split("=",1)
        if len(kv)==2 and kv[0].strip()==name: return kv[1].strip()
    return ""
def b64url(b): return base64.urlsafe_b64encode(b).decode().rstrip("=")
def gen_key(): return ec.generate_private_key(ec.SECP256R1(),default_backend())
def pub_point(priv):
    n=priv.public_key().public_numbers()
    return b"\x04"+n.x.to_bytes(32,"big")+n.y.to_bytes(32,"big")
def build_dpop(priv,htm,htu):
    n=priv.public_key().public_numbers()
    jwk={"crv":"P-256","kty":"EC","x":b64url(n.x.to_bytes(32,"big")),"y":b64url(n.y.to_bytes(32,"big"))}
    h=json.dumps({"alg":"ES256","typ":"dpop+jwt","jwk":jwk},separators=(",",":")).encode()
    p=json.dumps({"jti":b64url(os.urandom(32)),"htm":htm,"htu":htu,"iat":int(time.time())},separators=(",",":")).encode()
    si=f"{b64url(h)}.{b64url(p)}"
    sig=priv.sign(si.encode(),ec.ECDSA(hashes.SHA256())); r,s=decode_dss_signature(sig)
    return f"{si}.{b64url(r.to_bytes(32,'big')+s.to_bytes(32,'big'))}"

def build_meta(device_id,ms_token,verify_fp,pubkey,ua=None):
    ua=ua or DEFAULT_USER_AGENT
    pairs=[("aid",IM_AID),("app_name","tiktok_web"),("channel","web"),("device_platform","web_pc"),("device_id",device_id),("region","VN"),("priority_region","VN"),("os","windows"),("referer","https://www.tiktok.com/messages"),("root_referer",""),("cookie_enabled","true"),("screen_width","1920"),("screen_height","1080"),("browser_language","vi-VN"),("browser_platform","Win32"),("browser_name","Mozilla"),("browser_version",ua),("browser_online","true")]
    if verify_fp: pairs.append(("verifyFp",verify_fp))
    pairs.extend([("app_language","vi-VN"),("webcast_language","vi-VN"),("tz_name","Asia/Ho_Chi_Minh"),("is_page_visible","true"),("focus_state","true"),("is_fullscreen","false"),("history_len","2"),("user_is_login","true"),("data_collection_enabled","true"),("from_appID",IM_AID),("locale","vi-VN"),("tt-ticket-guard-public-key",pubkey),("tt-ticket-guard-client-data",""),("tt-ticket-guard-version","2"),("tt-ticket-guard-iteration-version","0"),("tt-ticket-guard-web-version","1"),("user_agent",ua)])
    if ms_token: pairs.append(("Web-Sdk-Ms-Token",ms_token))
    out=b""
    for k,v in pairs: out+=pbkv(k,v)
    return out

def get_device(cs):
    return extract_cookie(cs,"s_v_web_id") or "verify_msodzfdz_LM6w5Wfo_LJer_4bBr_8hqT_IC0ULF1Unn72"

class TClient:
    def __init__(self,cs):
        self.cookie_string=cs.strip()
        self.ua=random.choice(USER_AGENTS)
        h={"Cookie":self.cookie_string,"User-Agent":self.ua,"Accept-Language":"vi-VN,vi;q=0.9","Accept":"application/json, text/plain, */*","Referer":"https://www.tiktok.com/","Origin":"https://www.tiktok.com"}
        self.r=httpx.Client(base_url="https://www.tiktok.com",headers=h,timeout=20,follow_redirects=True)
        self.ia=httpx.Client(base_url="https://im-api-sg.tiktok.com",headers=h,timeout=20,follow_redirects=True)
        self.last_error=0
    def _refresh(self):
        self.ua=random.choice(USER_AGENTS)
        h={"Cookie":self.cookie_string,"User-Agent":self.ua,"Accept-Language":"vi-VN,vi;q=0.9","Accept":"application/json, text/plain, */*","Referer":"https://www.tiktok.com/","Origin":"https://www.tiktok.com"}
        self.r.headers.update(h); self.ia.headers.update(h)
    def _req(self,method,url,**kw):
        for attempt in range(5):
            try:
                if self.last_error and time.time()-self.last_error<3: time.sleep(3)
                resp=getattr(self.r if "tiktok.com" in url and "im-api" not in url else self.ia,method.lower())(url,**kw)
                if resp.status_code in (403, 429):
                    self._refresh(); self.last_error=time.time()
                    print(f"{Y}Retry {attempt+1}/5...{RST}")
                    time.sleep(1.5 ** attempt)
                    if attempt<4: continue
                if resp.status_code == 200:
                    self.last_error=0
                    return resp
                return resp
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout):
                self._refresh(); self.last_error=time.time()
                if attempt<4: continue
                raise
        raise RuntimeError("Max retry")
    def get_self(self):
        for p in ["/tiktok/v1/im/user/profile/","/api/user/detail/?aid=1988"]:
            try:
                r=self._req("GET",p)
                if r.status_code==200:
                    d=r.json()
                    if d.get("status_code",-1)==0 or "user" in d or "userInfo" in d:
                        u=d.get("user") or d.get("userInfo",{}).get("user") or {}
                        uid=str(u.get("uid") or u.get("id") or "")
                        if not uid:
                            ms=extract_cookie(self.cookie_string,"multi_sids")
                            if ms and "%3A" in ms: uid=ms.split("%3A")[0].strip()
                            elif ms and ":" in ms: uid=ms.split(":")[0].strip()
                            else: uid=extract_cookie(self.cookie_string,"uid_tt") or extract_cookie(self.cookie_string,"living_user_id") or ""
                        if uid or u.get("unique_id","")!="user":
                            return {"user_id":uid,"unique_id":str(u.get("unique_id") or u.get("uniqueId") or "user"),"nickname":str(u.get("nickname") or "User")}
            except: pass
        uid=extract_cookie(self.cookie_string,"uid_tt") or extract_cookie(self.cookie_string,"living_user_id") or ""
        ms=extract_cookie(self.cookie_string,"multi_sids")
        if ms and "%3A" in ms: uid=ms.split("%3A")[0].strip()
        if not uid: raise RuntimeError("Cookie het han")
        return {"user_id":uid,"unique_id":"user","nickname":"User"}
    def get_groups(self):
        dev=get_device(self.cookie_string); ms=extract_cookie(self.cookie_string,"msToken"); vf=extract_cookie(self.cookie_string,"s_v_web_id")
        payload=(et(1,0)+ev(203)+et(2,0)+ev(10002)+pbs(3,"1.6.0")+et(4,2)+ev(0)+et(5,0)+ev(3)+et(6,0)+ev(1)+pbb(8,b"\xda\x0c\x02\x08\x00")+pbs(9,dev)+pbs(11,"web")+build_meta(dev,ms,vf,"")+et(18,0)+ev(1)+pbb(100,pbb(1,et(1,0)+ev(0))))
        h={"Accept":"application/x-protobuf","Content-Type":"application/x-protobuf","Referer":"https://www.tiktok.com/messages"}
        r=self._req("POST","https://im-api-sg.tiktok.com/v2/message/get_by_user_init",headers=h,params={"aid":IM_AID,"version_code":"1.0.0","app_name":"tiktok_web","device_platform":"web_pc","msToken":ms,"X-Bogus":rand_bogus()},content=payload)
        if r.is_error: raise RuntimeError(f"HTTP {r.status_code}")
        return extract_groups(r.content)
    def send(self,cid,src,text):
        dev=get_device(self.cookie_string); ms=extract_cookie(self.cookie_string,"msToken"); vf=extract_cookie(self.cookie_string,"s_v_web_id")
        priv=gen_key(); pub=base64.b64encode(pub_point(priv)).decode(); dpop=build_dpop(priv,"POST",SEND_MSG_FULL_URL); cmid=str(uuid.uuid4())
        t1=pbb(5,pbs(1,"s:mentioned_users")); t2=pbb(5,pbs(1,"s:client_message_id")+pbb(2,cmid.encode()))
        body=(pbs(1,cid)+pbv(2,2)+pbv(3,src)+pbb(4,json.dumps({"aweType":0,"text":text}).encode())+t1+t2+pbv(6,7)+pbs(7,"deprecated")+pbs(8,cmid))
        payload=(et(1,0)+ev(100)+et(2,0)+ev(10014)+pbs(3,"1.6.0")+et(4,2)+ev(0)+et(5,0)+ev(3)+et(6,0)+ev(1)+et(7,2)+ev(0)+pbb(8,pbb(100,body))+pbs(9,dev)+pbs(11,"web")+build_meta(dev,ms,vf,pub,self.ua)+et(18,0)+ev(1))
        h={"Accept":"application/x-protobuf","Content-Type":"application/x-protobuf","Cache-Control":"no-cache","Origin":"https://www.tiktok.com","Referer":"https://www.tiktok.com/messages","tt-ticket-guard-iteration-version":"0","tt-ticket-guard-public-key":pub,"tt-ticket-guard-version":"2","tt-ticket-guard-web-version":"1","DPoP":dpop}
        r=self._req("POST",SEND_MSG_FULL_URL,headers=h,params={"aid":IM_AID,"version_code":"1.0.0","app_name":"tiktok_web","device_platform":"web_pc","ztca-version":"1","ztca-dpop":dpop,"msToken":ms,"X-Bogus":rand_bogus()},content=payload)
        if r.is_error: raise RuntimeError(f"API {r.status_code}")
        return cmid
    def send_typing(self,cid,src):
        dev=get_device(self.cookie_string); ms=extract_cookie(self.cookie_string,"msToken"); vf=extract_cookie(self.cookie_string,"s_v_web_id")
        priv=gen_key(); pub=base64.b64encode(pub_point(priv)).decode()
        url="https://im-api-sg.tiktok.com/v1/message/typing"
        dpop=build_dpop(priv,"POST",url)
        inner=(pbs(1,cid)+pbv(2,2)+pbv(3,src)+pbv(4,1))
        payload=(et(1,0)+ev(130)+et(2,0)+ev(10014)+pbs(3,"1.6.0")+et(4,2)+ev(0)+et(5,0)+ev(3)+et(6,0)+ev(1)+pbb(8,pbb(100,inner))+pbs(9,dev)+pbs(11,"web")+build_meta(dev,ms,vf,pub,self.ua)+et(18,0)+ev(1))
        h={"Accept":"application/x-protobuf","Content-Type":"application/x-protobuf","tt-ticket-guard-public-key":pub,"tt-ticket-guard-version":"2","tt-ticket-guard-web-version":"1","DPoP":dpop}
        r=self._req("POST",url,headers=h,params={"aid":IM_AID,"version_code":"1.0.0","app_name":"tiktok_web","device_platform":"web_pc","msToken":ms,"X-Bogus":rand_bogus(),"ztca-dpop":dpop},content=payload)
        return r.status_code==200
    def update_group(self,cid,src,name,desc=""):
        dev=get_device(self.cookie_string); ms=extract_cookie(self.cookie_string,"msToken"); vf=extract_cookie(self.cookie_string,"s_v_web_id")
        priv=gen_key(); pub=base64.b64encode(pub_point(priv)).decode()
        url="https://im-api-sg.tiktok.com/v1/conversation/update"
        dpop=build_dpop(priv,"POST",url)
        inner=(pbs(1,cid)+pbv(2,2)+pbv(3,src)+pbs(4,name[:50])+pbs(5,desc[:200]))
        payload=(et(1,0)+ev(120)+et(2,0)+ev(10014)+pbs(3,"1.6.0")+et(4,2)+ev(0)+et(5,0)+ev(3)+et(6,0)+ev(1)+pbb(8,pbb(100,inner))+pbs(9,dev)+pbs(11,"web")+build_meta(dev,ms,vf,pub,self.ua)+et(18,0)+ev(1))
        h={"Accept":"application/x-protobuf","Content-Type":"application/x-protobuf","tt-ticket-guard-public-key":pub,"tt-ticket-guard-version":"2","tt-ticket-guard-web-version":"1","DPoP":dpop}
        r=self._req("POST",url,headers=h,params={"aid":IM_AID,"version_code":"1.0.0","app_name":"tiktok_web","device_platform":"web_pc","msToken":ms,"X-Bogus":rand_bogus(),"ztca-dpop":dpop},content=payload)
        return r.status_code==200

def clear(): os.system("cls" if os.name=="nt" else "clear")
def banner():
    print(f"{C}{BOLD}\n╔═══════════════════════════════════════╗")
    print("║   TOOL SPAM TIKTOK - TREO/NHAY/NAME  ║")
    print("║        NTan + AI                     ║")
    print("╚═══════════════════════════════════════╝\n{RST}")

def get_cookie_input():
    print(f"{Y}Nhap cookie (moi dong 1, 'done' ket thuc):{RST}")
    c=[]
    while True:
        try:
            l=input(f"{C}> {RST}").strip()
            if l.lower()=="done": break
            if l: c.append(l)
        except: break
    return c[0] if c else None

def select_groups(client):
    try:
        groups=client.get_groups()
    except Exception as e:
        print(f"{R}Loi quet box: {e}{RST}")
        return None
    if not groups:
        print(f"{R}Khong tim thay box{RST}")
        return None
    for i,g in enumerate(groups,1): print(f"  {Y}{i}.{RST} {g['name']}")
    sel=input(f"{Y}Chon box (0 bo qua): {RST}").strip()
    if sel=="0": return None
    selected=[]
    try:
        for p in sel.split(","):
            s=int(p.strip())
            if 1<=s<=len(groups): selected.append(groups[s-1])
    except: pass
    if not selected: return None
    seen=set(); uniq=[]
    for g in selected:
        if g["id"] not in seen: seen.add(g["id"]); uniq.append(g)
    return uniq

class Task:
    def __init__(self,tid,client,groups,mode,content,lines,delay,name,filepath=""):
        self.tid=tid; self.client=client; self.groups=groups; self.mode=mode
        self.content=content; self.lines=lines; self.delay=delay; self.name=name
        self.filepath=filepath; self.running=True; self.count=0; self.li=0; self.gi=0
        self.typing=(mode==2)
    def run(self):
        self.thread=threading.Thread(target=self._work,daemon=True); self.thread.start()
    def _work(self):
        try:
            while self.running:
                g=self.groups[self.gi]; self.gi=(self.gi+1)%len(self.groups)
                if self.mode==3:
                    name=self.lines[0] if self.lines else "Renamed"
                    desc=self.lines[1] if len(self.lines)>1 else ""
                    try:
                        self.client.update_group(g["id"],g["source_id"],name,desc)
                        with task_lock: print(f"{C}[{datetime.datetime.now().strftime('%H:%M:%S')}]{RST} T{self.tid} NAME [{g['name'][:12]}] -> {name[:20]}")
                    except Exception as e:
                        with task_lock: print(f"         {R}NAME ERR: {e}{RST}")
                    self.count+=1
                    time.sleep(self.delay)
                    continue
                if self.mode==2 and self.typing:
                    try: self.client.send_typing(g["id"],g["source_id"])
                    except: pass
                text=self.content if self.mode==1 else self.lines[self.li]; self.li=(self.li+1)%len(self.lines) if self.mode!=1 else 0
                self.count+=1
                with task_lock:
                    print(f"{C}[{datetime.datetime.now().strftime('%H:%M:%S')}]{RST} T{self.tid} @{self.name} #{self.count} [{g['name'][:12]}] {text[:25]}...")
                try:
                    self.client.send(g["id"],g["source_id"],text)
                    print(f"         {G}OK{RST}")
                except Exception as e:
                    print(f"         {R}ERR: {e}{RST}")
                time.sleep(self.delay)
        except: pass
    def stop(self): self.running=False
    def update_file(self,new_content,new_lines):
        if self.mode==1: self.content=new_content
        else: self.lines=new_lines
    def update_delay(self,d): self.delay=d

def main():
    try: os.nice(10)
    except: pass
    clear(); banner()
    try:
        mk=input(f"{Y}Pass: {RST}").strip()
        if mk!=PASSWORD: print(f"{R}Sai pass{RST}"); return
    except: return
    tasks=[]; tid=0
    while True:
        clear(); banner()
        print(f"{G}Tasks: {len(tasks)} running{RST}\n")
        print(f"{B}=== MENU ==={RST}")
        print(f"  {Y}1{RST} TREO")
        print(f"  {Y}2{RST} NHAY (co typing)")
        print(f"  {Y}3{RST} DOI TEN BOX")
        print(f"  {Y}add{RST} Tao task moi voi cookie khac")
        print(f"  {Y}tab{RST} Liet ke task")
        print(f"  {Y}stop [stt]{RST} Dung task (vd: stop 1,2)")
        print(f"  {Y}file [stt]{RST} Doi file spam (vd: file 1,2)")
        print(f"  {Y}delay [stt]{RST} Doi delay (vd: delay 1,2)")
        print(f"  {R}0{RST} Thoat")
        try:
            cmd=input(f"{Y}> {RST}").strip().lower()
        except: break
        if cmd=="0": break
        if cmd=="tab":
            if not tasks: print(f"{Y}Khong co task{RST}")
            else:
                print(f"{B}=== TASK ==={RST}")
                for i,t in enumerate(tasks,1):
                    mode=["TREO","NHAY","NAME"][t.mode-1] if t.mode<=3 else "?"
                    print(f"  {Y}{i}.{RST} {mode} @{t.name} count:{t.count} delay:{t.delay}s file:{t.filepath or 'N/A'} {'RUN' if t.running else 'STOP'}")
            time.sleep(1); continue
        if cmd.startswith("stop "):
            try:
                for s in cmd.split()[1].split(","):
                    s=int(s.strip())
                    if 1<=s<=len(tasks): tasks[s-1].stop(); print(f"{G}Stopped {s}{RST}")
            except: print(f"{R}stop 1,2{RST}")
            time.sleep(1); continue
        if cmd.startswith("file "):
            try:
                ids=[int(x.strip()) for x in cmd.split()[1].split(",")]
                fpath=input(f"{Y}File moi: {RST}").strip()
                if not os.path.exists(fpath): print(f"{R}Khong ton tai{RST}"); continue
                raw=open(fpath,"r",encoding="utf-8").read()
                for s in ids:
                    if 1<=s<=len(tasks):
                        t=tasks[s-1]
                        if t.mode==1: t.update_file(raw.strip(),None)
                        else: t.update_file(None,[l.strip() for l in raw.splitlines() if l.strip()])
                        t.filepath=fpath
                print(f"{G}Updated file{RST}")
            except: print(f"{R}file 1,2{RST}")
            time.sleep(1); continue
        if cmd.startswith("delay "):
            try:
                ids=[int(x.strip()) for x in cmd.split()[1].split(",")]
                nd=float(input(f"{Y}Delay moi: {RST}").strip())
                for s in ids:
                    if 1<=s<=len(tasks): tasks[s-1].update_delay(nd)
                print(f"{G}Updated delay{RST}")
            except: print(f"{R}delay 1,2{RST}")
            time.sleep(1); continue
        if cmd in ("add","1","2","3"):
            ck=get_cookie_input()
            if not ck: continue
            cl=TClient(ck)
            try:
                info=cl.get_self(); print(f"{G}OK: @{info['unique_id']}{RST}")
            except Exception as e: print(f"{R}FAIL: {e}{RST}"); continue
            try: groups=select_groups(cl)
            except Exception as e: print(f"{R}Group err: {e}{RST}"); continue
            if not groups: continue
            if cmd=="add":
                print(f"{B}1.TREO 2.NHAY 3.NAME{RST}")
                mode=int(input(f"{Y}Chon: {RST}").strip() or "1")
            else:
                mode=int(cmd)
            fpath=input(f"{Y}File: {RST}").strip()
            if not os.path.exists(fpath): print(f"{R}Khong ton tai{RST}"); continue
            raw=open(fpath,"r",encoding="utf-8").read()
            content=None; lines=None
            if mode==1: content=raw.strip()
            elif mode==2: lines=[l.strip() for l in raw.splitlines() if l.strip()]
            else: lines=[l.strip() for l in raw.splitlines() if l.strip()]
            if (mode==1 and not content) or (mode!=1 and not lines): print(f"{R}File rong{RST}"); continue
            delay=float(input(f"{Y}Delay: {RST}").strip() or "5")
            tid+=1; task=Task(tid,cl,groups,mode,content,lines,delay,info["unique_id"],fpath)
            task.run(); tasks.append(task); print(f"{G}Task {tid} started{RST}")
            time.sleep(1); continue
    print(f"{Y}Thoat. Task van song.{RST}")

if __name__=="__main__": main()