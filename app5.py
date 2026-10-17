#!/usr/bin/env python3
"""
KAMOD WILL RISE — Forge + Activator Dashboard (FIXED v8 - Selective Activation)
Owner  : @kamod_codex
Channel: @kamod_codex
"""

import os, sys, json, time, random, string, hashlib, hmac, uuid, asyncio, socket, ipaddress
import threading
from concurrent.futures import ThreadPoolExecutor, wait as _wait, FIRST_COMPLETED as _FC
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import requests, urllib3
from requests.adapters import HTTPAdapter
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

try:
    import blackboxprotobuf
except ImportError:
    os.system("pip install blackboxprotobuf -q")
    import blackboxprotobuf

try:
    import httpx
except ImportError:
    os.system("pip install httpx -q")
    import httpx

try:
    import MASTERTeam_pb2
except ImportError:
    print("❌ ERROR: MASTERTeam_pb2.py not found in directory!")
    sys.exit(1)

try:
    from protobuf_decoder.protobuf_decoder import Parser
except ImportError:
    os.system("pip install protobuf-decoder -q")
    from protobuf_decoder.protobuf_decoder import Parser

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ═══════════════════════════════════════════════════════════
#  PERSISTENT STORAGE & BATCH MANAGEMENT
# ═══════════════════════════════════════════════════════════
GEN_TOTAL_FILE = "accounts.json"
ACT_TOTAL_FILE = "activated.json"
STORAGE_LOCK = threading.Lock()

def _load_storage(path):
    if not os.path.exists(path): return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception: return []

def _save_storage(path, data):
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception as e: print(f"[STORAGE] save error {path}: {e}")

def get_next_batch_num(prefix):
    max_num = 0
    for f in os.listdir('.'):
        if f.startswith(prefix) and f.endswith('.json'):
            try:
                num = int(f.replace(prefix, '').replace('.json', ''))
                if num > max_num: max_num = num
            except ValueError: continue
    return max_num + 1

def append_generated(acc, batch_num):
    with STORAGE_LOCK:
        batch_file = f"account_batch_{batch_num}.json"
        b_data = _load_storage(batch_file)
        b_data.append(acc)
        _save_storage(batch_file, b_data)
        m_data = _load_storage(GEN_TOTAL_FILE)
        m_data.append(acc)
        _save_storage(GEN_TOTAL_FILE, m_data)

def append_activated(acc, batch_num):
    with STORAGE_LOCK:
        batch_file = f"activate_batch_{batch_num}.json"
        b_data = _load_storage(batch_file)
        b_data.append(acc)
        _save_storage(batch_file, b_data)
        m_data = _load_storage(ACT_TOTAL_FILE)
        m_data.append(acc)
        _save_storage(ACT_TOTAL_FILE, m_data)

ALL_ACCOUNTS = _load_storage(GEN_TOTAL_FILE)
ALL_ACTIVATED = _load_storage(ACT_TOTAL_FILE)
ALL_FAILED = []


# ═══════════════════════════════════════════════════════════
#  IP ROTATOR
# ═══════════════════════════════════════════════════════════
class IPRotator:
    REGION_IP_CIDRS = {
        "BD":  ["27.147.128.0/17","37.111.192.0/19","49.0.32.0/20","59.152.96.0/20","114.130.0.0/17","115.127.0.0/17","119.30.32.0/20","123.49.0.0/18","103.220.220.0/22","103.108.140.0/22","103.242.20.0/22"],
        "IND": ["1.6.0.0/15","1.38.0.0/15","14.96.0.0/15","27.4.0.0/14","27.56.0.0/13","49.36.0.0/14","103.25.12.0/22","103.56.12.0/22","115.99.0.0/16"],
        "ID":  ["36.64.0.0/11","101.255.0.0/16","103.10.60.0/22","114.120.0.0/13"],
        "TH":  ["1.46.0.0/15","27.55.0.0/16","49.228.0.0/15","101.108.0.0/15"],
        "VN":  ["1.52.0.0/14","14.160.0.0/11","27.64.0.0/12","113.160.0.0/12"],
        "PK":  ["39.32.0.0/11","111.68.96.0/19","182.176.0.0/12"],
        "ME":  ["2.88.0.0/13","5.100.0.0/14","31.166.0.0/15","37.104.0.0/13"],
        "BR":  ["177.0.0.0/13","186.192.0.0/12","189.0.0.0/11","200.96.0.0/12"],
        "EU":  ["2.16.0.0/12","5.144.0.0/14","31.40.0.0/14","46.16.0.0/14"],
        "CIS": ["2.92.0.0/14","5.136.0.0/13","31.128.0.0/12","46.0.0.0/12"],
        "NA":  ["3.0.0.0/9","8.0.0.0/12","12.0.0.0/10","24.0.0.0/10"],
        "SAC": ["186.0.0.0/10","190.0.0.0/11","200.0.0.0/11"],
        "TW":  ["1.160.0.0/12","36.224.0.0/12","114.24.0.0/12","118.160.0.0/12"],
    }
    _cache = {}
    _cache_lock = threading.Lock()

    @classmethod
    def get_random_ip(cls, region="IND"):
        region = (region or "IND").upper()
        with cls._cache_lock:
            if region not in cls._cache:
                cidrs = cls.REGION_IP_CIDRS.get(region)
                if not cidrs: cls._cache[region] = []
                else:
                    hosts = []
                    for cidr in cidrs:
                        try:
                            net = ipaddress.ip_network(cidr, strict=False)
                            total = 2 ** (32 - net.prefixlen)
                            if total > 5000:
                                for _ in range(2000): hosts.append(str(net.network_address + random.randint(1, total - 2)))
                            else: hosts.extend([str(ip) for ip in net.hosts()])
                        except Exception: continue
                    cls._cache[region] = hosts
            pool = cls._cache.get(region) or []
            if not pool: return f"{random.randint(103,223)}.{random.randint(10,250)}.{random.randint(10,250)}.{random.randint(10,250)}"
            return random.choice(pool)


# ═══════════════════════════════════════════════════════════
#  GEN URLs & CONSTANTS
# ═══════════════════════════════════════════════════════════
URL_GUEST_REGISTER = "https://ffmconnect.live.gop.garenanow.com/api/v2/oauth/guest:register"
URL_TOKEN_GRANT    = "https://ffmconnect.live.gop.garenanow.com/api/v2/oauth/guest/token:grant"
URL_MAJOR_LOGIN    = "https://loginbp.ppmainecoonghj.com/MajorLogin"
URL_MAJOR_REGISTER = "https://loginbp.ppmainecoonghj.com/MajorRegister"
URL_NEWBIE_CHOICE  = "https://loginbp.ppmainecoonghj.com/ChooseNewbieChoice"

MAIN_KEY = bytes.fromhex('32656534343831396539623435393838343531343130363762323831363231383734643064356437616639643866376530306331653534373135623764316533')
AES_KEY = bytes([89,103,38,116,99,37,68,69,117,104,54,37,90,99,94,56])
AES_IV  = bytes([54,111,121,90,68,114,50,50,69,51,121,99,104,106,77,37])
CLIENT_SECRET = "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3"
APP_ID        = 100067
RELEASE_VER   = "OB55"
GAME_VERSION  = "2.132.4"

HTTP_TIMEOUT  = (5, 10)
FAIL_WAIT     = 0.2
MAX_RETRIES   = 3
POOL_CONN     = 100
POOL_MAX      = 200
PACE_PER_PROXY = 0.15
PROXY_COOLDOWN_429 = 20
PROXY_COOLDOWN_503 = 45
MAX_COUNT = 100000

FREE_PROXY_SOURCES = ["https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt","https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt","https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt","https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt"]
PROXY_VALIDATE_URL     = "https://ffmconnect.live.gop.garenanow.com/"
PROXY_VALIDATE_WORKERS = 50
PROXY_FETCH_INTERVAL   = 600
PROXY_MIN_POOL         = 15

PROXY_POOL = []
PROXY_POOL_LOCK = threading.Lock()
PROXY_LAST_FETCH = 0.0
PROXY_FETCH_RUNNING = False

DEVICES = [
    ("Asus ASUS_AI2501_B", "Android OS 12 / API-31 (SP1A.210812.016.C2/user.dxu.20260701.180839)", "Adreno (TM) 640", "OpenGL ES 3.2"),
    ("Redmi Note 12 Pro",  "Android OS 13 / API-33 (TP1A.220624.014)", "Adreno (TM) 618", "OpenGL ES 3.2"),
    ("Samsung SM-M135F",   "Android OS 13 / API-33 (TP1A.220624.014)", "Mali-G68", "OpenGL ES 3.2"),
    ("Realme RMX3630",     "Android OS 12 / API-31 (SP1A.210812.016)", "Adreno (TM) 610", "OpenGL ES 3.2"),
    ("Vivo V2149",         "Android OS 13 / API-33 (TP1A.220624.014)", "Adreno (TM) 642L", "OpenGL ES 3.2"),
    ("OnePlus CPH2411",    "Android OS 13 / API-33 (TP1A.220624.014)", "Adreno (TM) 730", "OpenGL ES 3.2"),
]

CONFIG = {
    "target": 100, "threads": 15, "nick_prefix": "MasteR~", "nick_max_len": 12,
    "use_proxy": False, "proxy_file": "working_proxies.txt", "region": "IND",
}

COUNTER_LOCK = threading.Lock()
PROXY_LOCK   = threading.Lock()
PACE_LOCK    = {}
LAST_PACE    = {}
PROXIES = [None]
PROXY_COOLDOWN = {}
CURRENT_PROXY = None
STATE_LOCK = threading.Lock()
STOP_GEN = threading.Event()
STOP_ACT = threading.Event()

STATE = {"running": False, "target": 0, "started_at": 0, "finished_at": 0, "workers": 0, "region": "IND", "name_prefix": "MasteR~", "last_error": None, "failed": 0, "stopped": False, "session_start_count": 0, "batch_num": 0}
ACT_STATE = {"running": False, "target": 0, "started_at": 0, "finished_at": 0, "workers": 0, "last_error": None, "active": 0, "failed": 0, "stopped": False, "batch_num": 0}

# ═══════════════════════════════════════════════════════════
#  PROXY & HELPERS
# ═══════════════════════════════════════════════════════════
def _validate_proxy(proxy_str):
    try:
        p = {"http": f"http://{proxy_str}", "https": f"http://{proxy_str}"}
        r = requests.get(PROXY_VALIDATE_URL, proxies=p, timeout=(4, 6), verify=False)
        if r.status_code in (200, 401, 403, 404): return proxy_str
    except Exception: pass
    return None

def _fetch_free_proxies():
    global PROXY_POOL, PROXY_LAST_FETCH, PROXY_FETCH_RUNNING
    with PROXY_POOL_LOCK:
        if PROXY_FETCH_RUNNING: return
        PROXY_FETCH_RUNNING = True
    raw = set()
    try:
        for url in FREE_PROXY_SOURCES:
            try:
                r = requests.get(url, timeout=10, verify=False)
                if r.status_code == 200:
                    for line in r.text.splitlines():
                        line = line.strip()
                        if not line: continue
                        if "://" in line: line = line.split("://", 1)[1]
                        parts = line.split(":")
                        if len(parts) == 2:
                            ip, port = parts
                            if ip.count(".") == 3 and port.isdigit(): raw.add(f"{ip}:{port}")
            except Exception: pass
        raw_list = list(raw)
        good = []
        with ThreadPoolExecutor(max_workers=PROXY_VALIDATE_WORKERS) as ex:
            for res in ex.map(_validate_proxy, raw_list):
                if res: good.append(res)
        with PROXY_POOL_LOCK:
            PROXY_POOL = good
            PROXY_LAST_FETCH = time.time()
        if CONFIG.get("use_proxy"): _rebuild_proxies_from_pool()
    finally:
        with PROXY_POOL_LOCK: PROXY_FETCH_RUNNING = False

def _rebuild_proxies_from_pool():
    global PROXIES, CURRENT_PROXY
    with PROXY_POOL_LOCK: pool = list(PROXY_POOL)
    if not pool: return
    PROXIES = [{"http": f"http://{p}", "https": f"http://{p}"} for p in pool]
    CURRENT_PROXY = PROXIES[0]

def _proxy_watchdog():
    global PROXY_LAST_FETCH
    while True:
        try:
            now = time.time()
            with PROXY_POOL_LOCK: pool_sz = len(PROXY_POOL)
            need = (now - PROXY_LAST_FETCH > PROXY_FETCH_INTERVAL) or (pool_sz < PROXY_MIN_POOL)
            if need and not PROXY_FETCH_RUNNING:
                _fetch_free_proxies()
        except Exception: pass
        time.sleep(60)

def load_proxies():
    global PROXIES, CURRENT_PROXY
    pf = CONFIG.get("proxy_file", "working_proxies.txt")
    file_proxies = []
    if os.path.exists(pf):
        try:
            with open(pf, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"): file_proxies.append(line)
        except Exception: pass
    with PROXY_POOL_LOCK: pool = list(PROXY_POOL)
    all_p = file_proxies + pool
    if not CONFIG.get("use_proxy") or not all_p:
        PROXIES = [None]
        CURRENT_PROXY = None
        return
    PROXIES = [{"http": f"http://{p}", "https": f"http://{p}"} for p in all_p]
    CURRENT_PROXY = PROXIES[0]

def _pk(p): return "__direct__" if p is None else p.get("http", "?")

def get_proxy():
    global CURRENT_PROXY
    if len(PROXIES) <= 1: return PROXIES[0] if PROXIES else None
    if len(PROXIES) >= 5:
        now = time.time()
        with PROXY_LOCK: healthy = [p for p in PROXIES if now >= PROXY_COOLDOWN.get(_pk(p), 0)]
        if healthy: return random.choice(healthy)
        return random.choice(PROXIES)
    if CURRENT_PROXY is not None:
        with PROXY_LOCK:
            if time.time() >= PROXY_COOLDOWN.get(_pk(CURRENT_PROXY), 0): return CURRENT_PROXY
    now = time.time()
    with PROXY_LOCK: healthy = [p for p in PROXIES if now >= PROXY_COOLDOWN.get(_pk(p), 0)]
    return random.choice(healthy) if healthy else random.choice(PROXIES)

def cooldown(p, sec):
    if p is None: return
    with PROXY_LOCK:
        k = _pk(p)
        PROXY_COOLDOWN[k] = max(PROXY_COOLDOWN.get(k, 0), time.time() + sec)

def pace_proxy(p):
    k = _pk(p)
    if k not in PACE_LOCK: PACE_LOCK[k] = threading.Lock()
    with PACE_LOCK[k]:
        now = time.time()
        el = now - LAST_PACE.get(k, 0)
        if el < PACE_PER_PROXY: time.sleep(PACE_PER_PROXY - el)
        LAST_PACE[k] = time.time()

def gen_password():
    return hashlib.sha256(''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32)).encode()).hexdigest().upper()

def gen_nickname():
    prefix = CONFIG["nick_prefix"]
    max_len = CONFIG["nick_max_len"]
    avail = max_len - len(prefix)
    if avail < 1: return prefix[:max_len].encode()
    digits = "".join(random.choice("0123456789") for _ in range(avail))
    return f"{prefix}{digits}".encode()

def enc_aes(data):
    return AES.new(AES_KEY, AES.MODE_CBC, AES_IV).encrypt(pad(data, AES.block_size))

def encode_f14(s):
    ks = [0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30]
    return bytes(ord(c) ^ ks[i % len(ks)] for i, c in enumerate(s))

# ═══════════════════════════════════════════════════════════
#  TYPEDEFS
# ═══════════════════════════════════════════════════════════
def _tf(t): return {'type': t, 'name': ''}

typedef_login = {'3':_tf('bytes'),'4':_tf('bytes'),'5':_tf('int'),'7':_tf('bytes'),'8':_tf('bytes'),'9':_tf('bytes'),'10':_tf('bytes'),'11':_tf('bytes'),'12':_tf('int'),'13':_tf('int'),'14':_tf('bytes'),'15':_tf('bytes'),'16':_tf('int'),'17':_tf('bytes'),'18':_tf('bytes'),'19':_tf('bytes'),'20':_tf('bytes'),'21':_tf('bytes'),'22':_tf('bytes'),'23':_tf('bytes'),'24':_tf('bytes'),'25':_tf('bytes'),'26':_tf('bytes'),'29':_tf('bytes'),'30':_tf('int'),'41':_tf('bytes'),'42':_tf('bytes'),'57':_tf('bytes'),'60':_tf('int'),'61':_tf('int'),'62':_tf('int'),'63':_tf('int'),'64':_tf('int'),'65':_tf('int'),'66':_tf('int'),'67':_tf('int'),'73':_tf('int'),'74':_tf('bytes'),'76':_tf('int'),'77':_tf('bytes'),'78':_tf('int'),'79':_tf('int'),'81':_tf('bytes'),'83':_tf('bytes'),'85':_tf('int'),'86':_tf('bytes'),'87':_tf('int'),'88':_tf('int'),'92':_tf('int'),'93':_tf('bytes'),'94':_tf('bytes'),'96':_tf('bytes'),'97':_tf('int'),'98':_tf('int'),'99':_tf('bytes'),'100':_tf('bytes'),'102':_tf('bytes'),'104':_tf('int'),'105':_tf('int'),'106':_tf('bytes'),'107':_tf('bytes')}
typedef_reg = {'1':_tf('bytes'),'2':_tf('bytes'),'3':_tf('bytes'),'5':_tf('int'),'6':_tf('int'),'7':_tf('int'),'13':_tf('int'),'14':_tf('bytes'),'15':_tf('bytes'),'16':_tf('int'),'20':_tf('bytes'),'21':_tf('int'),'22':_tf('bytes')}
typedef_newbie = {'1':_tf('int'),'2':_tf('int'),'3':_tf('int')}

FIELD_22 = bytes.fromhex("4747524501010100620200001052aa0d669c6a368f08338060d2ee0690053af84a41edcd3558556ec10f24f46c93ac64ca41a16732c46a2cb071246a79b8929032f9e1b6f4ef331bd53cabf29b09b97349a46e9863c0314e1a0d80819fef8aabf03876b3d037db354a7ccb5c1bce96411fb3753f6f50e44c69c4ed617fa30efb8ffc0517ff2f636739be1f304d999cfd6fd48bf69454199794c3dc88f55a4bdbd66534d5a061359cdfd1fb680cd37918df9fdb3cf7d80067b0a3506c90063cf62b2ccec11e23913a2fd7c4ef091331967bb518a5ad1e551146b90821be800883abadde39d6c80a5d798611466c748f075481806c5842ce45e6bd4e3368ec08fe2ec41ceb880cd86249eb71693f79f0bccf9e590c3fae12519fe08c7a1905d0927690109e0df28574bb14847225db1a59230e6662ed7730e15ff9a6c815cb41b420edeada735a4b03e181037c37c2c850257311df2f07b0a56e759372cbd0268e3f13a292ee4373e38ab5096e0342a5e0d7fec6da2bbc265d74baadd2b24ee4f74862f82c21d6694bac53f8ce80312a30068a6276a641c19b11d0305c6fe2f531ac7de578b29f543697f5c73663e6f23aa15277b6122dcd4d4171e38f9ac0b173f39c58416a16c5c1f4a35acd065ce78f449cf538a249339e763272d458e4ed86c976591a9c066b3a37111e44091eb6b5a795249f3e5145db022a6055f2cc675936391312f688f89627845df222a91156555225be36f9714a0ba50246d0f003bda3c9c1292ab73b4f79635ddd023218eda93a302d79e023404c14396544a930b98ed54771aca7fec10d095587685b473e81a9619764fad9256529dcd6e911f4f4629612287d4ee3ec5389f6ec4ec020b0e2aac017232a9197be9e46239ce690fe5d4872b2e98e651510c971667f3aca8b59f3e9d50e43")

HEADERS_MSDK = {"User-Agent": "GarenaMSDK/4.0.44(ASUS_AI2501_B ;Android 12;en;US;app 2.132.1 2019118525;)", "Content-Type": "application/json; charset=utf-8", "Connection": "keep-alive"}
HEADERS_LOGINBP = {'Host': 'loginbp.ppmainecoonghj.com', 'User-Agent': 'UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)', 'Accept': '*/*', 'Accept-Encoding': 'deflate, gzip', 'Authorization': 'Bearer', 'X-GA': 'v1 1', 'ReleaseVersion': RELEASE_VER, 'Content-Type': 'application/x-www-form-urlencoded', 'X-Unity-Version': '2018.4.12f1'}

_tl = threading.local()
def get_session():
    s = getattr(_tl, "s", None)
    if s: return s
    s = requests.Session()
    a = HTTPAdapter(pool_connections=POOL_CONN, pool_maxsize=POOL_MAX, max_retries=0)
    s.mount("https://", a); s.mount("http://", a)
    _tl.s = s
    return s

def _build_login_meta(open_id, access_token):
    region = CONFIG.get("region", "IND")
    ip = IPRotator.get_random_ip(region)
    model, os_str, gpu, gpu_full = random.choice(DEVICES)
    return {'3': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S').encode(),'4': b'free fire', '5': 1, '7': GAME_VERSION.encode(),'8': os_str.encode(),'9': b'Handheld', '10': b'Jio', '11': b'WIFI','12': 1280, '13': 720, '14': b'240','15': b'x86-64 SSE3 SSE4.1 SSE4.2 AVX AVX2 | 2400 | 4','16': random.choice([5951, 6000, 6100, 5500]),'17': gpu.encode(),'18': gpu_full.encode(),'19': f'Google|{uuid.uuid4()}'.encode(),'20': ip.encode(),'21': b'en', '22': open_id.encode(),'23': b'4', '24': b'Handheld','25': model.encode(),'26': region.encode(),'29': access_token.encode(), '30': 1,'41': b'Jio', '42': b'WIFI','57': b'1ac4b80ecf0478a44203bf8fac6120f5','60': 30000, '61': 30000, '62': 2519, '63': 243,'64': 32357, '65': 34308, '66': 32357, '67': 34308, '73': 1,'74': b'/data/app/~~iw-K-GR3srU7dLE-UxJ4bg==/com.dts.freefiremax-kbPhw3SUYautW0I_oayB_A==/lib/arm','76': 2,'77': b'428775ab8c8845bd341b5357ec61d15e|/data/app/~~iw-K-GR3srU7dLE-UxJ4bg==/com.dts.freefiremax-kbPhw3SUYautW0I_oayB_A==/base.apk','78': 2, '79': 1, '81': b'32', '83': b'2019118525', '85': 3,'86': b'OpenGLES3', '87': 4095, '88': 4,'92': random.choice([19788, 20000, 21000]),'93': b'android_max','94': b'KqsHT2gyPt7vUCc9SCjv2ioi3WEZSEL86ErvXB38suVVK/Z4IVt78ESl/r2S15C1pqu/j6ZmgFL7HbwoFiiVconX08ooKiisQffvEAPCo/C+Lahr','96': b'{"cur_rate":null,"support_etc2":true}','97': 1, '98': 1, '99': b'4', '100': b'4', '102': b'','104': 77149, '105': 1,'106': b'https://dl.cdn.freefiremobile.com/live/ABHotUpdates/|https://dl-core.cdn.freefiremobile.com/live/ABHotUpdates/|6b2078db9d22dd98f8e9386a39af8462','107': b'c8e41b7a93f02d56e1a94c7b8203f5d1'}

def register_one(worker_id, batch_num):
    if STOP_GEN.is_set(): return None
    session = get_session()
    proxy = get_proxy()
    for attempt in range(1, MAX_RETRIES + 1):
        if STOP_GEN.is_set(): return None
        try:
            pace_proxy(proxy)
            password = gen_password()
            reg_body = json.dumps({"app_id": APP_ID, "client_type": 2, "password": password, "source": 2}, separators=(",", ":"))
            reg_sig = hmac.new(MAIN_KEY, reg_body.encode(), hashlib.sha256).hexdigest()
            r = session.post(URL_GUEST_REGISTER, headers={**HEADERS_MSDK, "Authorization": "Signature " + reg_sig}, data=reg_body, verify=False, proxies=proxy, timeout=HTTP_TIMEOUT)
            if r.status_code == 429: cooldown(proxy, PROXY_COOLDOWN_429); proxy = get_proxy(); continue
            if r.status_code == 503: cooldown(proxy, PROXY_COOLDOWN_503); proxy = get_proxy(); continue
            if r.status_code != 200: raise Exception(f"reg HTTP {r.status_code}")
            uid = r.json()["data"]["uid"]
            dev_id = f"02-{uuid.uuid4()}"
            grant_body = {"client_id": APP_ID, "client_secret": CLIENT_SECRET, "client_type": 2, "device_id": dev_id, "password": password, "response_type": "token", "uid": int(uid)}
            r2 = session.post(URL_TOKEN_GRANT, headers=HEADERS_MSDK, json=grant_body, verify=False, proxies=proxy, timeout=HTTP_TIMEOUT)
            if r2.status_code != 200: raise Exception(f"grant HTTP {r2.status_code}")
            gd = r2.json()["data"]
            access_token = gd["access_token"]
            open_id      = gd["open_id"]
            hdr = dict(HEADERS_LOGINBP)
            hdr["X-GA-SV"] = str(int(time.time()))
            login_meta = _build_login_meta(open_id, access_token)
            try: session.post(URL_MAJOR_LOGIN, headers=hdr, data=enc_aes(blackboxprotobuf.encode_message(login_meta, typedef_login)), verify=False, proxies=proxy, timeout=HTTP_TIMEOUT)
            except Exception: pass
            nick = gen_nickname()
            reg_msg = {'1': nick, '2': access_token.encode(), '3': open_id.encode(),'5': 102000007, '6': 4, '7': 1, '13': 1,'14': encode_f14(open_id), '15': b'en', '16': 2,'20': GAME_VERSION.encode(), '21': 1, '22': FIELD_22}
            rr = session.post(URL_MAJOR_REGISTER, headers=hdr, data=enc_aes(blackboxprotobuf.encode_message(reg_msg, typedef_reg)), verify=False, proxies=proxy, timeout=HTTP_TIMEOUT)
            if rr.status_code != 200: raise Exception(f"majorreg HTTP {rr.status_code}")
            res, _ = blackboxprotobuf.decode_message(rr.content)
            account_id = None
            if isinstance(res, dict): account_id = res.get('3') or res.get(b'3')
            if not account_id: raise Exception("no account_id")
            try: session.post(URL_NEWBIE_CHOICE, headers=hdr, data=enc_aes(blackboxprotobuf.encode_message({'1': int(account_id), '2': 2, '3': 3}, typedef_newbie)), verify=False, proxies=proxy, timeout=HTTP_TIMEOUT)
            except Exception: pass
            
            nick_str = nick.decode('utf-8', errors='ignore')
            acc = {"account_name": nick_str, "account_region": CONFIG.get("region", "IND"), "uid": str(uid), "account_id": str(account_id), "password": str(password), "status": "registered", "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            ALL_ACCOUNTS.append(acc)
            append_generated(acc, batch_num)
            print(f"[GEN+] {nick_str} | uid={uid} | acc={account_id} | batch={batch_num}")
            return acc
        except requests.exceptions.Timeout: time.sleep(FAIL_WAIT)
        except requests.exceptions.ProxyError: cooldown(proxy, 30); proxy = get_proxy()
        except Exception as e:
            with STATE_LOCK: STATE["last_error"] = str(e)
            time.sleep(FAIL_WAIT)
    with STATE_LOCK: STATE["failed"] += 1
    return None

def _forge_worker(target_count, threads, batch_num):
    try:
        session_start = len(ALL_ACCOUNTS)
        with STATE_LOCK: STATE["session_start_count"] = session_start
        with ThreadPoolExecutor(max_workers=threads) as ex:
            pending = set()
            submitted = 0
            max_attempts = max(target_count * 20, target_count + 100)
            while True:
                if STOP_GEN.is_set(): break
                with STATE_LOCK: session_done = len(ALL_ACCOUNTS) - session_start
                if session_done >= target_count: break
                while len(pending) < threads and submitted < max_attempts:
                    pending.add(ex.submit(register_one, submitted % threads + 1, batch_num))
                    submitted += 1
                if not pending: break
                done, pending = _wait(pending, return_when=_FC)
                with STATE_LOCK: session_done = len(ALL_ACCOUNTS) - session_start
                if session_done >= target_count:
                    for p in pending: p.cancel()
                    break
                if submitted >= max_attempts and not pending: break
    finally:
        with STATE_LOCK:
            STATE["running"] = False
            STATE["finished_at"] = int(time.time())

# ═══════════════════════════════════════════════════════════
#  🚀 ACTIVATOR
# ═══════════════════════════════════════════════════════════
REGIONAL_LOGIN_HOSTS = {"IND": "https://client.ind.freefiremobile.com/","BD":  "https://client.bd.freefiremobile.com/","SG":  "https://client.sg.freefiremobile.com/","BR":  "https://client.br.freefiremobile.com/","US":  "https://client.us.freefiremobile.com/","EU":  "https://client.eu.freefiremobile.com/","ME":  "https://client.me.freefiremobile.com/"}
MAJORLOGIN_FALLBACK_HOSTS = ["https://client.ind.freefiremobile.com/","https://client.bd.freefiremobile.com/","https://loginbp.ppmainecoonghj.com/","https://loginbp.ggmainecoonghj.com/","https://loginbp.ggblueshark.com/","https://loginbp.commonmainecoonghj.com/","https://indnetwork.ggblueshark.com/","https://indgigateway.ggblueshark.com/"]
ACT_AES_KEY = b'Yg&tc%DEuh6%Zc^8'
ACT_AES_IV  = b'6oyZDr22E3ychjM%'

BATCH_SIZE = 30
BATCH_INTERVAL = 0.5
ONLINE_DURATION = 3.0
LOGIN_CONCURRENCY = 60
MAX_CONNECTIONS = 1000
MAX_KEEPALIVE = 500
HOST_RACE_TIMEOUT = 6.0
_act_client = None

def _get_act_client():
    global _act_client
    if _act_client is None:
        _act_client = httpx.AsyncClient(verify=False, timeout=httpx.Timeout(15.0, connect=6.0), limits=httpx.Limits(max_connections=MAX_CONNECTIONS, max_keepalive_connections=MAX_KEEPALIVE), follow_redirects=True, http2=False)
    return _act_client

def _act_aes_encrypt(payload: bytes) -> bytes:
    cipher = AES.new(ACT_AES_KEY, AES.MODE_CBC, ACT_AES_IV)
    return cipher.encrypt(pad(payload, AES.block_size))

async def _act_version_config(region="IND"):
    reg = (region or "IND").upper()
    regional_url = REGIONAL_LOGIN_HOSTS.get(reg, REGIONAL_LOGIN_HOSTS["IND"])
    return ("OB55", "1.132.9", regional_url)

async def _get_access_token(uid, password):
    client = _get_act_client()
    url = "https://100067.connect.garena.com/oauth/guest/token/grant"
    hdrs = {"Host": "100067.connect.garena.com","User-Agent": "Dalvik/2.1.0 (Linux; U; Android 12; SM-G998B Build/SP1A.210812.016)","Content-Type": "application/x-www-form-urlencoded","Accept-Encoding": "gzip, deflate, br","Connection": "close"}
    data = {"uid": uid, "password": password,"response_type": "token","client_type": "2","client_secret": CLIENT_SECRET,"client_id": "100067"}
    for _ in range(3):
        try:
            r = await client.post(url, headers=hdrs, data=data)
            if r.status_code == 200:
                d = r.json()
                oid = d.get("open_id"); tok = d.get("access_token")
                plat = d.get("platform", 4)
                if oid and tok: return oid, tok, plat
            if r.status_code == 429: await asyncio.sleep(0.8); continue
        except Exception: pass
        await asyncio.sleep(0.3)
    return None

async def _build_majorlogin_payload_pb2(open_id, access_token, platform, client_version, device_info):
    try:
        req = MASTERTeam_pb2.MajorLoginReq()
        req.event_time = str(datetime.now())[:-7]
        req.game_name = "free fire"
        req.platform_id = int(platform)
        req.client_version = str(client_version) if client_version else "1.132.9"
        req.system_software = str(device_info.get("system_software", "Android OS 15 / API-35"))
        req.system_hardware = "Handheld"
        req.telecom_operator = "Telkomsel"
        req.network_type = "CarrierDataNetwork"
        req.screen_width = int(device_info.get("screen_width", 1639))
        req.screen_height = int(device_info.get("screen_height", 720))
        req.screen_dpi = str(device_info.get("screen_dpi", 320))
        req.processor_details = str(device_info.get("processor_details", "ARM64 FP ASIMD AES | 2000 | 8"))
        req.memory = int(device_info.get("memory", 5653))
        req.gpu_renderer = str(device_info.get("gpu_renderer", "Mali-G52 MC2"))
        req.gpu_version = "OpenGL ES 3.2 v1.r49p1-03bet0.19498e0ae1d5dac223383c39a2e58f04"
        req.unique_device_id = str(device_info.get("unique_device_id", f"Google|{uuid.uuid4()}"))
        req.client_ip = str(device_info.get("client_ip", "182.5.135.225"))
        req.language = "en"
        req.open_id = str(open_id)
        req.open_id_type = str(platform)
        req.device_type = "Handheld"
        req.access_token = str(access_token)
        req.platform_sdk_id = 1
        req.network_operator_a = "Telkomsel"
        req.network_type_a = "4G"
        req.client_using_version = "7428b253defc164018c604a1ebbfebdf"
        req.external_storage_total = 109278
        req.external_storage_available = 55402
        req.internal_storage_total = 868
        req.game_disk_storage_available = 55927
        req.internal_storage_available = 109278
        req.game_disk_storage_total = 55927
        req.external_sdcard_avail_storage = 109278
        req.external_sdcard_total_storage = 2
        req.library_path = "/data/app/~~6Cw028g_ld-8Z0z2qhrOLA==/com.dts.freefireth-i3wiaEmpx8CbiRVhUMx_ag==/lib/arm64"
        req.reg_avatar = 1
        req.library_token = "b8e0cd5e295eee42f5860d3c86e483dd|/data/app/~~6Cw028g_ld-8Z0z2qhrOLA==/com.dts.freefireth-i3wiaEmpx8CbiRVhUMx_ag==/base.apk"
        req.channel_type = 3
        req.cpu_type = 2
        req.cpu_architecture = "64"
        req.client_version_code = "2019121229"
        req.graphics_api = "OpenGLES2"
        req.supported_astc_bitset = 8191
        req.login_open_id_type = int(platform)
        req.analytics_detail = "KqsHTyb7yHjsAiyNWUUZa0DSOD6U0AhDQ76smAo1WeHHHpSmJ8KMRyRrxb2ttgJqO9YOqO/K6AORAvDMAX/qBS8+JahIkrM7kHfzlfULbgRAoZ9r".encode('utf-8')
        req.loading_time = 111207
        req.extra_info = "{\"cur_rate\":[60,90,120],\"support_etc2\":false}"
        req.android_engine_init_flag = 1
        req.if_push = 1
        req.is_vpn = 1
        req.origin_platform_type = str(platform)
        req.primary_platform_type = str(platform)
        return _act_aes_encrypt(req.SerializeToString())
    except Exception: return None

async def _try_majorlogin_pb2(base_url, data, release_version):
    client = _get_act_client()
    url = f"{base_url.rstrip('/')}/MajorLogin"
    hdrs = {'User-Agent': 'UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)','Connection': 'Keep-Alive','Accept-Encoding': 'gzip','Content-Type': 'application/octet-stream','X-Unity-Version': '2018.4.12f1','X-GA-SV': '1789535859','X-GA': 'v1 1','ReleaseVersion': release_version}
    try:
        r = await client.post(url, headers=hdrs, content=data)
        if r.status_code != 200 or len(r.content) < 20: return None
        try:
            res_proto = MASTERTeam_pb2.MajorLoginRes()
            res_proto.ParseFromString(r.content)
            if res_proto.region and res_proto.token: return res_proto
        except Exception: pass
        if len(r.content) > 64:
            try:
                res_proto = MASTERTeam_pb2.MajorLoginRes()
                res_proto.ParseFromString(r.content[64:])
                if res_proto.region and res_proto.token: return res_proto
            except Exception: pass
        for offset in range(min(160, len(r.content))):
            try:
                candidate = MASTERTeam_pb2.MajorLoginRes()
                candidate.ParseFromString(r.content[offset:])
                if candidate.region and candidate.token: return candidate
            except Exception: continue
    except Exception: return None
    return None

async def _try_getlogin_pb2(base_url, data, token, release_version):
    client = _get_act_client()
    url = f"{base_url.rstrip('/')}/GetLoginData"
    hdrs = {'User-Agent': 'UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)','Connection': 'Keep-Alive','Accept-Encoding': 'gzip','Content-Type': 'application/octet-stream','X-Unity-Version': '2018.4.12f1','X-GA-SV': '1789535859','X-GA': 'v1 1','ReleaseVersion': release_version,'Authorization': f"Bearer {token}"}
    try:
        from urllib.parse import urlparse
        hdrs["Host"] = urlparse(base_url).netloc
    except Exception: pass
    try:
        r = await client.post(url, headers=hdrs, content=data)
        if r.status_code != 200: return None
        res_proto = MASTERTeam_pb2.GetLoginDataRes()
        parsed = False
        try:
            res_proto.ParseFromString(r.content)
            if res_proto.functional_addrs or res_proto.informational_addrs: parsed = True
        except Exception: pass
        if not parsed:
            for offset in range(min(160, len(r.content))):
                try:
                    cand = MASTERTeam_pb2.GetLoginDataRes()
                    cand.ParseFromString(r.content[offset:])
                    if cand.functional_addrs or cand.informational_addrs:
                        res_proto = cand; parsed = True; break
                except Exception: continue
        if not parsed: return None
        dict_res = {}
        try:
            for r_field in Parser().parse(r.content.hex()):
                key = str(r_field.field)
                if r_field.wire_type in ("varint", "string", "bytes"):
                    dict_res[key] = {"data": r_field.data}
        except Exception: pass
        return res_proto, dict_res
    except Exception: return None

async def _build_tcp_startup_packet(account_id, token, server_time, key, iv, region="IND", typ='OnLine'):
    uid_hex = f"{int(account_id):016x}"
    timestamp_hex = f"{int(server_time):08x}"
    encode_token = token.encode()
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted_packet = cipher.encrypt(pad(encode_token, AES.block_size)).hex()
    encrypted_packet_length = f"{len(encrypted_packet) // 2:08x}"
    reg = (region or "IND").upper()
    if typ == 'OnLine':
        prefix = '7219' if reg == 'BD' else ('7214' if reg == 'IND' else '7215')
        return f"{prefix}{uid_hex}{timestamp_hex}00000000{encrypted_packet_length}{encrypted_packet}"
    else:
        prefix = '8119' if reg == 'BD' else ('8114' if reg == 'IND' else '8115')
        return f"{prefix}{uid_hex}{timestamp_hex}{encrypted_packet_length}{encrypted_packet}"

async def _send_keep_alive(region="IND"):
    reg = (region or "IND").upper()
    ka_hex = "0219" if reg == "BD" else ("0214" if reg == "IND" else "0215")
    return bytes.fromhex(ka_hex)

async def _resolve_host(hostname):
    if not hostname: return hostname
    parts = hostname.split('.')
    if len(parts) == 4 and all(p.isdigit() for p in parts): return hostname
    try:
        loop = asyncio.get_running_loop()
        info = await loop.getaddrinfo(hostname, None, family=socket.AF_INET)
        if info: return info[0][4][0]
    except Exception: pass
    return hostname

def _optimize_tcp(sock):
    try:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    except Exception: pass

_ACT_SEMAPHORE = None

def _get_sem():
    global _ACT_SEMAPHORE
    if _ACT_SEMAPHORE is None: _ACT_SEMAPHORE = asyncio.Semaphore(LOGIN_CONCURRENCY)
    return _ACT_SEMAPHORE

def _random_act_device(uid_seed):
    brand, model, gpu, os_ver = random.choice([("Samsung", "SM-G998B",  "Adreno (TM) 660", "Android OS 12 / API-31"),("Xiaomi",  "2201122G",  "Adreno (TM) 730", "Android OS 13 / API-33"),("Realme",  "RMX3700",   "Mali-G710",       "Android OS 14 / API-34"),("OnePlus", "CPH2451",   "Adreno (TM) 740", "Android OS 13 / API-33"),("OPPO",    "CPH2611",   "Adreno (TM) 720", "Android OS 14 / API-34")])
    return {"unique_device_id": f"Google|{uuid.uuid4()}","brand": brand, "model": model,"gpu_renderer": gpu, "system_software": os_ver,"screen_width":  random.choice([1080, 1440, 720, 1280]),"screen_height": random.choice([2400, 3200, 1600, 2400]),"screen_dpi":    str(random.randint(300, 420)),"memory":        random.randint(2800, 6500),"processor_details": f"ARM64 FP ASIMD AES VMH | {random.randint(2200, 3200)} | {random.randint(6, 12)}","client_ip": IPRotator.get_random_ip("IND")}

async def _activate_single(acc, idx, total, batch_num):
    if STOP_ACT.is_set(): return False
    uid_input  = str(acc.get("uid", ""))
    password   = acc.get("password", "")
    input_nick = acc.get("account_name", "")
    try:
        async with _get_sem():
            if STOP_ACT.is_set(): return False
            release_version, client_version, server_url = await _act_version_config("IND")
            tg = await _get_access_token(uid_input, password)
            if tg is None: raise Exception("token grant failed")
            open_id, access_token, platform = tg
            device_info = _random_act_device(uid_input)
            payload = await _build_majorlogin_payload_pb2(open_id, access_token, platform, client_version, device_info)
            if payload is None: raise Exception("payload build failed")
            candidates = [server_url.rstrip("/") + "/"] + [h.rstrip("/") + "/" for h in MAJORLOGIN_FALLBACK_HOSTS]
            ml = None
            tasks = [asyncio.create_task(_try_majorlogin_pb2(b, payload, release_version)) for b in candidates]
            try:
                done, pending = await asyncio.wait(tasks, timeout=HOST_RACE_TIMEOUT, return_when=asyncio.FIRST_COMPLETED)
                for t in done:
                    try:
                        r = t.result()
                        if r is not None:
                            ml = r
                            for p in pending: p.cancel()
                            break
                    except Exception: continue
                if ml is None:
                    for t in pending:
                        try:
                            r = await t
                            if r is not None: ml = r; break
                        except Exception: continue
            finally:
                for t in tasks:
                    if not t.done(): t.cancel()
            if ml is None: raise Exception("MajorLogin failed")
            region = ml.region or "IND"
            gl_candidates = []
            reg_host = REGIONAL_LOGIN_HOSTS.get(region.upper())
            if reg_host: gl_candidates.append(reg_host.rstrip("/") + "/")
            if ml.url: gl_candidates.append(ml.url.rstrip("/") + "/")
            for h in MAJORLOGIN_FALLBACK_HOSTS:
                n = h.rstrip("/") + "/"
                if n not in gl_candidates: gl_candidates.append(n)
            gl = None
            gl_dict = {}
            tasks = [asyncio.create_task(_try_getlogin_pb2(b, payload, ml.token, release_version)) for b in gl_candidates]
            try:
                done, pending = await asyncio.wait(tasks, timeout=HOST_RACE_TIMEOUT, return_when=asyncio.FIRST_COMPLETED)
                for t in done:
                    try:
                        r = t.result()
                        if r is not None:
                            gl, gl_dict = r
                            for p in pending: p.cancel()
                            break
                    except Exception: continue
                if gl is None:
                    for t in pending:
                        try:
                            r = await t
                            if r is not None: gl, gl_dict = r; break
                        except Exception: continue
            finally:
                for t in tasks:
                    if not t.done(): t.cancel()
            if gl is None: raise Exception("GetLoginData failed")
            addrs = gl.functional_addrs
            if not addrs: raise Exception("no functional_addrs")
            ip, port = addrs.split(":")
            rip = await _resolve_host(ip)
            reader, writer = await asyncio.open_connection(rip, int(port))
            sock = writer.get_extra_info("socket")
            if sock: _optimize_tcp(sock)
            tcp_hex = await _build_tcp_startup_packet(ml.account_id, ml.token, ml.server_time or int(time.time()), ml.aes_ak or ACT_AES_KEY, ml.iv_i or ACT_AES_IV, region=region, typ="OnLine")
            writer.write(bytes.fromhex(tcp_hex))
            await writer.drain()
            try:
                ka = await _send_keep_alive(region)
                if ka and not writer.is_closing():
                    writer.write(ka)
                    await asyncio.wait_for(writer.drain(), timeout=1.5)
            except Exception: pass
            start = time.time()
            while time.time() - start < ONLINE_DURATION:
                if STOP_ACT.is_set(): break
                try:
                    data = await asyncio.wait_for(reader.read(4096), timeout=0.3)
                    if not data: break
                except asyncio.TimeoutError:
                    try:
                        if not writer.is_closing():
                            writer.write(await _send_keep_alive(region))
                            await writer.drain()
                    except Exception: break
                except Exception: break
            try:
                writer.close()
                await asyncio.wait_for(writer.wait_closed(), timeout=0.8)
            except Exception: pass
            
            lvl = 1
            try:
                val = gl_dict.get('6', {}).get('data')
                if val is not None: lvl = int(val)
            except Exception: pass

            nick = gl.nickname or input_nick or f"Player_{ml.account_id}"
            reg  = gl.region if hasattr(gl, 'region') and gl.region else (ml.region or "IND")
            entry = {"account_name": nick,"account_region": reg,"uid": uid_input,"account_id": str(ml.account_id),"password": password,"nickname": nick,"level": lvl,"status": "activated","activated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            ALL_ACTIVATED.append(entry)
            append_activated(entry, batch_num)
            with STATE_LOCK: ACT_STATE["active"] += 1
            print(f"[ACT+] {nick} | uid={uid_input} | lvl={lvl} | batch={batch_num}")
            return True
    except Exception as e:
        with STATE_LOCK: ACT_STATE["failed"] += 1
        ALL_FAILED.append({"uid": uid_input,"account_name": input_nick,"reason": str(e)[:120]})
        print(f"[ACT✗] {input_nick or uid_input} | {str(e)[:80]}")
        return False

async def _activate_batch(batch, start_idx, total, batch_num):
    tasks = []
    for i, acc in enumerate(batch):
        if STOP_ACT.is_set(): break
        tasks.append(_activate_single(acc, start_idx + i + 1, total, batch_num))
    if tasks: await asyncio.gather(*tasks, return_exceptions=True)

def _run_activator_sync(accounts, threads, batch_num):
    global _act_client, _ACT_SEMAPHORE
    _act_client = None
    _ACT_SEMAPHORE = None
    async def _main():
        total = len(accounts)
        for i in range(0, total, BATCH_SIZE):
            if STOP_ACT.is_set(): break
            batch = accounts[i:i + BATCH_SIZE]
            await _activate_batch(batch, i, total, batch_num)
            await asyncio.sleep(BATCH_INTERVAL)
    try: asyncio.run(_main())
    except Exception as e:
        with STATE_LOCK: ACT_STATE["last_error"] = str(e)
    finally:
        with STATE_LOCK:
            ACT_STATE["running"] = False
            ACT_STATE["finished_at"] = int(time.time())

def _activate_worker(accounts_list, threads, batch_num):
    try:
        if not accounts_list:
            with STATE_LOCK: ACT_STATE["last_error"] = "No accounts to activate"
            return
        _run_activator_sync(accounts_list, threads, batch_num)
    finally:
        with STATE_LOCK: ACT_STATE["running"] = False

# ═══════════════════════════════════════════════════════════
#  DASHBOARD HTML
# ═══════════════════════════════════════════════════════════
DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>💀 KAMOD DEVILS WILL RISE</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:'Segoe UI',system-ui,sans-serif; background:#0a0510; color:#eee; min-height:100vh; padding:20px;
    background-image: radial-gradient(circle at 20% 10%, rgba(255,20,147,0.15), transparent 40%),
                      radial-gradient(circle at 80% 80%, rgba(0,255,255,0.10), transparent 40%); }
  .container{max-width:1300px;margin:0 auto;}
  header{text-align:center;margin-bottom:26px;padding-bottom:18px;border-bottom:2px solid rgba(255,20,147,0.3);}
  h1{font-size:2.1rem;background:linear-gradient(90deg,#ff1493,#da70d6,#00ffff,#40e0d0);
     -webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:2px;}
  .owner{color:#888;font-size:0.85rem;margin-top:6px;letter-spacing:1px;}
  .card{background:rgba(20,10,30,0.7);border:1px solid rgba(255,20,147,0.25);border-radius:14px;
        padding:22px;margin-bottom:18px;backdrop-filter:blur(10px);box-shadow:0 8px 32px rgba(0,0,0,0.4);}
  .card h2{font-size:1.05rem;color:#ff69b4;margin-bottom:14px;letter-spacing:1px;text-transform:uppercase;}
  .row{display:flex;gap:14px;flex-wrap:wrap;}
  .field{flex:1;min-width:170px;}
  .field label{display:block;color:#999;font-size:0.75rem;margin-bottom:6px;text-transform:uppercase;letter-spacing:1px;}
  .field input,.field select{width:100%;background:rgba(0,0,0,0.5);border:1px solid rgba(255,20,147,0.3);
    border-radius:8px;padding:11px 14px;color:#fff;font-size:0.95rem;outline:none;transition:.2s;}
  .field input:focus,.field select:focus{border-color:#ff1493;box-shadow:0 0 0 3px rgba(255,20,147,.15);}
  button{background:linear-gradient(90deg,#ff1493,#b026ff);border:none;color:#fff;padding:12px 22px;
    border-radius:10px;font-size:0.9rem;font-weight:700;letter-spacing:1px;cursor:pointer;transition:.2s;text-transform:uppercase;}
  button:hover{transform:translateY(-2px);box-shadow:0 6px 20px rgba(255,20,147,.5);}
  button:disabled{opacity:.45;cursor:not-allowed;transform:none;box-shadow:none;}
  button.alt{background:linear-gradient(90deg,#00c9a7,#00b4d8);}
  button.danger{background:linear-gradient(90deg,#e63946,#f77f00);}
  button.gold{background:linear-gradient(90deg,#ffb700,#ff7b00);}
  .btn-row{display:flex;gap:12px;flex-wrap:wrap;margin-top:14px;}
  .stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px;margin-bottom:16px;}
  .stat{background:rgba(0,0,0,0.4);border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:14px;text-align:center;}
  .stat .val{font-size:1.7rem;font-weight:800;background:linear-gradient(90deg,#ff69b4,#00ffff);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;}
  .stat .lbl{font-size:0.7rem;color:#888;margin-top:4px;text-transform:uppercase;letter-spacing:1px;}
  .progress-wrap{height:12px;background:rgba(0,0,0,.5);border-radius:8px;overflow:hidden;
    margin-top:8px;border:1px solid rgba(255,255,255,.08);}
  .progress-bar{height:100%;width:0%;background:linear-gradient(90deg,#ff1493,#00ffff);transition:width .4s;}
  .progress-bar.act{background:linear-gradient(90deg,#ffb700,#00ff7f);}
  .status-pill{display:inline-block;padding:5px 12px;border-radius:20px;font-size:0.72rem;font-weight:700;
    letter-spacing:1px;text-transform:uppercase;}
  .pill-run{background:rgba(255,20,147,.2);color:#ff69b4;border:1px solid #ff1493;}
  .pill-idle{background:rgba(128,128,128,.2);color:#aaa;border:1px solid #555;}
  .pill-done{background:rgba(0,255,127,.15);color:#00ff7f;border:1px solid #00c853;}
  .pill-stop{background:rgba(230,57,70,.2);color:#ff8a8a;border:1px solid #e63946;}
  table{width:100%;border-collapse:collapse;font-size:0.82rem;margin-top:10px;}
  th,td{text-align:left;padding:9px 10px;border-bottom:1px solid rgba(255,255,255,0.06);}
  th{color:#ff69b4;text-transform:uppercase;font-size:0.7rem;letter-spacing:1px;}
  tr:hover{background:rgba(255,20,147,0.05);}
  .mono{font-family:Consolas,monospace;font-size:0.78rem;color:#aaa;}
  .toast{position:fixed;bottom:24px;right:24px;background:linear-gradient(90deg,#ff1493,#b026ff);
    padding:13px 20px;border-radius:10px;color:#fff;font-weight:600;box-shadow:0 8px 30px rgba(255,20,147,.5);
    transform:translateY(120%);transition:.3s;z-index:999;}
  .toast.show{transform:translateY(0);}
  .toast.err{background:linear-gradient(90deg,#e63946,#f77f00);}
  .empty{text-align:center;color:#666;padding:24px;font-style:italic;}
  .scroll{max-height:420px;overflow-y:auto;}
  .scroll::-webkit-scrollbar{width:8px;}
  .scroll::-webkit-scrollbar-thumb{background:#ff1493;border-radius:4px;}
  .tab{display:flex;gap:10px;margin-bottom:16px;}
  .tab button{background:rgba(0,0,0,0.4);border:1px solid rgba(255,20,147,0.3);color:#aaa;padding:9px 18px;
    border-radius:8px;font-size:0.82rem;text-transform:uppercase;letter-spacing:1px;cursor:pointer;}
  .tab button.active{background:linear-gradient(90deg,#ff1493,#b026ff);color:#fff;border-color:transparent;}
  .hide{display:none;}
  .region-tag{display:inline-block;padding:2px 8px;border-radius:4px;background:rgba(0,255,255,.15);
    color:#00ffff;font-size:0.7rem;font-weight:700;}
  .proxy-tag{display:inline-block;padding:2px 8px;border-radius:4px;background:rgba(255,183,0,.15);
    color:#ffb700;font-size:0.7rem;font-weight:700;}
  
  /* MODAL STYLES */
  .modal { display:none; position:fixed; z-index:1000; left:0; top:0; width:100%; height:100%; background-color:rgba(0,0,0,0.8); backdrop-filter:blur(5px); }
  .modal-content { background:rgba(20,10,30,0.95); margin:10% auto; padding:24px; border:1px solid #ff1493; border-radius:14px; width:90%; max-width:500px; box-shadow:0 10px 40px rgba(255,20,147,.3); }
  .modal-content h3 { color:#ff69b4; margin-bottom:16px; text-transform:uppercase; letter-spacing:1px; }
  .file-list { max-height: 300px; overflow-y: auto; margin-bottom: 20px; }
  .file-item { padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); cursor: pointer; display: flex; justify-content: space-between; align-items: center; }
  .file-item:hover { background: rgba(255,20,147,0.1); }
  .file-name { font-family: monospace; color:#00ffff; }
  .file-size { font-size: 0.8rem; color: #888; }
  .modal-close { background: transparent; border: 1px solid #ff1493; color: #ff1493; padding: 8px 16px; border-radius: 8px; cursor: pointer; text-transform: uppercase; font-weight: bold; }
  .modal-close:hover { background: #ff1493; color: #fff; }
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>💀 KAMOD DEVILS WILL RISE 💀</h1>
    <div class="owner">Owner @kamod_codex · Channel @kamod_codex</div>
  </header>
  <div class="tab">
    <button id="tabGen" class="active" onclick="switchTab('gen')">⚙️ Generator</button>
    <button id="tabAct" onclick="switchTab('act')">🚀 Activator</button>
    <button id="tabProxy" onclick="switchTab('proxy')">🌐 Proxy Pool</button>
  </div>
  <!-- GENERATOR -->
  <div id="panelGen">
    <div class="card">
      <h2>⚙️ Account Generator</h2>
      <div class="row">
        <div class="field"><label>Name Prefix</label><input id="gName" type="text" value="MasteR~" maxlength="12"></div>
        <div class="field"><label>Region</label><select id="gRegion"><option value="IND">IND — India</option><option value="BD">BD — Bangladesh</option><option value="PK">PK — Pakistan</option><option value="ID">ID — Indonesia</option><option value="SG">SG — Singapore</option></select></div>
        <div class="field"><label>Count (1 - 100000)</label><input id="gCount" type="number" value="10" min="1" max="100000"></div>
        <div class="field"><label>Threads</label><input id="gThreads" type="number" value="10" min="1" max="100"></div>
        <div class="field"><label>Use Proxy</label><select id="gProxy"><option value="false">OFF — direct (fast)</option><option value="true">ON — free proxy pool (safe)</option></select></div>
      </div>
      <div class="btn-row">
        <button id="btnGen" onclick="startGen()">🚀 Start Generate</button>
        <button class="danger" id="btnStopGen" onclick="stopAll()">⛔ STOP</button>
        <button class="alt" onclick="refreshAll()">🔄 Refresh</button>
        <button class="danger" onclick="resetGen()">🗑️ Reset All Generated</button>
        <button class="gold" onclick="openModal('gen', 'download')">⬇️ Download / Select Batch</button>
      </div>
    </div>
    <div class="card">
      <h2>📊 Generator Status</h2>
      <div class="stats">
        <div class="stat"><div class="val" id="gGen">0</div><div class="lbl">Total Generated</div></div>
        <div class="stat"><div class="val" id="gSession">0</div><div class="lbl">This Session</div></div>
        <div class="stat"><div class="val" id="gTarget">0</div><div class="lbl">Session Target</div></div>
        <div class="stat"><div class="val" id="gFail">0</div><div class="lbl">Failed</div></div>
        <div class="stat"><div class="val" id="gRun">—</div><div class="lbl">State</div></div>
      </div>
      <div class="progress-wrap"><div class="progress-bar" id="gBar"></div></div>
      <div style="margin-top:12px;">
        <span class="status-pill pill-idle" id="gPill">IDLE</span>
        <span style="color:#888;font-size:0.8rem;margin-left:12px;" id="gText">Ready</span>
      </div>
    </div>
    <div class="card">
      <h2>📦 Generated Accounts (Master)</h2>
      <div class="scroll"><table><thead><tr><th>#</th><th>Name</th><th>Region</th><th>UID</th><th>Acc ID</th><th>Password</th></tr></thead><tbody id="gBody"><tr><td colspan="6" class="empty">No accounts yet.</td></tr></tbody></table></div>
    </div>
  </div>
  <!-- ACTIVATOR -->
  <div id="panelAct" class="hide">
    <div class="card">
      <h2>🚀 Account Activator</h2>
      <div class="row"><div class="field"><label>Threads</label><input id="aThreads" type="number" value="10" min="1" max="100"></div></div>
      <div class="btn-row">
        <button class="gold" id="btnAct" onclick="openModal('gen', 'activate')">🚀 Start Activation</button>
        <button class="danger" id="btnStopAct" onclick="stopAll()">⛔ STOP</button>
        <button class="alt" onclick="refreshAll()">🔄 Refresh</button>
        <button class="gold" onclick="openModal('act', 'download')">⬇️ Download / Select Batch</button>
        <button class="danger" onclick="clearAct()">🗑️ Reset All Activated</button>
      </div>
    </div>
    <div class="card">
      <h2>📊 Activator Status</h2>
      <div class="stats">
        <div class="stat"><div class="val" id="aAct">0</div><div class="lbl">Activated</div></div>
        <div class="stat"><div class="val" id="aTarget">0</div><div class="lbl">Total Accounts</div></div>
        <div class="stat"><div class="val" id="aFail">0</div><div class="lbl">Failed</div></div>
        <div class="stat"><div class="val" id="aRun">—</div><div class="lbl">State</div></div>
      </div>
      <div class="progress-wrap"><div class="progress-bar act" id="aBar"></div></div>
      <div style="margin-top:12px;">
        <span class="status-pill pill-idle" id="aPill">IDLE</span>
        <span style="color:#888;font-size:0.8rem;margin-left:12px;" id="aText">Ready</span>
      </div>
    </div>
    <div class="card">
      <h2>◉ Activated Accounts (Master)</h2>
      <div class="scroll"><table><thead><tr><th>#</th><th>Name</th><th>Region</th><th>UID</th><th>Acc ID</th><th>Level</th></tr></thead><tbody id="aBody"><tr><td colspan="6" class="empty">No activated accounts yet.</td></tr></tbody></table></div>
    </div>
    <div class="card" id="failCard" style="display:none;">
      <h2 style="color:#e63946;">✕ Failed Accounts</h2>
      <div class="scroll"><table><thead><tr><th>#</th><th>UID / Name</th><th>Reason</th></tr></thead><tbody id="fBody"></tbody></table></div>
    </div>
  </div>
  <!-- PROXY -->
  <div id="panelProxy" class="hide">
    <div class="card">
      <h2>🌐 Proxy Pool Status</h2>
      <div class="stats">
        <div class="stat"><div class="val" id="pSize">0</div><div class="lbl">Working Proxies</div></div>
        <div class="stat"><div class="val" id="pFetch">—</div><div class="lbl">Fetching</div></div>
        <div class="stat"><div class="val" id="pUse">—</div><div class="lbl">In Use</div></div>
      </div>
      <p style="color:#888;font-size:0.85rem;margin-top:12px;">Auto-fetch every 10 minutes. <span class="proxy-tag">Free proxies = slow but safe</span></p>
      <div class="btn-row"><button class="alt" onclick="refreshProxy()">🔄 Refresh Status</button><button class="gold" onclick="fetchProxy()">⬇️ Force Fetch Now</button></div>
    </div>
    <div class="card">
      <h2>🔍 Sample Proxies</h2>
      <div class="scroll" style="max-height:300px;"><table><thead><tr><th>#</th><th>Proxy</th></tr></thead><tbody id="pBody"><tr><td colspan="2" class="empty">No proxies loaded yet.</td></tr></tbody></table></div>
    </div>
  </div>
</div>

<!-- MODAL -->
<div id="downloadModal" class="modal">
  <div class="modal-content">
    <h3 id="modalTitle">Select File</h3>
    <div class="file-list" id="fileList"></div>
    <button class="modal-close" onclick="closeModal()">Close</button>
  </div>
</div>

<div class="toast" id="toast">Done</div>
<script>
let pollGen = null, pollAct = null, pollProxy = null;
let currentModalAction = 'download'; 

function toast(msg, isErr=false) { const t = document.getElementById('toast'); t.textContent = msg; t.className = 'toast show' + (isErr ? ' err' : ''); setTimeout(() => t.className = 'toast', 2500); }
function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function switchTab(tab) {
  document.getElementById('panelGen').classList.toggle('hide', tab !== 'gen');
  document.getElementById('panelAct').classList.toggle('hide', tab !== 'act');
  document.getElementById('panelProxy').classList.toggle('hide', tab !== 'proxy');
  document.getElementById('tabGen').classList.toggle('active', tab === 'gen');
  document.getElementById('tabAct').classList.toggle('active', tab === 'act');
  document.getElementById('tabProxy').classList.toggle('active', tab === 'proxy');
  if (tab === 'proxy') startProxyPoll();
  refreshAll();
}

// MODAL FUNCTIONS
async function openModal(type, action) {
  currentModalAction = action;
  document.getElementById('downloadModal').style.display = 'block';
  
  let title = 'Select File';
  if (type === 'gen' && action === 'download') title = 'Download Generated Batch';
  if (type === 'gen' && action === 'activate') title = 'Select Batch to Activate';
  if (type === 'act' && action === 'download') title = 'Download Activated Batch';
  
  document.getElementById('modalTitle').textContent = title;
  const listEl = document.getElementById('fileList');
  listEl.innerHTML = '<div style="text-align:center; padding:20px; color:#888;">Loading...</div>';
  
  try {
    const r = await fetch(`/list_files?type=${type}`);
    const files = await r.json();
    if (files.length === 0) {
      listEl.innerHTML = '<div style="text-align:center; padding:20px; color:#888;">No files found.</div>';
      return;
    }
    listEl.innerHTML = files.map(f => `
      <div class="file-item" onclick="handleFileClick('${f.name}')">
        <span class="file-name">${esc(f.name)}</span>
        <span class="file-size">${f.size} KB</span>
      </div>
    `).join('');
  } catch(e) {
    listEl.innerHTML = '<div style="text-align:center; padding:20px; color:#ff1493;">Error loading files.</div>';
  }
}

function closeModal() {
  document.getElementById('downloadModal').style.display = 'none';
}

async function handleFileClick(filename) {
  if (currentModalAction === 'download') {
    downloadFile(filename);
  } else if (currentModalAction === 'activate') {
    startAct(filename);
  }
}

async function downloadFile(filename) {
  try {
    const r = await fetch(`/get_file?name=${encodeURIComponent(filename)}`);
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || 'Failed');
    
    const blob = new Blob([JSON.stringify(data, null, 2)], {type:'application/json'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);
    toast(`⬇️ Downloaded ${filename}`);
    closeModal();
  } catch(e) {
    toast('❌ ' + e.message, true);
  }
}

// GENERATOR
async function startGen() {
  const name = document.getElementById('gName').value.trim() || 'MasteR~';
  const region = document.getElementById('gRegion').value;
  const count = parseInt(document.getElementById('gCount').value) || 10;
  const threads = parseInt(document.getElementById('gThreads').value) || 10;
  const useProxy = document.getElementById('gProxy').value;
  document.getElementById('btnGen').disabled = true;
  try {
    const url = `/account_gen?name=${encodeURIComponent(name)}&regin=${encodeURIComponent(region)}&count=${count}&threads=${threads}&use_proxy=${useProxy}`;
    const r = await fetch(url); const j = await r.json();
    if (r.ok) { toast(`🚀 Forge started: ${count} accounts`); startGenPoll(); }
    else { toast('❌ ' + (j.error || 'Failed'), true); document.getElementById('btnGen').disabled = false; }
  } catch(e) { toast('❌ ' + e.message, true); document.getElementById('btnGen').disabled = false; }
}
function startGenPoll() { if (pollGen) clearInterval(pollGen); pollGen = setInterval(refreshGen, 1500); refreshGen(); }
async function refreshGen() {
  try {
    const r = await fetch('/accounts'); const j = await r.json(); renderGen(j);
    if (!j.running) { document.getElementById('btnGen').disabled = false; if (pollGen) { clearInterval(pollGen); pollGen = null; } }
  } catch(e){}
}
function renderGen(j) {
  const accs = j.accounts || [];
  document.getElementById('gGen').textContent = accs.length;
  document.getElementById('gSession').textContent = j.session_count || 0;
  document.getElementById('gTarget').textContent = j.target || 0;
  document.getElementById('gFail').textContent = j.failed || 0;
  document.getElementById('gRun').textContent = j.running ? 'RUN' : 'IDLE';
  const sess = j.session_count || 0; const tgt = j.target || 0;
  const pct = tgt > 0 ? Math.min(100, (sess / tgt) * 100) : 0;
  document.getElementById('gBar').style.width = pct + '%';
  const pill = document.getElementById('gPill'); const stxt = document.getElementById('gText');
  if (j.stopped) { pill.className = 'status-pill pill-stop'; pill.textContent = 'STOPPED'; stxt.textContent = `Stopped · Session: ${sess}/${tgt} · Total: ${accs.length}`; }
  else if (j.running) { pill.className = 'status-pill pill-run'; pill.textContent = 'RUNNING'; stxt.textContent = `Generating... Session: ${sess}/${tgt} · Total: ${accs.length}`; }
  else if (sess > 0 || accs.length > 0) { pill.className = 'status-pill pill-done'; pill.textContent = 'DONE'; stxt.textContent = `Total: ${accs.length} accounts`; }
  else { pill.className = 'status-pill pill-idle'; pill.textContent = 'IDLE'; stxt.textContent = 'Ready'; }
  const tb = document.getElementById('gBody');
  if (accs.length === 0) { tb.innerHTML = '<tr><td colspan="6" class="empty">No accounts yet.</td></tr>'; return; }
  const display = accs.slice(-500);
  tb.innerHTML = display.map((a,i)=>`<tr><td class="mono">${accs.length - display.length + i + 1}</td><td style="color:#ff69b4;font-weight:600;">${esc(a.account_name)}</td><td><span class="region-tag">${esc(a.account_region)}</span></td><td class="mono">${esc(a.uid)}</td><td class="mono">${esc(a.account_id)}</td><td class="mono" style="color:#00ffff;">${esc(a.password)}</td></tr>`).join('');
}

// ACTIVATOR
async function startAct(filename) {
  const threads = parseInt(document.getElementById('aThreads').value) || 10;
  document.getElementById('btnAct').disabled = true;
  closeModal();
  try {
    const r = await fetch(`/activate?threads=${threads}&file=${encodeURIComponent(filename)}`, {method:'POST'}); 
    const j = await r.json();
    if (r.ok) { toast(`🚀 Activation started from ${filename}`); startActPoll(); }
    else { toast('❌ ' + (j.error || 'Failed'), true); document.getElementById('btnAct').disabled = false; }
  } catch(e) { toast('❌ ' + e.message, true); document.getElementById('btnAct').disabled = false; }
}
function startActPoll() { if (pollAct) clearInterval(pollAct); pollAct = setInterval(refreshAct, 1500); refreshAct(); }
async function refreshAct() {
  try {
    const r = await fetch('/activated'); const j = await r.json(); renderAct(j);
    if (!j.running) { document.getElementById('btnAct').disabled = false; if (pollAct) { clearInterval(pollAct); pollAct = null; } }
  } catch(e){}
}
function renderAct(j) {
  const accs = j.activated || []; const fails = j.failed_list || [];
  document.getElementById('aAct').textContent = accs.length;
  document.getElementById('aTarget').textContent = j.total_accounts || 0;
  document.getElementById('aFail').textContent = fails.length;
  document.getElementById('aRun').textContent = j.running ? 'RUN' : 'IDLE';
  const tot = j.total_accounts || 0;
  const pct = tot > 0 ? Math.min(100, ((accs.length + fails.length) / tot) * 100) : 0;
  document.getElementById('aBar').style.width = pct + '%';
  const pill = document.getElementById('aPill'); const stxt = document.getElementById('aText');
  if (j.stopped) { pill.className = 'status-pill pill-stop'; pill.textContent = 'STOPPED'; stxt.textContent = `Stopped · Active: ${accs.length} · Failed: ${fails.length}`; }
  else if (j.running) { pill.className = 'status-pill pill-run'; pill.textContent = 'RUNNING'; stxt.textContent = `Activating... ${accs.length}/${tot} (${fails.length} failed)`; }
  else if (accs.length > 0 || fails.length > 0) { pill.className = 'status-pill pill-done'; pill.textContent = 'DONE'; stxt.textContent = `Active: ${accs.length} · Failed: ${fails.length}`; }
  else { pill.className = 'status-pill pill-idle'; pill.textContent = 'IDLE'; stxt.textContent = 'Ready'; }
  const tb = document.getElementById('aBody');
  if (accs.length === 0) { tb.innerHTML = '<tr><td colspan="6" class="empty">No activated accounts yet.</td></tr>'; }
  else {
    const display = accs.slice(-500);
    tb.innerHTML = display.map((a,i)=>`<tr><td class="mono">${accs.length - display.length + i + 1}</td><td style="color:#ffb700;font-weight:600;">${esc(a.nickname || a.account_name)}</td><td><span class="region-tag">${esc(a.region || a.account_region)}</span></td><td class="mono">${esc(a.uid)}</td><td class="mono">${esc(a.account_id)}</td><td class="mono" style="color:#00ff7f;">Lvl ${esc(a.level || 1)}</td></tr>`).join('');
  }
  const fc = document.getElementById('failCard');
  if (fails.length === 0) { fc.style.display = 'none'; }
  else { fc.style.display = 'block'; document.getElementById('fBody').innerHTML = fails.map((f,i)=>`<tr><td class="mono">${i+1}</td><td class="mono">${esc(f.account_name || f.uid)}</td><td style="color:#ff8a8a;">${esc(f.reason)}</td></tr>`).join(''); }
}

// PROXY
async function refreshProxy() {
  try {
    const r = await fetch('/proxy_status'); const j = await r.json();
    document.getElementById('pSize').textContent = j.pool_size || 0;
    document.getElementById('pFetch').textContent = j.fetching ? 'YES' : 'NO';
    document.getElementById('pUse').textContent = j.use_proxy ? 'ON' : 'OFF';
    const tb = document.getElementById('pBody'); const sample = j.sample || [];
    if (sample.length === 0) { tb.innerHTML = '<tr><td colspan="2" class="empty">No proxies loaded yet.</td></tr>'; }
    else { tb.innerHTML = sample.map((p,i)=>`<tr><td class="mono">${i+1}</td><td class="mono" style="color:#ffb700;">${esc(p)}</td></tr>`).join(''); }
  } catch(e){}
}
function startProxyPoll() { if (pollProxy) clearInterval(pollProxy); pollProxy = setInterval(refreshProxy, 3000); refreshProxy(); }
async function fetchProxy() {
  try { await fetch('/proxy_fetch', {method:'POST'}); toast('⬇️ Fetching proxies...'); setTimeout(refreshProxy, 5000); } catch(e){ toast('❌ '+e.message, true); }
}
function refreshAll() { refreshGen(); refreshAct(); }
async function stopAll() {
  try {
    const r = await fetch('/stop', {method:'POST'}); const j = await r.json();
    if (r.ok) { toast('⛔ Stopped'); document.getElementById('btnGen').disabled = false; document.getElementById('btnAct').disabled = false; setTimeout(refreshAll, 500); }
  } catch(e) { toast('❌ '+e.message, true); }
}
async function resetGen() {
  if (!confirm('Delete all generated accounts and batch files?')) return;
  try { const r = await fetch('/reset_generated', {method:'POST'}); const j = await r.json(); if (r.ok) { toast('🗑️ Generated list cleared'); refreshAll(); } else { toast('❌ ' + (j.error || 'Failed'), true); } } catch(e){ toast('❌ '+e.message, true); }
}
async function clearAct() {
  if (!confirm('Delete all activated accounts and batch files?')) return;
  try { const r = await fetch('/reset_activated', {method:'POST'}); const j = await r.json(); if (r.ok) { toast('🗑️ Activated list cleared'); refreshAll(); } else { toast('❌ ' + (j.error || 'Failed'), true); } } catch(e){ toast('❌ '+e.message, true); }
}
refreshAll();
</script>
</body>
</html>
"""

# ═══════════════════════════════════════════════════════════
#  HTTP HANDLER
# ═══════════════════════════════════════════════════════════
class Handler(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.send_header("Access-Control-Allow-Origin", "*"); self.end_headers(); self.wfile.write(body)
    def _html(self, code, html):
        body = html.encode("utf-8"); self.send_response(code); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def _read_json(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n <= 0: return {}
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception: return {}
    def log_message(self, *a): pass
    
    def _start_forge(self, name, region, count, threads=None, use_proxy=None):
        if use_proxy is not None: CONFIG["use_proxy"] = bool(use_proxy)
        count = max(1, min(count, MAX_COUNT))
        if threads is None: threads = min(count, 10)
        threads = max(1, min(threads, 100))
        with STATE_LOCK:
            if STATE["running"]: return 409, {"error": "Forge already running", "generated_so_far": len(ALL_ACCOUNTS)}
            b_num = get_next_batch_num("account_batch_")
            CONFIG["target"] = count; CONFIG["threads"] = threads; CONFIG["nick_prefix"] = name; CONFIG["region"] = region; CONFIG["nick_max_len"] = max(12, len(name) + 4)
            STOP_GEN.clear()
            STATE.update({"running": True, "target": count, "started_at": int(time.time()), "finished_at": 0, "workers": threads, "region": region, "name_prefix": name, "last_error": None, "failed": 0, "stopped": False, "session_start_count": len(ALL_ACCOUNTS), "batch_num": b_num})
        if CONFIG.get("use_proxy"):
            with PROXY_POOL_LOCK: pool_low = len(PROXY_POOL) < 5
            if pool_low and not PROXY_FETCH_RUNNING: threading.Thread(target=_fetch_free_proxies, daemon=True).start()
            for _ in range(15):
                with PROXY_POOL_LOCK:
                    if len(PROXY_POOL) >= 3: break
                time.sleep(0.5)
        load_proxies()
        t = threading.Thread(target=_forge_worker, args=(count, threads, b_num), daemon=True); t.start()
        return 200, {"ok": True, "message": f"Forge started for {count}", "batch": b_num}

    def _start_activate(self, threads=5, filename=GEN_TOTAL_FILE):
        with STATE_LOCK:
            if ACT_STATE["running"]: return 409, {"error": "Activation already running"}
            
        # Load accounts from selected file
        accounts_to_activate = _load_storage(filename)
        if not accounts_to_activate:
            return 400, {"error": f"No accounts found in {filename}"}
            
        with STATE_LOCK:
            b_num = get_next_batch_num("activate_batch_")
            ALL_FAILED.clear(); STOP_ACT.clear()
            ACT_STATE.update({"running": True, "target": len(accounts_to_activate), "started_at": int(time.time()), "finished_at": 0, "workers": threads, "last_error": None, "active": 0, "failed": 0, "stopped": False, "batch_num": b_num})
            
        t = threading.Thread(target=_activate_worker, args=(accounts_to_activate, threads, b_num), daemon=True); t.start()
        return 200, {"ok": True, "message": f"Activation started for {len(accounts_to_activate)} accounts from {filename}", "batch": b_num}

    def do_GET(self):
        parsed = urlparse(self.path); path = parsed.path.rstrip("/") or "/"; qs = parse_qs(parsed.query)
        if path in ("/", "/dashboard"): return self._html(200, DASHBOARD_HTML)
        
        if path == "/list_files":
            typ = qs.get("type", ["gen"])[0]
            prefix = "account_batch_" if typ == "gen" else "activate_batch_"
            files = []
            for f in os.listdir('.'):
                if f.startswith(prefix) and f.endswith('.json'):
                    files.append({"name": f, "size": round(os.path.getsize(f)/1024, 2)})
            master = GEN_TOTAL_FILE if typ == "gen" else ACT_TOTAL_FILE
            if os.path.exists(master):
                files.append({"name": master, "size": round(os.path.getsize(master)/1024, 2)})
            files.sort(key=lambda x: x['name'])
            return self._json(200, files)
            
        if path == "/get_file":
            fname = qs.get("name", [""])[0]
            if not fname or not os.path.exists(fname) or not fname.endswith('.json'):
                return self._json(404, {"error": "File not found"})
            return self._json(200, _load_storage(fname))
            
        if path == "/api":
            return self._json(200, {"owner": "@kamod_codex", "channel": "@kamod_codex", "endpoints": {"GET /": "Dashboard", "GET /list_files?type=gen":"List Batch Files", "GET /get_file?name=X":"Get File Content"}})
            
        if path == "/account_gen":
            name = qs.get("name", qs.get("nick", ["MasteR~"]))[0]; region = qs.get("regin", qs.get("region", ["IND"]))[0]
            try: count = int(qs.get("count", ["10"])[0])
            except ValueError: return self._json(400, {"error": "count must be integer"})
            t_raw = qs.get("threads", [None])[0]
            try: threads = int(t_raw) if t_raw else None
            except ValueError: threads = None
            up_raw = qs.get("use_proxy", [None])[0]; use_proxy = None
            if up_raw is not None: use_proxy = str(up_raw).lower() in ("1", "true", "yes", "on")
            code, obj = self._start_forge(name, region, count, threads, use_proxy)
            return self._json(code, obj)
            
        if path == "/accounts":
            with STATE_LOCK:
                session_count = len(ALL_ACCOUNTS) - STATE.get("session_start_count", 0)
                return self._json(200, {"count": len(ALL_ACCOUNTS), "target": STATE["target"], "session_count": max(0, session_count), "running": STATE["running"], "failed": STATE["failed"], "stopped": STATE.get("stopped", False), "accounts": list(ALL_ACCOUNTS)})
                
        if path == "/activated":
            with STATE_LOCK:
                return self._json(200, {"running": ACT_STATE["running"], "stopped": ACT_STATE.get("stopped", False), "target": ACT_STATE["target"], "total_accounts": ACT_STATE["target"], "active_count": len(ALL_ACTIVATED), "failed_count": len(ALL_FAILED), "last_error": ACT_STATE["last_error"], "activated": list(ALL_ACTIVATED), "failed_list": list(ALL_FAILED)})
                
        if path == "/proxy_status":
            with PROXY_POOL_LOCK:
                return self._json(200, {"pool_size": len(PROXY_POOL), "last_fetch": PROXY_LAST_FETCH, "fetching": PROXY_FETCH_RUNNING, "use_proxy": CONFIG.get("use_proxy"), "sample": PROXY_POOL[:10]})
                
        if path == "/status":
            with STATE_LOCK:
                return self._json(200, {"generator": dict(STATE), "activator": dict(ACT_STATE), "generated_count": len(ALL_ACCOUNTS), "activated_count": len(ALL_ACTIVATED), "failed_count": len(ALL_FAILED), "proxy_pool": len(PROXY_POOL)})
        return self._json(404, {"error": "not found", "path": path})

    def do_POST(self):
        parsed = urlparse(self.path); path = parsed.path.rstrip("/") or "/"; qs = parse_qs(parsed.query)
        if path == "/forge":
            req = self._read_json(); name = req.get("name", req.get("nick", "MasteR~")); region = req.get("region", req.get("regin", "IND"))
            try: count = int(req.get("count", 10))
            except (TypeError, ValueError): return self._json(400, {"error": "count must be integer"})
            t_raw = req.get("threads")
            try: threads = int(t_raw) if t_raw is not None else None
            except (TypeError, ValueError): threads = None
            use_proxy = req.get("use_proxy", None)
            code, obj = self._start_forge(name, region, count, threads, use_proxy)
            return self._json(code, obj)
            
        if path == "/activate":
            t_raw = qs.get("threads", [None])[0]
            try: threads = int(t_raw) if t_raw else 5
            except ValueError: threads = 5
            threads = max(1, min(threads, 100))
            filename = qs.get("file", [GEN_TOTAL_FILE])[0]
            code, obj = self._start_activate(threads, filename)
            return self._json(code, obj)
            
        if path == "/proxy_fetch":
            threading.Thread(target=_fetch_free_proxies, daemon=True).start()
            return self._json(200, {"ok": True, "message": "Proxy fetch started"})
        if path == "/stop":
            STOP_GEN.set(); STOP_ACT.set()
            with STATE_LOCK:
                STATE["running"] = False; STATE["stopped"] = True; ACT_STATE["running"] = False; ACT_STATE["stopped"] = True
            return self._json(200, {"ok": True, "message": "Stopped"})
            
        if path == "/reset_generated":
            with STATE_LOCK:
                if STATE["running"]: return self._json(409, {"error": "Forge running"})
                ALL_ACCOUNTS.clear(); ALL_FAILED.clear()
                if os.path.exists(GEN_TOTAL_FILE): os.remove(GEN_TOTAL_FILE)
                for f in os.listdir('.'):
                    if f.startswith("account_batch_") and f.endswith('.json'): os.remove(f)
                STATE.update({"target":0,"started_at":0,"finished_at":0,"last_error":None,"region":"IND","name_prefix":"MasteR~","failed":0,"stopped":False,"session_start_count":0})
            return self._json(200, {"ok": True, "message": "Generated cleared"})
            
        if path == "/reset_activated":
            with STATE_LOCK:
                if ACT_STATE["running"]: return self._json(409, {"error": "Activation running"})
                ALL_ACTIVATED.clear(); ALL_FAILED.clear()
                if os.path.exists(ACT_TOTAL_FILE): os.remove(ACT_TOTAL_FILE)
                for f in os.listdir('.'):
                    if f.startswith("activate_batch_") and f.endswith('.json'): os.remove(f)
                ACT_STATE.update({"active":0,"failed":0,"target":0,"last_error":None,"stopped":False})
            return self._json(200, {"ok": True, "message": "Activated cleared"})
        return self._json(404, {"error": "not found"})

def main():
    port = int(os.environ.get("PORT", 8000))
    print("💀 KAMOD DEVILS WILL RISE 💀")
    print("Owner  : @kamod_codex")
    print("Channel: @kamod_codex")
    print(f"Dashboard : http://0.0.0.0:{port}/")
    print(f"API       : http://0.0.0.0:{port}/api")
    print()
    
    print("[PROXY] Initializing proxy pool...")
    threading.Thread(target=_fetch_free_proxies, daemon=True).start()
    threading.Thread(target=_proxy_watchdog, daemon=True).start()
    print("[PROXY] watchdog started")
    
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    try: 
        server.serve_forever()
    except KeyboardInterrupt: 
        print("\n[!] Shutdown")
        server.shutdown()

if __name__ == "__main__":
    main()