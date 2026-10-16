#!/usr/bin/env python3
"""
KAMOD WILL RISE — Forge + Activator Dashboard
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

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ═══════════════════════════════════════════════════════════
#  IP ROTATOR
# ═══════════════════════════════════════════════════════════
class IPRotator:
    REGION_IP_CIDRS = {
        "BD":  ["27.147.128.0/17","37.111.192.0/19","49.0.32.0/20","59.152.96.0/20",
                "114.130.0.0/17","115.127.0.0/17","119.30.32.0/20","123.49.0.0/18",
                "103.220.220.0/22","103.108.140.0/22","103.242.20.0/22"],
        "IND": ["1.6.0.0/15","1.38.0.0/15","14.96.0.0/15","27.4.0.0/14","27.56.0.0/13",
                "49.36.0.0/14","103.25.12.0/22","103.56.12.0/22","115.99.0.0/16"],
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
                if not cidrs:
                    cls._cache[region] = []
                else:
                    hosts = []
                    for cidr in cidrs:
                        try:
                            net = ipaddress.ip_network(cidr, strict=False)
                            total = 2 ** (32 - net.prefixlen)
                            if total > 5000:
                                for _ in range(2000):
                                    hosts.append(str(net.network_address + random.randint(1, total - 2)))
                            else:
                                hosts.extend([str(ip) for ip in net.hosts()])
                        except Exception:
                            continue
                    cls._cache[region] = hosts
            pool = cls._cache.get(region) or []
            if not pool:
                return f"{random.randint(103,223)}.{random.randint(10,250)}.{random.randint(10,250)}.{random.randint(10,250)}"
            return random.choice(pool)


# ═══════════════════════════════════════════════════════════
#  GEN URLs
# ═══════════════════════════════════════════════════════════
URL_GUEST_REGISTER = "https://ffmconnect.live.gop.garenanow.com/api/v2/oauth/guest:register"
URL_TOKEN_GRANT    = "https://ffmconnect.live.gop.garenanow.com/api/v2/oauth/guest/token:grant"
URL_MAJOR_LOGIN    = "https://loginbp.ppmainecoonghj.com/MajorLogin"
URL_MAJOR_REGISTER = "https://loginbp.ppmainecoonghj.com/MajorRegister"
URL_NEWBIE_CHOICE  = "https://loginbp.ppmainecoonghj.com/ChooseNewbieChoice"


# ═══════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════
MAIN_KEY = bytes.fromhex(
    '326565343438313965396234353938383435313431303637'
    '6232383136323138373464306435643761663964386637653030'
    '6331653534373135623764316533'
)
AES_KEY = bytes([89,103,38,116,99,37,68,69,117,104,54,37,90,99,94,56])
AES_IV  = bytes([54,111,121,90,68,114,50,50,69,51,121,99,104,106,77,37])
CLIENT_SECRET = "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3"
APP_ID        = 100067
RELEASE_VER   = "OB55"
GAME_VERSION  = "2.132.4"

HTTP_TIMEOUT  = (5, 10)
FAIL_WAIT     = 0.3
MAX_RETRIES   = 3
POOL_CONN     = 100
POOL_MAX      = 200
PACE_PER_PROXY = 0.3
PROXY_COOLDOWN_429 = 20
PROXY_COOLDOWN_503 = 45
MAX_COUNT = 1000


# ═══════════════════════════════════════════════════════════
#  DATA POOLS
# ═══════════════════════════════════════════════════════════
DEVICES = [
    ("Asus ASUS_AI2501_B", "Android OS 12 / API-31 (SP1A.210812.016.C2/user.dxu.20260701.180839)", "Adreno (TM) 640", "OpenGL ES 3.2"),
    ("Redmi Note 12 Pro",  "Android OS 13 / API-33 (TP1A.220624.014)", "Adreno (TM) 618", "OpenGL ES 3.2"),
    ("Samsung SM-M135F",   "Android OS 13 / API-33 (TP1A.220624.014)", "Mali-G68", "OpenGL ES 3.2"),
    ("Realme RMX3630",     "Android OS 12 / API-31 (SP1A.210812.016)", "Adreno (TM) 610", "OpenGL ES 3.2"),
    ("Vivo V2149",         "Android OS 13 / API-33 (TP1A.220624.014)", "Adreno (TM) 642L", "OpenGL ES 3.2"),
    ("OnePlus CPH2411",    "Android OS 13 / API-33 (TP1A.220624.014)", "Adreno (TM) 730", "OpenGL ES 3.2"),
]


# ═══════════════════════════════════════════════════════════
#  CONFIG + GLOBALS
# ═══════════════════════════════════════════════════════════
CONFIG = {
    "target":        100,
    "threads":       15,
    "nick_prefix":   "MasteR~",
    "nick_max_len":  12,
    "use_proxy":     False,
    "proxy_file":    "working_proxies.txt",
    "region":        "IND",
}

ALL_ACCOUNTS = []
ALL_ACTIVATED = []
ALL_FAILED = []

COUNTER_LOCK = threading.Lock()
PROXY_LOCK   = threading.Lock()
PACE_LOCK    = {}
LAST_PACE    = {}

TOTAL = 0
PROXIES = [None]
PROXY_COOLDOWN = {}
CURRENT_PROXY = None
STATE_LOCK = threading.Lock()

STOP_GEN = threading.Event()
STOP_ACT = threading.Event()

STATE = {
    "running":     False,
    "target":      0,
    "started_at":  0,
    "finished_at": 0,
    "workers":     0,
    "region":      "IND",
    "name_prefix": "MasteR~",
    "last_error":  None,
    "failed":      0,
}

ACT_STATE = {
    "running":     False,
    "target":      0,
    "started_at":  0,
    "finished_at": 0,
    "workers":     0,
    "last_error":  None,
    "active":      0,
    "failed":      0,
}


# ═══════════════════════════════════════════════════════════
#  PROXY
# ═══════════════════════════════════════════════════════════
def load_proxies():
    global PROXIES, CURRENT_PROXY
    PROXIES = []
    if not CONFIG["use_proxy"]:
        PROXIES = [None]; CURRENT_PROXY = None
        return
    pf = CONFIG["proxy_file"]
    if not os.path.exists(pf):
        PROXIES = [None]; CURRENT_PROXY = None
        return
    with open(pf, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                PROXIES.append({"http": line, "https": line})
    PROXIES = PROXIES or [None]
    CURRENT_PROXY = PROXIES[0]

def _pk(p):
    return "__direct__" if p is None else p.get("http", "?")

def get_proxy():
    global CURRENT_PROXY
    if len(PROXIES) <= 1:
        return PROXIES[0] if PROXIES else None
    if CURRENT_PROXY is not None:
        with PROXY_LOCK:
            if time.time() >= PROXY_COOLDOWN.get(_pk(CURRENT_PROXY), 0):
                return CURRENT_PROXY
    now = time.time()
    with PROXY_LOCK:
        healthy = [p for p in PROXIES if now >= PROXY_COOLDOWN.get(_pk(p), 0)]
        return random.choice(healthy) if healthy else random.choice(PROXIES)

def cooldown(p, sec):
    if p is None: return
    with PROXY_LOCK:
        k = _pk(p)
        PROXY_COOLDOWN[k] = max(PROXY_COOLDOWN.get(k, 0), time.time() + sec)

def pace_proxy(p):
    k = _pk(p)
    if k not in PACE_LOCK:
        PACE_LOCK[k] = threading.Lock()
    with PACE_LOCK[k]:
        now = time.time()
        el = now - LAST_PACE.get(k, 0)
        if el < PACE_PER_PROXY:
            time.sleep(PACE_PER_PROXY - el)
        LAST_PACE[k] = time.time()


# ═══════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════
def gen_password():
    return hashlib.sha256(
        ''.join(random.choice(string.ascii_letters + string.digits)
                for _ in range(32)).encode()
    ).hexdigest().upper()

def gen_nickname():
    prefix = CONFIG["nick_prefix"]
    max_len = CONFIG["nick_max_len"]
    avail = max_len - len(prefix)
    if avail < 1:
        return prefix[:max_len].encode()
    digits = "".join(random.choice("0123456789") for _ in range(avail))
    return f"{prefix}{digits}".encode()

def enc_aes(data):
    return AES.new(AES_KEY, AES.MODE_CBC, AES_IV).encrypt(pad(data, AES.block_size))

def encode_f14(s):
    ks = [0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,
          0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,
          0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,
          0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30]
    return bytes(ord(c) ^ ks[i % len(ks)] for i, c in enumerate(s))


# ═══════════════════════════════════════════════════════════
#  TYPEDEFS
# ═══════════════════════════════════════════════════════════
def _tf(t): return {'type': t, 'name': ''}

typedef_login = {
    '3':_tf('bytes'),'4':_tf('bytes'),'5':_tf('int'),
    '7':_tf('bytes'),'8':_tf('bytes'),'9':_tf('bytes'),
    '10':_tf('bytes'),'11':_tf('bytes'),'12':_tf('int'),
    '13':_tf('int'),'14':_tf('bytes'),'15':_tf('bytes'),
    '16':_tf('int'),'17':_tf('bytes'),'18':_tf('bytes'),
    '19':_tf('bytes'),'20':_tf('bytes'),'21':_tf('bytes'),
    '22':_tf('bytes'),'23':_tf('bytes'),'24':_tf('bytes'),
    '25':_tf('bytes'),'26':_tf('bytes'),'29':_tf('bytes'),
    '30':_tf('int'),'41':_tf('bytes'),'42':_tf('bytes'),
    '57':_tf('bytes'),'60':_tf('int'),'61':_tf('int'),
    '62':_tf('int'),'63':_tf('int'),'64':_tf('int'),
    '65':_tf('int'),'66':_tf('int'),'67':_tf('int'),
    '73':_tf('int'),'74':_tf('bytes'),'76':_tf('int'),
    '77':_tf('bytes'),'78':_tf('int'),'79':_tf('int'),
    '81':_tf('bytes'),'83':_tf('bytes'),'85':_tf('int'),
    '86':_tf('bytes'),'87':_tf('int'),'88':_tf('int'),
    '92':_tf('int'),'93':_tf('bytes'),'94':_tf('bytes'),
    '96':_tf('bytes'),'97':_tf('int'),'98':_tf('int'),
    '99':_tf('bytes'),'100':_tf('bytes'),'102':_tf('bytes'),
    '104':_tf('int'),'105':_tf('int'),'106':_tf('bytes'),
    '107':_tf('bytes'),
}
typedef_reg = {
    '1':_tf('bytes'),'2':_tf('bytes'),'3':_tf('bytes'),
    '5':_tf('int'),'6':_tf('int'),'7':_tf('int'),
    '13':_tf('int'),'14':_tf('bytes'),'15':_tf('bytes'),
    '16':_tf('int'),'20':_tf('bytes'),'21':_tf('int'),
    '22':_tf('bytes'),
}
typedef_newbie = {'1':_tf('int'),'2':_tf('int'),'3':_tf('int')}

FIELD_22 = bytes.fromhex(
    "4747524501010100620200001052aa0d669c6a368f08338060d2ee0690053af84a41edcd3558556ec10f24f4"
    "6c93ac64ca41a16732c46a2cb071246a79b8929032f9e1b6f4ef331bd53cabf29b09b97349a46e9863c0314e"
    "1a0d80819fef8aabf03876b3d037db354a7ccb5c1bce96411fb3753f6f50e44c69c4ed617fa30efb8ffc0517"
    "ff2f636739be1f304d999cfd6fd48bf69454199794c3dc88f55a4bdbd66534d5a061359cdfd1fb680cd37918"
    "df9fdb3cf7d80067b0a3506c90063cf62b2ccec11e23913a2fd7c4ef091331967bb518a5ad1e551146b90821"
    "be800883abadde39d6c80a5d798611466c748f075481806c5842ce45e6bd4e3368ec08fe2ec41ceb880cd862"
    "49eb71693f79f0bccf9e590c3fae12519fe08c7a1905d0927690109e0df28574bb14847225db1a59230e6662"
    "ed7730e15ff9a6c815cb41b420edeada735a4b03e181037c37c2c850257311df2f07b0a56e759372cbd0268e"
    "3f13a292ee4373e38ab5096e0342a5e0d7fec6da2bbc265d74baadd2b24ee4f74862f82c21d6694bac53f8ce"
    "80312a30068a6276a641c19b11d0305c6fe2f531ac7de578b29f543697f5c73663e6f23aa15277b6122dcd4d"
    "4171e38f9ac0b173f39c58416a16c5c1f4a35acd065ce78f449cf538a249339e763272d458e4ed86c976591a"
    "9c066b3a37111e44091eb6b5a795249f3e5145db022a6055f2cc675936391312f688f89627845df222a91156"
    "555225be36f9714a0ba50246d0f003bda3c9c1292ab73b4f79635ddd023218eda93a302d79e023404c143965"
    "44a930b98ed54771aca7fec10d095587685b473e81a9619764fad9256529dcd6e911f4f4629612287d4ee3ec"
    "5389f6ec4ec020b0e2aac017232a9197be9e46239ce690fe5d4872b2e98e651510c971667f3aca8b59f3e9d5"
    "0e43"
)


# ═══════════════════════════════════════════════════════════
#  HEADERS
# ═══════════════════════════════════════════════════════════
HEADERS_MSDK = {
    "User-Agent": "GarenaMSDK/4.0.44(ASUS_AI2501_B ;Android 12;en;US;app 2.132.1 2019118525;)",
    "Content-Type": "application/json; charset=utf-8",
    "Connection": "keep-alive",
}
HEADERS_LOGINBP = {
    'Host': 'loginbp.ppmainecoonghj.com',
    'User-Agent': 'UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)',
    'Accept': '*/*', 'Accept-Encoding': 'deflate, gzip',
    'Authorization': 'Bearer', 'X-GA': 'v1 1',
    'ReleaseVersion': RELEASE_VER,
    'Content-Type': 'application/x-www-form-urlencoded',
    'X-Unity-Version': '2018.4.12f1',
}


# ═══════════════════════════════════════════════════════════
#  SESSION
# ═══════════════════════════════════════════════════════════
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
    return {
        '3': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S').encode(),
        '4': b'free fire', '5': 1, '7': GAME_VERSION.encode(),
        '8': os_str.encode(),
        '9': b'Handheld', '10': b'Jio', '11': b'WIFI',
        '12': 1280, '13': 720, '14': b'240',
        '15': b'x86-64 SSE3 SSE4.1 SSE4.2 AVX AVX2 | 2400 | 4',
        '16': random.choice([5951, 6000, 6100, 5500]),
        '17': gpu.encode(),
        '18': gpu_full.encode(),
        '19': f'Google|{uuid.uuid4()}'.encode(),
        '20': ip.encode(),
        '21': b'en', '22': open_id.encode(),
        '23': b'4', '24': b'Handheld',
        '25': model.encode(),
        '26': region.encode(),
        '29': access_token.encode(), '30': 1,
        '41': b'Jio', '42': b'WIFI',
        '57': b'1ac4b80ecf0478a44203bf8fac6120f5',
        '60': 30000, '61': 30000, '62': 2519, '63': 243,
        '64': 32357, '65': 34308, '66': 32357, '67': 34308, '73': 1,
        '74': b'/data/app/~~iw-K-GR3srU7dLE-UxJ4bg==/com.dts.freefiremax-kbPhw3SUYautW0I_oayB_A==/lib/arm',
        '76': 2,
        '77': b'428775ab8c8845bd341b5357ec61d15e|/data/app/~~iw-K-GR3srU7dLE-UxJ4bg==/com.dts.freefiremax-kbPhw3SUYautW0I_oayB_A==/base.apk',
        '78': 2, '79': 1, '81': b'32', '83': b'2019118525', '85': 3,
        '86': b'OpenGLES3', '87': 4095, '88': 4,
        '92': random.choice([19788, 20000, 21000]),
        '93': b'android_max',
        '94': b'KqsHT2gyPt7vUCc9SCjv2ioi3WEZSEL86ErvXB38suVVK/Z4IVt78ESl/r2S15C1pqu/j6ZmgFL7HbwoFiiVconX08ooKiisQffvEAPCo/C+Lahr',
        '96': b'{"cur_rate":null,"support_etc2":true}',
        '97': 1, '98': 1, '99': b'4', '100': b'4', '102': b'',
        '104': 77149, '105': 1,
        '106': b'https://dl.cdn.freefiremobile.com/live/ABHotUpdates/|https://dl-core.cdn.freefiremobile.com/live/ABHotUpdates/|6b2078db9d22dd98f8e9386a39af8462',
        '107': b'c8e41b7a93f02d56e1a94c7b8203f5d1',
    }


# ═══════════════════════════════════════════════════════════
#  REGISTER ONE
# ═══════════════════════════════════════════════════════════
def register_one(worker_id):
    global TOTAL

    if STOP_GEN.is_set():
        return None

    session = get_session()
    proxy = get_proxy()

    for attempt in range(1, MAX_RETRIES + 1):
        if STOP_GEN.is_set():
            return None

        try:
            pace_proxy(proxy)
            password = gen_password()
            reg_body = json.dumps(
                {"app_id": APP_ID, "client_type": 2, "password": password, "source": 2},
                separators=(",", ":")
            )
            reg_sig = hmac.new(MAIN_KEY, reg_body.encode(), hashlib.sha256).hexdigest()

            r = session.post(URL_GUEST_REGISTER,
                             headers={**HEADERS_MSDK, "Authorization": "Signature " + reg_sig},
                             data=reg_body, verify=False, proxies=proxy,
                             timeout=HTTP_TIMEOUT)

            if r.status_code == 429:
                cooldown(proxy, PROXY_COOLDOWN_429); proxy = get_proxy(); continue
            if r.status_code == 503:
                cooldown(proxy, PROXY_COOLDOWN_503); proxy = get_proxy(); continue
            if r.status_code != 200:
                raise Exception(f"reg HTTP {r.status_code}")

            uid = r.json()["data"]["uid"]

            dev_id = f"02-{uuid.uuid4()}"
            grant_body = {
                "client_id": APP_ID, "client_secret": CLIENT_SECRET,
                "client_type": 2, "device_id": dev_id, "password": password,
                "response_type": "token", "uid": int(uid),
            }
            r2 = session.post(URL_TOKEN_GRANT, headers=HEADERS_MSDK,
                              json=grant_body, verify=False, proxies=proxy,
                              timeout=HTTP_TIMEOUT)
            if r2.status_code != 200:
                raise Exception(f"grant HTTP {r2.status_code}")
            gd = r2.json()["data"]
            access_token = gd["access_token"]
            open_id      = gd["open_id"]

            hdr = dict(HEADERS_LOGINBP)
            hdr["X-GA-SV"] = str(int(time.time()))
            login_meta = _build_login_meta(open_id, access_token)
            try:
                session.post(URL_MAJOR_LOGIN, headers=hdr,
                             data=enc_aes(blackboxprotobuf.encode_message(login_meta, typedef_login)),
                             verify=False, proxies=proxy, timeout=HTTP_TIMEOUT)
            except Exception:
                pass

            nick = gen_nickname()

            reg_msg = {
                '1': nick, '2': access_token.encode(), '3': open_id.encode(),
                '5': 102000007, '6': 4, '7': 1, '13': 1,
                '14': encode_f14(open_id), '15': b'en', '16': 2,
                '20': GAME_VERSION.encode(), '21': 1, '22': FIELD_22,
            }
            rr = session.post(URL_MAJOR_REGISTER, headers=hdr,
                              data=enc_aes(blackboxprotobuf.encode_message(reg_msg, typedef_reg)),
                              verify=False, proxies=proxy, timeout=HTTP_TIMEOUT)

            if rr.status_code != 200:
                raise Exception(f"majorreg HTTP {rr.status_code}")

            res, _ = blackboxprotobuf.decode_message(rr.content)
            account_id = None
            if isinstance(res, dict):
                account_id = res.get('3') or res.get(b'3')
            if not account_id:
                raise Exception("no account_id")

            try:
                session.post(URL_NEWBIE_CHOICE, headers=hdr,
                             data=enc_aes(blackboxprotobuf.encode_message(
                                 {'1': int(account_id), '2': 2, '3': 3}, typedef_newbie)),
                             verify=False, proxies=proxy, timeout=HTTP_TIMEOUT)
            except Exception:
                pass

            with COUNTER_LOCK:
                TOTAL += 1

            nick_str = nick.decode('utf-8', errors='ignore')
            acc = {
                "account_name":   nick_str,
                "account_region": CONFIG.get("region", "IND"),
                "uid":            str(uid),
                "account_id":     str(account_id),
                "password":       str(password),
                "status":         "registered",
            }
            ALL_ACCOUNTS.append(acc)
            print(f"[GEN+] {nick_str} | uid={uid} | acc={account_id}")
            return acc

        except requests.exceptions.Timeout:
            time.sleep(FAIL_WAIT)
        except requests.exceptions.ProxyError:
            cooldown(proxy, 30); proxy = get_proxy()
        except Exception as e:
            with STATE_LOCK:
                STATE["last_error"] = str(e)
            time.sleep(FAIL_WAIT)

    with STATE_LOCK:
        STATE["failed"] += 1
    return None


# ═══════════════════════════════════════════════════════════
#  FORGE WORKER — Success-target loop
# ═══════════════════════════════════════════════════════════
def _forge_worker(target_count, threads):
    """Keep spawning until success == target_count or STOP."""
    try:
        with ThreadPoolExecutor(max_workers=threads) as ex:
            pending = set()
            submitted = 0
            max_attempts = max(target_count * 3, target_count + 20)

            while True:
                if STOP_GEN.is_set():
                    break

                # Fill worker slots
                while len(pending) < threads and submitted < max_attempts:
                    pending.add(ex.submit(register_one, submitted % threads + 1))
                    submitted += 1

                if not pending:
                    break

                done, pending = _wait(pending, return_when=_FC)

                # Stop if we hit target
                if len(ALL_ACCOUNTS) >= target_count:
                    for p in pending:
                        p.cancel()
                    break

                # Stop if we exhausted max attempts
                if submitted >= max_attempts and not pending:
                    break
    finally:
        with STATE_LOCK:
            STATE["running"] = False
            STATE["finished_at"] = int(time.time())


# ═══════════════════════════════════════════════════════════
#  ══════════════ ACTIVATOR ══════════════
# ═══════════════════════════════════════════════════════════
REGIONAL_LOGIN_HOSTS = {
    "IND": "https://client.ind.freefiremobile.com/",
    "BD":  "https://client.bd.freefiremobile.com/",
    "SG":  "https://client.sg.freefiremobile.com/",
    "BR":  "https://client.br.freefiremobile.com/",
    "US":  "https://client.us.freefiremobile.com/",
    "EU":  "https://client.eu.freefiremobile.com/",
    "ME":  "https://client.me.freefiremobile.com/",
}
MAJORLOGIN_FALLBACK_HOSTS = [
    "https://client.ind.freefiremobile.com/",
    "https://client.bd.freefiremobile.com/",
    "https://loginbp.ppmainecoonghj.com/",
    "https://loginbp.ggmainecoonghj.com/",
    "https://loginbp.ggblueshark.com/",
    "https://loginbp.commonmainecoonghj.com/",
    "https://indnetwork.ggblueshark.com/",
    "https://indgigateway.ggblueshark.com/",
]
ACT_AES_KEY = b'Yg&tc%DEuh6%Zc^8'
ACT_AES_IV  = b'6oyZDr22E3ychjM%'

BATCH_SIZE       = 30
BATCH_INTERVAL   = 0.5
ONLINE_DURATION  = 3.0
LOGIN_CONCURRENCY = 60
MAX_CONNECTIONS  = 1000
MAX_KEEPALIVE    = 500
HOST_RACE_TIMEOUT = 6.0

_act_client = None


def _get_act_client():
    global _act_client
    if _act_client is None:
        _act_client = httpx.AsyncClient(
            verify=False,
            timeout=httpx.Timeout(15.0, connect=6.0),
            limits=httpx.Limits(
                max_connections=MAX_CONNECTIONS,
                max_keepalive_connections=MAX_KEEPALIVE,
            ),
            follow_redirects=True,
            http2=False,
        )
    return _act_client


def _act_aes_encrypt(payload: bytes) -> bytes:
    cipher = AES.new(ACT_AES_KEY, AES.MODE_CBC, ACT_AES_IV)
    return cipher.encrypt(pad(payload, AES.block_size))


def _encode_varint(n: int) -> bytes:
    if n < 0: return b''
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n: b |= 0x80
        out.append(b)
        if not n: break
    return bytes(out)


def _build_proto(fields: dict) -> bytes:
    parts = []
    for k, v in fields.items():
        if isinstance(v, dict):
            nested = _build_proto(v)
            parts.append(_encode_varint((k << 3) | 2) + _encode_varint(len(nested)) + nested)
        elif isinstance(v, int):
            parts.append(_encode_varint((k << 3) | 0) + _encode_varint(v))
        elif isinstance(v, (str, bytes)):
            ev = v.encode() if isinstance(v, str) else v
            parts.append(_encode_varint((k << 3) | 2) + _encode_varint(len(ev)) + ev)
    return b''.join(parts)


def _build_majorlogin_payload(open_id, access_token, platform, client_version, device_info):
    try:
        payload_dict = {
            3:  str(datetime.now())[:-7],
            4:  "free fire",
            5:  "1",
            7:  str(client_version) if client_version else "1.132.9",
            8:  str(device_info.get("system_software", "Android OS 15 / API-35")),
            9:  "Handheld",
            10: "Telkomsel",
            11: "CarrierDataNetwork",
            12: str(device_info.get("screen_width", 1639)),
            13: str(device_info.get("screen_height", 720)),
            14: str(device_info.get("screen_dpi", 320)),
            15: str(device_info.get("processor_details", "ARM64 FP ASIMD AES | 2000 | 8")),
            16: str(device_info.get("memory", 5653)),
            17: str(device_info.get("gpu_renderer", "Mali-G52 MC2")),
            18: "OpenGL ES 3.2 v1.r49p1-03bet0.19498e0ae1d5dac223383c39a2e58f04",
            19: str(device_info.get("unique_device_id", f"Google|{uuid.uuid4()}")),
            20: str(device_info.get("client_ip", "182.5.135.225")),
            21: "en",
            22: str(open_id),
            23: str(platform),
            24: "Handheld",
            25: str(device_info.get("model", "Xiaomi 2409BRN2CY")),
            26: "ID",
            29: str(access_token),
            30: "1",
            41: "Telkomsel",
            42: "4G",
            57: "7428b253defc164018c604a1ebbfebdf",
            60: "109278", 61: "55402", 62: "868", 64: "55927",
            65: "109278", 66: "55927", 67: "109278", 73: "2",
            74: "/data/app/~~6Cw028g_ld-8Z0z2qhrOLA==/com.dts.freefireth-i3wiaEmpx8CbiRVhUMx_ag==/lib/arm64",
            76: "1",
            77: "b8e0cd5e295eee42f5860d3c86e483dd|/data/app/~~6Cw028g_ld-8Z0z2qhrOLA==/com.dts.freefireth-i3wiaEmpx8CbiRVhUMx_ag==/base.apk",
            78: "3", 79: "2", 81: "64", 83: "2019121229",
            85: "3", 86: "OpenGLES2", 87: "8191", 88: str(platform),
            90: "Cirebon", 91: "JB", 92: "14466", 93: "android",
            94: "KqsHTyb7yHjsAiyNWUUZa0DSOD6U0AhDQ76smAo1WeHHHpSmJ8KMRyRrxb2ttgJqO9YOqO/K6AORAvDMAX/qBS8+JahIkrM7kHfzlfULbgRAoZ9r",
            95: "111207",
            96: "{\"cur_rate\":[60,90,120],\"support_etc2\":false}",
            97: "1", 98: "1", 99: str(platform), 100: str(platform),
            102: "D]C\x15\x05T\x0eU3", 103: "1", 104: "52837", 105: "1",
            106: "https://dl.gmc.freefiremobile.com/live/ABHotUpdates/|https://core-gmc.freefiremobile.com/live/ABHotUpdates/|211c933168f55902c7dfbfd8c4e2957d",
            107: "1.3fb8adbf45f44ce9",
        }
        raw_proto = _build_proto(payload_dict)
        return _act_aes_encrypt(raw_proto)
    except Exception as e:
        print(f"[ACT] payload build error: {e}")
        return None


def _parse_majorlogin(raw: bytes):
    def _parse_fields(data):
        out = {}
        i = 0; n = len(data)
        while i < n:
            try:
                key = 0; shift = 0
                while True:
                    if i >= n: return out
                    b = data[i]; i += 1
                    key |= (b & 0x7F) << shift
                    if not (b & 0x80): break
                    shift += 7
                    if shift > 63: return out
                fn = key >> 3; wire = key & 0x07
                if wire == 0:
                    val = 0; shift = 0
                    while True:
                        if i >= n: return out
                        b = data[i]; i += 1
                        val |= (b & 0x7F) << shift
                        if not (b & 0x80): break
                        shift += 7
                        if shift > 63: return out
                    out[fn] = val
                elif wire == 2:
                    ln = 0; shift = 0
                    while True:
                        if i >= n: return out
                        b = data[i]; i += 1
                        ln |= (b & 0x7F) << shift
                        if not (b & 0x80): break
                        shift += 7
                        if shift > 63: return out
                    if i + ln > n: return out
                    out[fn] = data[i:i+ln]; i += ln
                elif wire == 5: i += 4
                elif wire == 1: i += 8
                else: return out
            except Exception:
                return out
        return out

    for offset in range(min(200, len(raw))):
        try:
            f = _parse_fields(raw[offset:])
            if 1 in f and 2 in f and 8 in f:
                return {
                    "account_id": f.get(1),
                    "region":     f.get(2, b"").decode("utf-8", "ignore") if isinstance(f.get(2), bytes) else str(f.get(2)),
                    "token":      f.get(8, b"").decode("utf-8", "ignore") if isinstance(f.get(8), bytes) else str(f.get(8)),
                    "url":        f.get(10, b"").decode("utf-8", "ignore") if isinstance(f.get(10), bytes) else "",
                    "server_time": f.get(21, 0),
                    "aes_ak":     f.get(22, b""),
                    "iv_i":       f.get(23, b""),
                }
        except Exception:
            continue
    return None


def _parse_getlogin(raw: bytes):
    def _parse_fields(data):
        out = {}
        i = 0; n = len(data)
        while i < n:
            try:
                key = 0; shift = 0
                while True:
                    if i >= n: return out
                    b = data[i]; i += 1
                    key |= (b & 0x7F) << shift
                    if not (b & 0x80): break
                    shift += 7
                    if shift > 63: return out
                fn = key >> 3; wire = key & 0x07
                if wire == 0:
                    val = 0; shift = 0
                    while True:
                        if i >= n: return out
                        b = data[i]; i += 1
                        val |= (b & 0x7F) << shift
                        if not (b & 0x80): break
                        shift += 7
                        if shift > 63: return out
                    out[fn] = val
                elif wire == 2:
                    ln = 0; shift = 0
                    while True:
                        if i >= n: return out
                        b = data[i]; i += 1
                        ln |= (b & 0x7F) << shift
                        if not (b & 0x80): break
                        shift += 7
                        if shift > 63: return out
                    if i + ln > n: return out
                    out[fn] = data[i:i+ln]; i += ln
                elif wire == 5: i += 4
                elif wire == 1: i += 8
                else: return out
            except Exception:
                return out
        return out

    for offset in range(min(200, len(raw))):
        try:
            f = _parse_fields(raw[offset:])
            if 4 in f or 14 in f or 32 in f:
                def _s(x):
                    if isinstance(x, bytes):
                        return x.decode("utf-8", "ignore")
                    return str(x) if x is not None else ""
                return {
                    "nickname": _s(f.get(4, "")),
                    "functional_addrs": _s(f.get(14, "")),
                    "informational_addrs": _s(f.get(32, "")),
                    "level": f.get(6, 1) if isinstance(f.get(6), int) else 1,
                    "region": _s(f.get(3, "")),
                }
        except Exception:
            continue
    return None


_ACT_VERSION_CACHE = None
_ACT_VERSION_TIME = 0
_ACT_VERSION_TTL = 1800.0


async def _act_version_config(region="IND"):
    global _ACT_VERSION_CACHE, _ACT_VERSION_TIME
    now = time.time()
    if _ACT_VERSION_CACHE and (now - _ACT_VERSION_TIME) < _ACT_VERSION_TTL:
        return _ACT_VERSION_CACHE

    reg = (region or "IND").upper()
    regional_url = REGIONAL_LOGIN_HOSTS.get(reg, REGIONAL_LOGIN_HOSTS["IND"])
    FALLBACK = ("OB55", "1.132.9", regional_url)

    try:
        client = _get_act_client()
        api_url = (
            "https://version.ggwhitehawk.com/live/ver.php"
            "?version=1.132.9"
            "&lang=hi&device=android&channel=android"
            "&appstore=googleplay&region=IND"
            "&whitelist_version=1.3.0&whitelist_sp_version=1.0.0"
        )
        r = await client.get(api_url, timeout=6.0)
        if r.status_code == 200:
            data = r.json()
            server_url = data.get("server_url") or regional_url
            remote_version = data.get("remote_version")
            latest = data.get("latest_release_version")
            if server_url and remote_version and latest:
                _ACT_VERSION_CACHE = (latest, remote_version, server_url)
                _ACT_VERSION_TIME = now
                return _ACT_VERSION_CACHE
    except Exception:
        pass

    _ACT_VERSION_CACHE = FALLBACK
    _ACT_VERSION_TIME = now
    return _ACT_VERSION_CACHE


async def _get_access_token(uid, password):
    client = _get_act_client()
    url = "https://100067.connect.garena.com/oauth/guest/token/grant"
    hdrs = {
        "Host": "100067.connect.garena.com",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 12; SM-G998B Build/SP1A.210812.016)",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "close",
    }
    data = {
        "uid": uid, "password": password,
        "response_type": "token",
        "client_type": "2",
        "client_secret": CLIENT_SECRET,
        "client_id": "100067",
    }
    for _ in range(3):
        try:
            r = await client.post(url, headers=hdrs, data=data)
            if r.status_code == 200:
                d = r.json()
                oid = d.get("open_id"); tok = d.get("access_token")
                plat = d.get("platform", 4)
                if oid and tok:
                    return oid, tok, plat
            if r.status_code == 429:
                await asyncio.sleep(0.8); continue
        except Exception:
            pass
        await asyncio.sleep(0.3)
    return None


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
    if len(parts) == 4 and all(p.isdigit() for p in parts):
        return hostname
    try:
        loop = asyncio.get_running_loop()
        info = await loop.getaddrinfo(hostname, None, family=socket.AF_INET)
        if info: return info[0][4][0]
    except Exception:
        pass
    return hostname


def _optimize_tcp(sock):
    try:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    except Exception:
        pass


_ACT_SEMAPHORE = None


def _get_sem():
    global _ACT_SEMAPHORE
    if _ACT_SEMAPHORE is None:
        _ACT_SEMAPHORE = asyncio.Semaphore(LOGIN_CONCURRENCY)
    return _ACT_SEMAPHORE


def _random_act_device(uid_seed):
    brand, model, gpu, os_ver = random.choice([
        ("Samsung", "SM-G998B",  "Adreno (TM) 660", "Android OS 12 / API-31"),
        ("Xiaomi",  "2201122G",  "Adreno (TM) 730", "Android OS 13 / API-33"),
        ("Realme",  "RMX3700",   "Mali-G710",       "Android OS 14 / API-34"),
        ("OnePlus", "CPH2451",   "Adreno (TM) 740", "Android OS 13 / API-33"),
        ("OPPO",    "CPH2611",   "Adreno (TM) 720", "Android OS 14 / API-34"),
    ])
    return {
        "unique_device_id": f"Google|{uuid.uuid4()}",
        "brand": brand, "model": model,
        "gpu_renderer": gpu, "system_software": os_ver,
        "screen_width":  random.choice([1080, 1440, 720, 1280]),
        "screen_height": random.choice([2400, 3200, 1600, 2400]),
        "screen_dpi":    str(random.randint(300, 420)),
        "memory":        random.randint(2800, 6500),
        "processor_details": f"ARM64 FP ASIMD AES VMH | {random.randint(2200, 3200)} | {random.randint(6, 12)}",
        "client_ip": IPRotator.get_random_ip("IND"),
    }


async def _activate_single(acc, idx, total):
    if STOP_ACT.is_set():
        return False

    uid_input  = str(acc.get("uid", ""))
    password   = acc.get("password", "")
    input_nick = acc.get("account_name", "")

    try:
        async with _get_sem():
            if STOP_ACT.is_set():
                return False

            release_version, client_version, server_url = await _act_version_config("IND")
            tg = await _get_access_token(uid_input, password)
            if tg is None:
                raise Exception("token grant failed")
            open_id, access_token, platform = tg

            device_info = _random_act_device(uid_input)
            payload = _build_majorlogin_payload(open_id, access_token, platform,
                                                client_version, device_info)
            if payload is None:
                raise Exception("payload build failed")

            client = _get_act_client()

            candidates = [server_url.rstrip("/") + "/"] + [h.rstrip("/") + "/" for h in MAJORLOGIN_FALLBACK_HOSTS]

            async def _try_ml(base):
                try:
                    h = {
                        "User-Agent": "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
                        "Content-Type": "application/x-www-form-urlencoded",
                        "X-Unity-Version": "2018.4.12f1",
                        "X-GA": "v1 1",
                        "ReleaseVersion": release_version,
                    }
                    r = await client.post(base + "MajorLogin", headers=h, content=payload)
                    if r.status_code != 200 or len(r.content) < 20:
                        return None
                    parsed = _parse_majorlogin(r.content)
                    if parsed and parsed.get("account_id") and parsed.get("token"):
                        return parsed
                except Exception:
                    return None
                return None

            ml = None
            tasks = [asyncio.create_task(_try_ml(b)) for b in candidates]
            try:
                done, pending = await asyncio.wait(tasks, timeout=HOST_RACE_TIMEOUT,
                                                   return_when=asyncio.FIRST_COMPLETED)
                for t in done:
                    try:
                        r = t.result()
                        if r is not None:
                            ml = r
                            for p in pending: p.cancel()
                            break
                    except Exception:
                        continue
                if ml is None:
                    for t in pending:
                        try:
                            r = await t
                            if r is not None:
                                ml = r; break
                        except Exception:
                            continue
            finally:
                for t in tasks:
                    if not t.done(): t.cancel()

            if ml is None:
                raise Exception("MajorLogin failed")

            region = ml.get("region") or "IND"

            async def _try_gl(base):
                try:
                    h = {
                        "User-Agent": "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
                        "Content-Type": "application/x-www-form-urlencoded",
                        "X-Unity-Version": "2018.4.12f1",
                        "X-GA": "v1 1",
                        "ReleaseVersion": release_version,
                        "Authorization": f"Bearer {ml['token']}",
                    }
                    r = await client.post(base + "GetLoginData", headers=h, content=payload)
                    if r.status_code != 200:
                        return None
                    parsed = _parse_getlogin(r.content)
                    if parsed and (parsed.get("functional_addrs") or parsed.get("informational_addrs")):
                        return parsed
                except Exception:
                    return None
                return None

            gl_candidates = []
            reg_host = REGIONAL_LOGIN_HOSTS.get(region.upper())
            if reg_host: gl_candidates.append(reg_host.rstrip("/") + "/")
            if ml.get("url"): gl_candidates.append(ml["url"].rstrip("/") + "/")
            for h in MAJORLOGIN_FALLBACK_HOSTS:
                n = h.rstrip("/") + "/"
                if n not in gl_candidates: gl_candidates.append(n)

            gl = None
            tasks = [asyncio.create_task(_try_gl(b)) for b in gl_candidates]
            try:
                done, pending = await asyncio.wait(tasks, timeout=HOST_RACE_TIMEOUT,
                                                   return_when=asyncio.FIRST_COMPLETED)
                for t in done:
                    try:
                        r = t.result()
                        if r is not None:
                            gl = r
                            for p in pending: p.cancel()
                            break
                    except Exception:
                        continue
                if gl is None:
                    for t in pending:
                        try:
                            r = await t
                            if r is not None:
                                gl = r; break
                        except Exception:
                            continue
            finally:
                for t in tasks:
                    if not t.done(): t.cancel()

            if gl is None:
                raise Exception("GetLoginData failed")

            addrs = gl.get("functional_addrs")
            if not addrs:
                raise Exception("no functional_addrs")

            ip, port = addrs.split(":")
            rip = await _resolve_host(ip)
            reader, writer = await asyncio.open_connection(rip, int(port))
            sock = writer.get_extra_info("socket")
            if sock: _optimize_tcp(sock)

            tcp_hex = await _build_tcp_startup_packet(
                ml["account_id"], ml["token"], ml.get("server_time", int(time.time())),
                ml.get("aes_ak", ACT_AES_KEY), ml.get("iv_i", ACT_AES_IV),
                region=region, typ="OnLine",
            )
            writer.write(bytes.fromhex(tcp_hex))
            await writer.drain()

            try:
                ka = await _send_keep_alive(region)
                if ka and not writer.is_closing():
                    writer.write(ka)
                    await asyncio.wait_for(writer.drain(), timeout=1.5)
            except Exception:
                pass

            start = time.time()
            while time.time() - start < ONLINE_DURATION:
                if STOP_ACT.is_set():
                    break
                try:
                    data = await asyncio.wait_for(reader.read(4096), timeout=0.3)
                    if not data: break
                except asyncio.TimeoutError:
                    try:
                        if not writer.is_closing():
                            writer.write(await _send_keep_alive(region))
                            await writer.drain()
                    except Exception:
                        break
                except Exception:
                    break

            try:
                writer.close()
                await asyncio.wait_for(writer.wait_closed(), timeout=0.8)
            except Exception:
                pass

            nick = gl.get("nickname") or input_nick or f"Player_{ml['account_id']}"
            lvl  = gl.get("level", 1)
            reg  = gl.get("region") or region

            entry = {
                "account_name": nick,
                "account_region": reg,
                "uid": uid_input,
                "account_id": str(ml["account_id"]),
                "password": password,
                "nickname": nick,
                "level": lvl,
                "status": "activated",
                "activated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            ALL_ACTIVATED.append(entry)
            with STATE_LOCK:
                ACT_STATE["active"] += 1
            print(f"[ACT+] {nick} | uid={uid_input} | lvl={lvl} | reg={reg}")
            return True

    except Exception as e:
        with STATE_LOCK:
            ACT_STATE["failed"] += 1
        ALL_FAILED.append({
            "uid": uid_input,
            "account_name": input_nick,
            "reason": str(e)[:120],
        })
        print(f"[ACT✗] {input_nick or uid_input} | {str(e)[:80]}")
        return False


async def _activate_batch(batch, start_idx, total):
    tasks = []
    for i, acc in enumerate(batch):
        if STOP_ACT.is_set():
            break
        tasks.append(_activate_single(acc, start_idx + i + 1, total))
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


def _run_activator_sync(accounts, threads):
    global _act_client, _ACT_SEMAPHORE
    _act_client = None
    _ACT_SEMAPHORE = None

    async def _main():
        total = len(accounts)
        for i in range(0, total, BATCH_SIZE):
            if STOP_ACT.is_set():
                break
            batch = accounts[i:i + BATCH_SIZE]
            await _activate_batch(batch, i, total)
            await asyncio.sleep(BATCH_INTERVAL)

    try:
        asyncio.run(_main())
    except Exception as e:
        with STATE_LOCK:
            ACT_STATE["last_error"] = str(e)
    finally:
        with STATE_LOCK:
            ACT_STATE["running"] = False
            ACT_STATE["finished_at"] = int(time.time())


def _activate_worker(threads):
    try:
        accounts = list(ALL_ACCOUNTS)
        if not accounts:
            with STATE_LOCK:
                ACT_STATE["last_error"] = "No accounts to activate"
            return
        _run_activator_sync(accounts, threads)
    finally:
        with STATE_LOCK:
            ACT_STATE["running"] = False


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
  </div>

  <!-- ═══ GENERATOR ═══ -->
  <div id="panelGen">
    <div class="card">
      <h2>⚙️ Account Generator</h2>
      <div class="row">
        <div class="field">
          <label>Name Prefix</label>
          <input id="gName" type="text" value="MasteR~" maxlength="12">
        </div>
        <div class="field">
          <label>Region</label>
          <select id="gRegion">
            <option value="IND">IND — India</option>
            <option value="BD">BD — Bangladesh</option>
            <option value="PK">PK — Pakistan</option>
            <option value="ID">ID — Indonesia</option>
            <option value="SG">SG — Singapore</option>
          </select>
        </div>
        <div class="field">
          <label>Count</label>
          <input id="gCount" type="number" value="10" min="1" max="1000">
        </div>
        <div class="field">
          <label>Threads</label>
          <input id="gThreads" type="number" value="5" min="1" max="50">
        </div>
      </div>
      <div class="btn-row">
        <button id="btnGen" onclick="startGen()">🚀 Start Generate</button>
        <button class="danger" id="btnStopGen" onclick="stopAll()">⛔ STOP</button>
        <button class="alt" onclick="refreshAll()">🔄 Refresh</button>
        <button class="danger" onclick="resetAll()">🗑️ Reset All</button>
        <button class="gold" onclick="downloadGen()">⬇️ Download Generated</button>
      </div>
    </div>

    <div class="card">
      <h2>📊 Generator Status</h2>
      <div class="stats">
        <div class="stat"><div class="val" id="gGen">0</div><div class="lbl">Generated</div></div>
        <div class="stat"><div class="val" id="gTarget">0</div><div class="lbl">Target</div></div>
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
      <h2>📦 Generated Accounts</h2>
      <div class="scroll">
        <table>
          <thead><tr><th>#</th><th>Name</th><th>Region</th><th>UID</th><th>Acc ID</th><th>Password</th></tr></thead>
          <tbody id="gBody"><tr><td colspan="6" class="empty">No accounts yet.</td></tr></tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- ═══ ACTIVATOR ═══ -->
  <div id="panelAct" class="hide">
    <div class="card">
      <h2>🚀 Account Activator</h2>
      <p style="color:#888;font-size:0.85rem;margin-bottom:14px;">
        Activates all currently generated accounts. Logs each account online.
      </p>
      <div class="row">
        <div class="field">
          <label>Threads</label>
          <input id="aThreads" type="number" value="5" min="1" max="50">
        </div>
        <div class="field">
          <label>Batch Size</label>
          <input id="aBatch" type="number" value="30" min="1" max="200">
        </div>
      </div>
      <div class="btn-row">
        <button class="gold" id="btnAct" onclick="startAct()">🚀 Start Activation</button>
        <button class="danger" id="btnStopAct" onclick="stopAll()">⛔ STOP</button>
        <button class="alt" onclick="refreshAll()">🔄 Refresh</button>
        <button class="gold" onclick="downloadAct()">⬇️ Download Activated</button>
        <button class="danger" onclick="clearAct()">🗑️ Clear Activation</button>
      </div>
    </div>

    <div class="card">
      <h2>📊 Activator Status</h2>
      <div class="stats">
        <div class="stat"><div class="val" id="aAct">0</div><div class="lbl">Activated</div></div>
        <div class="stat"><div class="val" id="aTarget">0</div><div class="lbl">Total</div></div>
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
      <h2>◉ Activated Accounts</h2>
      <div class="scroll">
        <table>
          <thead><tr><th>#</th><th>Name</th><th>Region</th><th>UID</th><th>Acc ID</th><th>Level</th></tr></thead>
          <tbody id="aBody"><tr><td colspan="6" class="empty">No activated accounts yet.</td></tr></tbody>
        </table>
      </div>
    </div>

    <div class="card" id="failCard" style="display:none;">
      <h2 style="color:#e63946;">✕ Failed Accounts</h2>
      <div class="scroll">
        <table>
          <thead><tr><th>#</th><th>UID / Name</th><th>Reason</th></tr></thead>
          <tbody id="fBody"></tbody>
        </table>
      </div>
    </div>
  </div>

</div>

<div class="toast" id="toast">Done</div>

<script>
let pollGen = null, pollAct = null;

function toast(msg, isErr=false) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show' + (isErr ? ' err' : '');
  setTimeout(() => t.className = 'toast', 2500);
}

function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}

function switchTab(tab) {
  document.getElementById('panelGen').classList.toggle('hide', tab !== 'gen');
  document.getElementById('panelAct').classList.toggle('hide', tab !== 'act');
  document.getElementById('tabGen').classList.toggle('active', tab === 'gen');
  document.getElementById('tabAct').classList.toggle('active', tab === 'act');
  refreshAll();
}

async function startGen() {
  const name    = document.getElementById('gName').value.trim() || 'MasteR~';
  const region  = document.getElementById('gRegion').value;
  const count   = parseInt(document.getElementById('gCount').value) || 10;
  const threads = parseInt(document.getElementById('gThreads').value) || 5;

  document.getElementById('btnGen').disabled = true;
  try {
    const url = `/account_gen?name=${encodeURIComponent(name)}&regin=${encodeURIComponent(region)}&count=${count}&threads=${threads}`;
    const r = await fetch(url);
    const j = await r.json();
    if (r.ok) { toast(`🚀 Forge started: ${count} accounts`); startGenPoll(); }
    else { toast('❌ ' + (j.error || 'Failed'), true); document.getElementById('btnGen').disabled = false; }
  } catch(e) { toast('❌ ' + e.message, true); document.getElementById('btnGen').disabled = false; }
}

function startGenPoll() {
  if (pollGen) clearInterval(pollGen);
  pollGen = setInterval(refreshGen, 1500);
  refreshGen();
}

async function refreshGen() {
  try {
    const r = await fetch('/accounts');
    const j = await r.json();
    renderGen(j);
    if (!j.running) {
      document.getElementById('btnGen').disabled = false;
      if (pollGen) { clearInterval(pollGen); pollGen = null; }
    }
  } catch(e){}
}

function renderGen(j) {
  const accs = j.accounts || [];
  document.getElementById('gGen').textContent    = accs.length;
  document.getElementById('gTarget').textContent = j.target || 0;
  document.getElementById('gFail').textContent   = j.failed || 0;
  document.getElementById('gRun').textContent    = j.running ? 'RUN' : 'IDLE';

  const pct = j.target > 0 ? Math.min(100, (accs.length / j.target) * 100) : 0;
  document.getElementById('gBar').style.width = pct + '%';

  const pill = document.getElementById('gPill');
  const stxt = document.getElementById('gText');
  if (j.stopped) {
    pill.className = 'status-pill pill-stop'; pill.textContent = 'STOPPED';
    stxt.textContent = `Stopped at ${accs.length}/${j.target}`;
  } else if (j.running) {
    pill.className = 'status-pill pill-run'; pill.textContent = 'RUNNING';
    stxt.textContent = `Generating... ${accs.length}/${j.target}`;
  } else if (accs.length > 0) {
    pill.className = 'status-pill pill-done'; pill.textContent = 'DONE';
    stxt.textContent = `Completed ${accs.length} accounts`;
  } else {
    pill.className = 'status-pill pill-idle'; pill.textContent = 'IDLE';
    stxt.textContent = 'Ready';
  }

  const tb = document.getElementById('gBody');
  if (accs.length === 0) {
    tb.innerHTML = '<tr><td colspan="6" class="empty">No accounts yet.</td></tr>';
    return;
  }
  tb.innerHTML = accs.map((a,i)=>`
    <tr>
      <td class="mono">${i+1}</td>
      <td style="color:#ff69b4;font-weight:600;">${esc(a.account_name)}</td>
      <td><span class="region-tag">${esc(a.account_region)}</span></td>
      <td class="mono">${esc(a.uid)}</td>
      <td class="mono">${esc(a.account_id)}</td>
      <td class="mono" style="color:#00ffff;">${esc(a.password)}</td>
    </tr>`).join('');
}

async function startAct() {
  const threads = parseInt(document.getElementById('aThreads').value) || 5;
  document.getElementById('btnAct').disabled = true;
  try {
    const r = await fetch(`/activate?threads=${threads}`, {method:'POST'});
    const j = await r.json();
    if (r.ok) { toast('🚀 Activation started'); startActPoll(); }
    else { toast('❌ ' + (j.error || 'Failed'), true); document.getElementById('btnAct').disabled = false; }
  } catch(e) { toast('❌ ' + e.message, true); document.getElementById('btnAct').disabled = false; }
}

function startActPoll() {
  if (pollAct) clearInterval(pollAct);
  pollAct = setInterval(refreshAct, 1500);
  refreshAct();
}

async function refreshAct() {
  try {
    const r = await fetch('/activated');
    const j = await r.json();
    renderAct(j);
    if (!j.running) {
      document.getElementById('btnAct').disabled = false;
      if (pollAct) { clearInterval(pollAct); pollAct = null; }
    }
  } catch(e){}
}

function renderAct(j) {
  const accs = j.activated || [];
  const fails = j.failed_list || [];
  document.getElementById('aAct').textContent    = accs.length;
  document.getElementById('aTarget').textContent = j.total_accounts || 0;
  document.getElementById('aFail').textContent   = fails.length;
  document.getElementById('aRun').textContent    = j.running ? 'RUN' : 'IDLE';

  const tot = j.total_accounts || 0;
  const pct = tot > 0 ? Math.min(100, ((accs.length + fails.length) / tot) * 100) : 0;
  document.getElementById('aBar').style.width = pct + '%';

  const pill = document.getElementById('aPill');
  const stxt = document.getElementById('aText');
  if (j.stopped) {
    pill.className = 'status-pill pill-stop'; pill.textContent = 'STOPPED';
    stxt.textContent = `Stopped · Active: ${accs.length} · Failed: ${fails.length}`;
  } else if (j.running) {
    pill.className = 'status-pill pill-run'; pill.textContent = 'RUNNING';
    stxt.textContent = `Activating... ${accs.length}/${tot} (${fails.length} failed)`;
  } else if (accs.length > 0 || fails.length > 0) {
    pill.className = 'status-pill pill-done'; pill.textContent = 'DONE';
    stxt.textContent = `Active: ${accs.length} · Failed: ${fails.length}`;
  } else {
    pill.className = 'status-pill pill-idle'; pill.textContent = 'IDLE';
    stxt.textContent = 'Ready';
  }

  const tb = document.getElementById('aBody');
  if (accs.length === 0) {
    tb.innerHTML = '<tr><td colspan="6" class="empty">No activated accounts yet.</td></tr>';
  } else {
    tb.innerHTML = accs.map((a,i)=>`
      <tr>
        <td class="mono">${i+1}</td>
        <td style="color:#ffb700;font-weight:600;">${esc(a.nickname || a.account_name)}</td>
        <td><span class="region-tag">${esc(a.region || a.account_region)}</span></td>
        <td class="mono">${esc(a.uid)}</td>
        <td class="mono">${esc(a.account_id)}</td>
        <td class="mono" style="color:#00ff7f;">Lvl ${esc(a.level || 1)}</td>
      </tr>`).join('');
  }

  const fc = document.getElementById('failCard');
  if (fails.length === 0) { fc.style.display = 'none'; }
  else {
    fc.style.display = 'block';
    document.getElementById('fBody').innerHTML = fails.map((f,i)=>`
      <tr>
        <td class="mono">${i+1}</td>
        <td class="mono">${esc(f.account_name || f.uid)}</td>
        <td style="color:#ff8a8a;">${esc(f.reason)}</td>
      </tr>`).join('');
  }
}

function refreshAll() { refreshGen(); refreshAct(); }

async function stopAll() {
  try {
    const r = await fetch('/stop', {method:'POST'});
    const j = await r.json();
    if (r.ok) {
      toast('⛔ Stopped');
      document.getElementById('btnGen').disabled = false;
      document.getElementById('btnAct').disabled = false;
      setTimeout(refreshAll, 500);
    } else toast('❌ ' + (j.error || 'Failed'), true);
  } catch(e) { toast('❌ '+e.message, true); }
}

async function resetAll() {
  if (!confirm('Clear all accounts & state?')) return;
  try {
    const r = await fetch('/reset', {method:'POST'});
    const j = await r.json();
    if (r.ok) { toast('🗑️ Reset done'); refreshAll(); }
    else toast('❌ ' + (j.error || 'Failed'), true);
  } catch(e){ toast('❌ '+e.message, true); }
}

async function clearAct() {
  if (!confirm('Clear activated & failed list?')) return;
  try {
    const r = await fetch('/reset_activated', {method:'POST'});
    const j = await r.json();
    if (r.ok) { toast('🗑️ Activation cleared'); refreshAll(); }
    else toast('❌ ' + (j.error || 'Failed'), true);
  } catch(e){ toast('❌ '+e.message, true); }
}

async function downloadGen() {
  try {
    const r = await fetch('/accounts');
    const j = await r.json();
    if (!j.accounts || j.accounts.length === 0) { toast('⚠️ No accounts to download', true); return; }
    const blob = new Blob([JSON.stringify(j.accounts, null, 2)], {type:'application/json'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `kamod_generated_${j.region}_${Date.now()}.json`;
    a.click(); URL.revokeObjectURL(a.href);
    toast(`⬇️ Downloaded ${j.accounts.length} accounts`);
  } catch(e){ toast('❌ '+e.message, true); }
}

async function downloadAct() {
  try {
    const r = await fetch('/activated');
    const j = await r.json();
    if (!j.activated || j.activated.length === 0) { toast('⚠️ No activated accounts', true); return; }
    const blob = new Blob([JSON.stringify(j.activated, null, 2)], {type:'application/json'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `kamod_activated_${Date.now()}.json`;
    a.click(); URL.revokeObjectURL(a.href);
    toast(`⬇️ Downloaded ${j.activated.length} activated`);
  } catch(e){ toast('❌ '+e.message, true); }
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
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _html(self, code, html):
        body = html.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n <= 0: return {}
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    def log_message(self, *a): pass

    def _start_forge(self, name, region, count, threads=None):
        count = max(1, min(count, MAX_COUNT))
        if threads is None: threads = min(count, 5)
        threads = max(1, min(threads, 50))

        with STATE_LOCK:
            if STATE["running"]:
                return 409, {"error": "Forge already running",
                             "generated_so_far": len(ALL_ACCOUNTS)}
            CONFIG["target"]       = count
            CONFIG["threads"]      = threads
            CONFIG["nick_prefix"]  = name
            CONFIG["region"]       = region
            CONFIG["nick_max_len"] = max(12, len(name) + 4)
            ALL_ACCOUNTS.clear()
            load_proxies()
            STOP_GEN.clear()
            STATE.update({
                "running": True, "target": count,
                "started_at": int(time.time()), "finished_at": 0,
                "workers": threads, "region": region,
                "name_prefix": name, "last_error": None, "failed": 0,
                "stopped": False,
            })
        t = threading.Thread(target=_forge_worker, args=(count, threads), daemon=True)
        t.start()
        return 200, {"ok": True, "message": f"Forge started for {count}",
                     "name": name, "region": region, "count": count, "threads": threads}

    def _start_activate(self, threads=5):
        with STATE_LOCK:
            if ACT_STATE["running"]:
                return 409, {"error": "Activation already running"}
            if not ALL_ACCOUNTS:
                return 400, {"error": "No accounts. Generate first."}
            ALL_ACTIVATED.clear()
            ALL_FAILED.clear()
            STOP_ACT.clear()
            ACT_STATE.update({
                "running": True, "target": len(ALL_ACCOUNTS),
                "started_at": int(time.time()), "finished_at": 0,
                "workers": threads, "last_error": None,
                "active": 0, "failed": 0, "stopped": False,
            })
        t = threading.Thread(target=_activate_worker, args=(threads,), daemon=True)
        t.start()
        return 200, {"ok": True, "message": "Activation started",
                     "total": len(ALL_ACCOUNTS), "threads": threads}

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = parse_qs(parsed.query)

        if path in ("/", "/dashboard"):
            return self._html(200, DASHBOARD_HTML)

        if path == "/api":
            return self._json(200, {
                "owner": "@kamod_codex", "channel": "@kamod_codex",
                "endpoints": {
                    "GET  /":                                    "Dashboard",
                    "GET  /account_gen?name=X&regin=IN&count=10":"Start generator",
                    "GET  /accounts":                            "List generated",
                    "POST /activate?threads=5":                  "Start activator",
                    "GET  /activated":                           "List activated + failed",
                    "POST /stop":                                "Stop all",
                    "POST /reset":                               "Clear all",
                    "POST /reset_activated":                     "Clear activation",
                },
            })

        if path == "/account_gen":
            name   = qs.get("name",  qs.get("nick", ["MasteR~"]))[0]
            region = qs.get("regin", qs.get("region", ["IND"]))[0]
            try: count = int(qs.get("count", ["10"])[0])
            except ValueError: return self._json(400, {"error": "count must be integer"})
            t_raw = qs.get("threads", [None])[0]
            try: threads = int(t_raw) if t_raw else None
            except ValueError: threads = None
            code, obj = self._start_forge(name, region, count, threads)
            return self._json(code, obj)

        if path == "/accounts":
            with STATE_LOCK:
                return self._json(200, {
                    "owner": "@kamod_codex", "channel": "@kamod_codex",
                    "count": len(ALL_ACCOUNTS), "target": STATE["target"],
                    "running": STATE["running"], "failed": STATE["failed"],
                    "stopped": STATE.get("stopped", False),
                    "region": STATE["region"], "name_prefix": STATE["name_prefix"],
                    "accounts": list(ALL_ACCOUNTS),
                })

        if path == "/activated":
            with STATE_LOCK:
                return self._json(200, {
                    "owner": "@kamod_codex", "channel": "@kamod_codex",
                    "running": ACT_STATE["running"],
                    "stopped": ACT_STATE.get("stopped", False),
                    "target": ACT_STATE["target"],
                    "total_accounts": len(ALL_ACCOUNTS),
                    "active_count": len(ALL_ACTIVATED),
                    "failed_count": len(ALL_FAILED),
                    "last_error": ACT_STATE["last_error"],
                    "activated": list(ALL_ACTIVATED),
                    "failed_list": list(ALL_FAILED),
                })

        if path == "/status":
            with STATE_LOCK:
                return self._json(200, {
                    "generator": dict(STATE),
                    "activator": dict(ACT_STATE),
                    "generated_count": len(ALL_ACCOUNTS),
                    "activated_count": len(ALL_ACTIVATED),
                    "failed_count":     len(ALL_FAILED),
                })

        return self._json(404, {"error": "not found", "path": path})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = parse_qs(parsed.query)

        if path == "/forge":
            req = self._read_json()
            name   = req.get("name",   req.get("nick", "MasteR~"))
            region = req.get("region", req.get("regin", "IND"))
            try: count = int(req.get("count", 10))
            except (TypeError, ValueError):
                return self._json(400, {"error": "count must be integer"})
            t_raw = req.get("threads")
            try: threads = int(t_raw) if t_raw is not None else None
            except (TypeError, ValueError): threads = None
            CONFIG["use_proxy"] = bool(req.get("use_proxy", False))
            code, obj = self._start_forge(name, region, count, threads)
            return self._json(code, obj)

        if path == "/activate":
            t_raw = qs.get("threads", [None])[0]
            try: threads = int(t_raw) if t_raw else 5
            except ValueError: threads = 5
            threads = max(1, min(threads, 50))
            code, obj = self._start_activate(threads)
            return self._json(code, obj)

        if path == "/stop":
            STOP_GEN.set()
            STOP_ACT.set()
            with STATE_LOCK:
                STATE["running"] = False
                STATE["stopped"] = True
                ACT_STATE["running"] = False
                ACT_STATE["stopped"] = True
            return self._json(200, {"ok": True, "message": "Stopped"})

        if path == "/reset":
            with STATE_LOCK:
                if STATE["running"] or ACT_STATE["running"]:
                    return self._json(409, {"error": "Busy"})
                STOP_GEN.clear()
                STOP_ACT.clear()
                ALL_ACCOUNTS.clear(); ALL_ACTIVATED.clear(); ALL_FAILED.clear()
                STATE.update({"target":0,"started_at":0,"finished_at":0,
                              "last_error":None,"region":"IND","name_prefix":"MasteR~","failed":0,"stopped":False})
                ACT_STATE.update({"target":0,"started_at":0,"finished_at":0,
                                  "last_error":None,"active":0,"failed":0,"stopped":False})
            return self._json(200, {"ok": True, "message": "Cleared"})

        if path == "/reset_activated":
            with STATE_LOCK:
                if ACT_STATE["running"]:
                    return self._json(409, {"error": "Activation running"})
                ALL_ACTIVATED.clear(); ALL_FAILED.clear()
                ACT_STATE.update({"active":0,"failed":0,"target":0,"last_error":None,"stopped":False})
            return self._json(200, {"ok": True, "message": "Activation list cleared"})

        return self._json(404, {"error": "not found"})


# ═══════════════════════════════════════════════════════════
#  RUN
# ═══════════════════════════════════════════════════════════
def main():
    port = int(os.environ.get("PORT", 8000))
    print("💀 KAMOD DEVILS WILL RISE 💀")
    print("Owner  : @kamod_codex")
    print("Channel: @kamod_codex")
    print(f"Dashboard : http://0.0.0.0:{port}/")
    print(f"API       : http://0.0.0.0:{port}/api")
    print()
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Shutdown")
        server.shutdown()


if __name__ == "__main__":
    main()
