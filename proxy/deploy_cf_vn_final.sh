#!/bin/sh

# ================== 配置区域 ==================
TELEGRAM_TOKEN="你的BotToken"
TELEGRAM_CHAT_ID="你的ChatID"
VENV_DIR="$HOME/cf_env"
SCRIPT_PATH="$HOME/cf_scripts/cf_vietnam_ips_final.py"
STARTUP_SCRIPT="$HOME/cf_scripts/run_cf_vn_final.sh"
OUTPUT_FILE="$HOME/vietnam_cloudflare_ips_best.txt"
HISTORY_FILE="$HOME/cf_scripts/history_ips.txt"
UPDATE_TIME="02:00"
TOP_N=50
MAX_HISTORY=5000
# =============================================

echo "更新 apk 源..."
apk update

echo "安装 Python3、pip、虚拟环境、bash、curl、screen、ping 工具..."
apk add python3 py3-pip bash curl screen iputils -y
pip3 install --upgrade pip

mkdir -p "$HOME/cf_scripts"

# -------------------- 写入 Python 脚本 --------------------
cat > $SCRIPT_PATH <<'EOF'
import requests
import ipaddress
import subprocess
import platform
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import os
import random

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "vietnam_cloudflare_ips_best.txt")
HISTORY_FILE = os.getenv("HISTORY_FILE", "history_ips.txt")
THREADS = 30
TOP_N = int(os.getenv("TOP_N", 50))
MAX_HISTORY = int(os.getenv("MAX_HISTORY", 5000))

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                      data={"chat_id": TELEGRAM_CHAT_ID, "text": message})
    except Exception as e:
        print(f"[错误] Telegram 发送失败: {e}")

def fetch_cloudflare_ips():
    ipv4_list = requests.get("https://www.cloudflare.com/ips-v4").text.strip().splitlines()
    ipv6_list = requests.get("https://www.cloudflare.com/ips-v6").text.strip().splitlines()
    return ipv4_list, ipv6_list

def sample_ips(ip_list):
    result = []
    for cidr in ip_list:
        try:
            net = ipaddress.ip_network(cidr)
            hosts = list(net.hosts())
            if net.prefixlen <= 24:
                result.extend([str(ip) for ip in hosts])
            else:
                count = max(1, int(len(hosts)*0.05))
                result.extend([str(ip) for ip in random.sample(hosts,count)])
        except:
            continue
    return result

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE,"r") as f:
            return [line.strip() for line in f]
    return []

def save_history(history):
    history = history[-MAX_HISTORY:]
    with open(HISTORY_FILE,"w") as f:
        for ip in history:
            f.write(ip+"\n")

def is_vietnam(ip):
    try:
        r = requests.get(f"https://ipinfo.io/{ip}/json", timeout=3)
        return r.json().get("country")=="VN"
    except:
        return False

def ping_ip(ip):
    param = "-n" if platform.system().lower()=="windows" else "-c"
    try:
        res = subprocess.run(["ping",param,"1",ip],capture_output=True,text=True,timeout=2)
        out = res.stdout
        import re
        if platform.system().lower()=="windows":
            m = re.search(r"Average = (\d+)ms", out)
            if m: return int(m.group(1))
        else:
            m = re.search(r"time=(\d+(?:\.\d+)?) ms", out)
            if m: return float(m.group(1))
    except:
        return None
    return None

def scan_single(ip):
    if is_vietnam(ip):
        latency = ping_ip(ip)
        if latency is not None:
            print(f"[发现] {ip} 延迟 {latency}ms")
            return (ip, latency)
    return None

def scan_batch(ip_list):
    results=[]
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures={executor.submit(scan_single,ip):ip for ip in ip_list}
        for f in as_completed(futures):
            res=f.result()
            if res: results.append(res)
    return results

def main():
    print("抓取 Cloudflare IP...")
    ipv4,ipv6=fetch_cloudflare_ips()
    all_ips=sample_ips(ipv4)+sample_ips(ipv6)
    history_list=load_history()
    history_set=set(history_list)
    new_ips=[ip for ip in all_ips if ip not in history_set]
    if not new_ips:
        send_telegram_message("今天没有新增 Cloudflare IP，无需扫描。")
        return
    print(f"开始扫描 {len(new_ips)} 个新增 IP...")
    results=scan_batch(new_ips)
    history_list.extend(new_ips)
    save_history(history_list)
    existing=[]
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE,"r") as f:
            for line in f:
                ip,lat=line.strip().split()
                existing.append((ip,float(lat.replace("ms",""))))
    all_results=existing+results
    all_results=sorted(all_results,key=lambda x:x[1])[:TOP_N]
    with open(OUTPUT_FILE,"w") as f:
        for ip,lat in all_results:
            f.write(f"{ip} {lat}ms\n")
    msg=f"增量扫描完成，本次新增 {len(results)} 个越南 IP。\nTOP {TOP_N} 延迟最低 IP:\n"
    msg+="\n".join([f"{ip} {lat}ms" for ip,lat in all_results])
    send_telegram_message(msg)
    print(msg)

if __name__=="__main__":
    main()
EOF

chmod +x $SCRIPT_PATH

# -------------------- 创建虚拟环境并安装依赖 --------------------
python3 -m venv $VENV_DIR
. $VENV_DIR/bin/activate
pip install requests schedule

# -------------------- 写后台启动脚本 --------------------
cat > $STARTUP_SCRIPT <<EOL
#!/bin/sh
. $VENV_DIR/bin/activate
export TELEGRAM_TOKEN="$TELEGRAM_TOKEN"
export TELEGRAM_CHAT_ID="$TELEGRAM_CHAT_ID"
export OUTPUT_FILE="$OUTPUT_FILE"
export HISTORY_FILE="$HISTORY_FILE"
export TOP_N="$TOP_N"
export MAX_HISTORY="$MAX_HISTORY"

python3 $SCRIPT_PATH

python3 - <<PYTHON
import schedule
import time
from cf_vietnam_ips_final import main
schedule.every().day.at("$UPDATE_TIME").do(main)
while True:
    schedule.run_pending()
    time.sleep(60)
PYTHON
EOL

chmod +x $STARTUP_SCRIPT

# -------------------- 启动后台运行 --------------------
screen -dmS cf_vn_final bash -c "$STARTUP_SCRIPT"

# -------------------- 注册 OpenRC 服务 --------------------
sudo tee /etc/init.d/cf_vn_final > /dev/null <<EOF
#!/sbin/openrc-run
command="$STARTUP_SCRIPT"
command_background="yes"
name="cf_vn_final"
description="后台运行加速增量+优选越南 Cloudflare IP + 历史清理"
pidfile="/run/cf_vn_final.pid"
EOF

sudo chmod +x /etc/init.d/cf_vn_final
sudo rc-update add cf_vn_final default

echo "部署完成！"
echo "后台脚本已启动，每天 $UPDATE_TIME 自动扫描 TOP $TOP_N 越南 Cloudflare IP"
echo "OpenRC 服务已注册开机自启，历史文件自动清理保持最新 $MAX_HISTORY 条记录"
