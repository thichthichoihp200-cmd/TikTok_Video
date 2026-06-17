import os
import time
import random
import requests
import subprocess
import warnings
import sys
import re
import unicodedata
from datetime import datetime, timedelta, timezone

warnings.filterwarnings("ignore")

API_BASE = "https://gateway.golike.net/api"

# ===== ANSI FIX =====
ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*m')

def strip_ansi(s):
    return ANSI_ESCAPE.sub('', s)

def real_length(s):
    s = strip_ansi(s)
    length = 0
    for ch in s:
        if unicodedata.east_asian_width(ch) in ("F","W"):
            length += 2
        else:
            length += 1
    return length

# ===== COLOR =====
class Color:
    RED="\033[1;91m";GREEN="\033[1;92m";YELLOW="\033[1;93m"
    BLUE="\033[1;94m";PURPLE="\033[1;95m";CYAN="\033[1;96m"
    WHITE="\033[1;97m";GRAY="\033[1;90m";RESET="\033[0m"

RAINBOW=[Color.RED,Color.YELLOW,Color.GREEN,Color.CYAN,Color.BLUE,Color.PURPLE]

# ===== VIDEO CONFIG =====
VIDEO_FILE = "tiktok_links.txt"
WATCHED_FILE = "watched_videos.txt"

# ===== SESSION =====
session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})

# ===== IP (FIX ISP) =====
IP_INFO=("Unknown","Unknown","0.0.0.0")

def clean_isp(isp):
    if isp.startswith("AS"):
        return " ".join(isp.split(" ")[1:])
    return isp

def get_ip_country_once():
    global IP_INFO
    try:
        r = session.get("https://ipinfo.io/json", timeout=5).json()
        country = r.get("country", "Unknown")
        isp = r.get("org", "Unknown")
        ip = r.get("ip", "")
        IP_INFO = (country, isp, ip)
    except:
        pass

def get_ip_country():
    return IP_INFO

# ===== VIDEO =====
def resolve_tiktok_url(url):
    try:
        r = session.get(url, allow_redirects=True, timeout=10)
        return r.url
    except:
        return url

def load_video_links():
    if not os.path.exists(VIDEO_FILE):
        return []
    with open(VIDEO_FILE, "r") as f:
        return [line.strip() for line in f if line.strip()]

def load_watched():
    if not os.path.exists(WATCHED_FILE):
        return set()
    return set(open(WATCHED_FILE).read().splitlines())

def save_watched(watched):
    with open(WATCHED_FILE, "w") as f:
        for i in watched:
            f.write(i + "\n")

def save_video_link():
    while True:
        link = input(Color.CYAN+"Nhập link video (Enter để dừng): "+Color.RESET).strip()
        if not link:
            break

        if not link.startswith("http"):
            print(Color.RED+"❌ Link không hợp lệ!"+Color.RESET)
            continue

        print(Color.YELLOW+"🔄 Đang xử lý..."+Color.RESET)
        real = resolve_tiktok_url(link)
        print(Color.GREEN+"➡️ "+real+Color.RESET)

        links = load_video_links()

        if real in links:
            print(Color.YELLOW+"⚠️ Đã tồn tại\n"+Color.RESET)
            continue

        with open(VIDEO_FILE, "a") as f:
            f.write(real + "\n")

        print(Color.GREEN+"✔ Đã lưu\n"+Color.RESET)

def watch_videos(name, stats, acc_id):
    watched = load_watched()
    links = list(dict.fromkeys(load_video_links()))
    if not links:
        return

    available = [l for l in links if l not in watched]

    if not available:
        watched.clear()
        available = links

    num = random.randint(3, 5)
    if len(available) < num:
        num = len(available)

    selected = random.sample(available, num)

    for link in selected:
        watched.add(link)
        save_watched(watched)

        try:
            subprocess.run(
                ["am","start","-a","android.intent.action.VIEW","-d",link],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except:
            pass

        delay = random.randint(15, 25)

        for i in range(1, delay + 1):
            draw_box(
                name,"WATCH VIDEO",link,
                0,0,0,i,delay,
                stats.get(acc_id, {}).get("xu", 0),
                "🎬 Đang lướt video..."
            )
            time.sleep(1)

# ===== KEEP AWAKE =====
def keep_awake():
    try:
        subprocess.run(["termux-wake-lock"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except: pass

def prevent_sleep():
    try:
        subprocess.run(["svc","power","stayon","true"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except: pass

# ===== TIME =====
def get_vn_time():
    now=datetime.now(timezone.utc)+timedelta(hours=7)
    days=["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ Nhật"]
    return f"{days[now.weekday()]}, {now.strftime('%d/%m/%Y %H:%M:%S')}"

# ===== PING =====
last_ping=0;last_ping_time=0
def get_ping():
    global last_ping,last_ping_time
    if time.time()-last_ping_time<5: return last_ping
    try:
        t=time.time()
        session.get("https://1.1.1.1",timeout=3)
        last_ping=int((time.time()-t)*1000)
    except: last_ping=999
    last_ping_time=time.time()
    return last_ping

# ===== NETWORK SPEED =====
last_speed="0 KB/s";last_speed_time=0

def get_network_speed():
    global last_speed,last_speed_time
    if time.time()-last_speed_time<10:return last_speed
    try:
        s=time.time()
        r=session.get("https://www.google.com",timeout=5)
        size=len(r.content)
        d=time.time()-s
        sp=size/d
        last_speed=f"{sp/1024/1024:.2f} MB/s" if sp>1024*1024 else f"{sp/1024:.2f} KB/s"
    except:last_speed="0 KB/s"
    last_speed_time=time.time()
    return last_speed

def get_speed_color(s):
    try:
        if "MB" in s:
            v=float(s.replace(" MB/s",""))
            return Color.GREEN if v>=1 else Color.YELLOW if v>=0.3 else Color.RED
        if "KB" in s:
            v=float(s.replace(" KB/s",""))
            return Color.GREEN if v>=500 else Color.YELLOW if v>=100 else Color.RED
    except: pass
    return Color.GRAY

def get_speed_icon(s):
    try:
        if "MB" in s:
            v=float(s.replace(" MB/s",""))
            return "🚀" if v>=1 else "⚡" if v>=0.3 else "🐢"
        if "KB" in s:
            v=float(s.replace(" KB/s",""))
            return "🚀" if v>=500 else "⚡" if v>=100 else "🐢"
    except: pass
    return "❓"

# ===== BAR =====
def dot_bar(c,t,l=10):
    if t<=0:return ""
    c=min(c,t)
    filled=int(l*c/t)
    bar=""
    for i in range(l):
        if i<filled:
            bar+="█"
        else:
            bar+="░"
    return bar

# ===== FORMAT =====
def format_job_type(t):
    t=str(t).lower()
    if "follow" in t:return "FOLLOW"
    if "like" in t:return "LIKE"
    return t.upper()

# ===== STATS =====
def load_acc_stats():
    stats={}
    if os.path.exists("acc_stats.txt"):
        for line in open("acc_stats.txt"):
            try:
                aid,job,xu,ts=line.strip().split("|")
                job=int(job);xu=int(xu);ts=int(ts)
                if time.time()-ts>=86400:
                    stats[aid]={"job":0,"xu":0,"ts":int(time.time())}
                else:
                    stats[aid]={"job":job,"xu":xu,"ts":ts}
            except: pass
    return stats

def save_acc_stats(stats):
    with open("acc_stats.txt","w") as f:
        for k,v in stats.items():
            f.write(f"{k}|{v['job']}|{v['xu']}|{v['ts']}\n")

# ===== FIX TEXT =====
def fix(s,w=46):
    s=str(s)
    result=""
    for ch in s:
        if real_length(result+ch)>w-3:
            return result+"..."
        result+=ch
    return result

# ===== UI =====
def draw_box(name,job_type,link,done,maxj,total,i,delay,daily,status=""):
    width=50
    print("\033[2J\033[H",end="")

    time_str=get_vn_time()
    ping=get_ping()
    country, isp, ip = get_ip_country()
    isp = clean_isp(isp)

    sp=get_network_speed()
    col=get_speed_color(sp)
    icon=get_speed_icon(sp)

    bar=dot_bar(i,delay)

    def line(c):
        c=fix(c,width-2)
        space = width - real_length(c) - 1
        return "│ " + c + " " * space + "│"

    print(Color.CYAN+"┌"+"─"*width+"┐"+Color.RESET)
    print(line(Color.YELLOW+"⏰ "+time_str))
    print(line(Color.GREEN+f"🌍 {country} | 📡 {ping}ms"))
    print(line(Color.CYAN+f"🌐 IP: {ip}"))
    print(line(Color.PURPLE+f"📶 {isp} | "+icon+" "+col+sp+Color.RESET))
    print(line(""))
    print(line(Color.CYAN+"👤 "+name))
    print(line(Color.PURPLE+"🎯 JOB: "+job_type))
    print(line(Color.BLUE+"🔗 "+link))
    print(line(""))
    print(line(Color.YELLOW+f"⏳ {i}/{delay}s {bar}"))
    print(line(Color.GREEN+"🔄 "+status))
    print(line(""))

    left = Color.CYAN + f"📦 {done}/{maxj}"
    right = Color.YELLOW + f"💰 {total} xu" + Color.RESET
    space = width - real_length(left) - real_length(right)
    print("│ " + left + " " * space + right + "│")

    print(line(Color.YELLOW+f"💎 Tổng Xu: {daily} xu"))
    print(Color.CYAN+"└"+"─"*width+"┘"+Color.RESET)
    sys.stdout.flush()

# ===== XU =====
def xu_fly(xu):
    for i in range(5):
        print(f"\033[{10-i};10H{Color.YELLOW}💰 +{xu}{Color.RESET}")
        time.sleep(0.1)

# ===== REQUEST =====
def rq(m,u,**k):
    for _ in range(3):
        try:
            r=session.request(m,u,timeout=10,**k)
            if r.status_code==200:
                return r.json()
        except: pass
        time.sleep(2)
    return None

# ===== API =====
def get_acc(h): return rq("GET",f"{API_BASE}/tiktok-account",headers=h)
def get_job(h,id): return rq("GET",f"{API_BASE}/advertising/publishers/tiktok/jobs",headers=h,params={"account_id":id})
def complete(h,jid,id): return rq("POST",f"{API_BASE}/advertising/publishers/tiktok/complete-jobs",headers=h,json={"ads_id":jid,"account_id":id})

def skip(h,d,acc_id):
    try:
        payload={"ads_id":d.get("id"),"account_id":acc_id,"type":d.get("type")}
        if d.get("object_id"):
            payload["object_id"]=d["object_id"]
        session.post(f"{API_BASE}/advertising/publishers/tiktok/skip-jobs",
                      headers=h,json=payload,timeout=10)
    except: pass

# ===== TOKEN =====
def load():
    open("Authorization.txt","a").close()
    open("token.txt","a").close()
    a=open("Authorization.txt").read().strip()
    t=open("token.txt").read().strip()
    if a and t and input("Dùng Token Cũ? Enter=OK: ")=="":
        return a,t
    a=input("Authorization: ")
    t=input("Token: ")
    open("Authorization.txt","w").write(a)
    open("token.txt","w").write(t)
    return a,t

# ===== MAIN =====
def main():
    keep_awake()
    prevent_sleep()
    stats=load_acc_stats()

    auth,token=load()
    h={"Authorization":auth,"t":token}
    get_ip_country_once()

    while True:
        print(Color.CYAN+"\n1. Chạy Tool"+Color.RESET)
        print(Color.YELLOW+"2. Nhập link video TikTok"+Color.RESET)
        menu=input(Color.GREEN+"Chọn: "+Color.RESET)

        if menu=="2":
            save_video_link()
            continue

        accs=get_acc(h)
        if not accs or "data" not in accs:
            print(Color.RED+"Token Lỗi"+Color.RESET);return

        print(Color.CYAN+"\n=== DANH SÁCH TÀI KHOẢN ==="+Color.RESET)
        for i,a in enumerate(accs["data"],1):
            aid=str(a["id"])
            s=stats.get(aid,{"job":0,"xu":0})
            print(f"{Color.YELLOW}{i}. {a['nickname']} ({s['job']} job | {s['xu']} xu){Color.RESET}")

        try:
            idx=int(input(Color.GREEN+"Chọn Acc: "+Color.RESET))-1
            if idx<0 or idx>=len(accs["data"]): continue
            acc=accs["data"][idx]
        except: continue

        id=str(acc["id"])
        name=acc["nickname"]

        print("\n1. Follow\n2. Like\n3. Cả 2")
        choice=input("Chọn: ")
        job_filter=["follow","like"] if choice=="3" else ["follow"] if choice=="1" else ["like"]

        dmin=int(input("Delay Min: "))
        dmax=int(input("Delay Max: "))
        maxj=int(input("Số Job: "))
        retry=int(input("Retry: "))
        max_fail=int(input("Số Lỗi Liên Tiếp: "))
        rest_after=int(input("Bao nhiêu job thì nghỉ xem video: "))

        input("\n👉 Nhấn Enter Để Chạy...")

        total=done=fail=0

        while done<maxj:
            job=get_job(h,id)
            if not job or not job.get("data"):
                time.sleep(3);continue

            d=job["data"]
            if not isinstance(d,dict):
                continue

            raw=d.get("type","").lower()

            if any(x in raw for x in ["comment","share","view","join"]):
                skip(h,d,id)
                continue

            if not any(x in raw for x in job_filter):
                skip(h,d,id)
                continue

            link=d.get("link")
            if not link:
                skip(h,d,id)
                continue

            job_type=format_job_type(d["type"])

            try:
                subprocess.run(["am","start","-a","android.intent.action.VIEW","-d",link],
                               stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            except: pass

            delay=random.randint(dmin,dmax)

            for i in range(1,delay+1):
                draw_box(name,job_type,link,done,maxj,total,i,delay,
                         stats.get(id,{}).get("xu",0),"Đang Làm Job.")
                time.sleep(1)

            ok=False;xu=0

            for attempt in range(1,retry+1):
                draw_box(name,job_type,link,done,maxj,total,delay,delay,
                         stats.get(id,{}).get("xu",0),
                         f"🔄 Đang Hoàn Thành Lần {attempt}/{retry}")

                r=complete(h,d["id"],id)

                if r and r.get("status")==200:
                    xu=r.get("data",{}).get("prices",0)
                    if xu>0:
                        ok=True
                        xu_fly(xu)
                        draw_box(name,job_type,link,done,maxj,total,delay,delay,
                                 stats.get(id,{}).get("xu",0),
                                 f"🔥 Bú Job +{xu} Xu (lần {attempt})")
                        time.sleep(1.5)

                        stats.setdefault(id,{"job":0,"xu":0,"ts":int(time.time())})
                        stats[id]["job"]+=1
                        stats[id]["xu"]+=xu
                        save_acc_stats(stats)
                        break

                time.sleep(2)

            if not ok:
                fail+=1
                skip(h,d,id)
                if fail>=max_fail:
                    fail=0
                continue

            total+=xu
            done+=1
            fail=0

            if rest_after > 0 and done % rest_after == 0:
                watch_videos(name, stats, id)

        print(Color.YELLOW+"\n🔁 Hoàn Thành, Quay Lại Menu...\n"+Color.RESET)

# ===== RUN =====
if __name__=="__main__":
    while True:
        try:
            main()
        except Exception as e:
            print(Color.RED+"Lỗi, restart... "+str(e)+Color.RESET)
            time.sleep(5)