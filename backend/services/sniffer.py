import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scapy.all import sniff, ARP, Ether, conf, sr1, srp
import time
import threading
import os
import json
import subprocess
import platform
import shutil
import smtplib
from email.message import EmailMessage
from models.alert import Alert

if platform.system() == 'Windows':
    try:
        import winsound
    except ImportError:
        winsound = None

ip_mac_table = {}
attack_tracker = {}

START_TIME = time.time()
STARTUP_GRACE_SECONDS = int(os.getenv('IDS_STARTUP_GRACE', '30'))

WHITELIST_IPS = set()
raw_whitelist = os.getenv('IDS_WHITELIST_IPS', '')
if raw_whitelist:
    WHITELIST_IPS = set([ip.strip() for ip in raw_whitelist.split(',') if ip.strip()])

TIME_WINDOW = int(os.getenv('IDS_TIME_WINDOW', '30'))
ATTACK_THRESHOLD = int(os.getenv('IDS_ATTACK_THRESHOLD', '2'))

EMAIL_RATE_LIMIT = int(os.getenv('IDS_EMAIL_RATE_LIMIT', '30'))
last_email_time = 0

_alert_counter = 0
_alert_counter_lock = threading.Lock()

socketio = None
PERSIST_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'ip_mac_table.json')

TRACKER_PRUNE_INTERVAL = 60
_last_prune_time = time.time()

# Active scanner interval in seconds
ARP_SCAN_INTERVAL = int(os.getenv('IDS_SCAN_INTERVAL', '10'))

# Your network subnet — auto detected or set via env
NETWORK_SUBNET = os.getenv('IDS_SUBNET', '192.168.31.0/24')


def ensure_persist_dir():
    persist_dir = os.path.dirname(PERSIST_PATH)
    try:
        os.makedirs(persist_dir, exist_ok=True)
    except Exception:
        pass


def load_baseline():
    global ip_mac_table
    try:
        if os.path.exists(PERSIST_PATH):
            with open(PERSIST_PATH, 'r') as f:
                ip_mac_table = json.load(f)
                print(f'[INFO] Loaded baseline with {len(ip_mac_table)} entries')
    except Exception as e:
        print(f'[WARN] Failed to load baseline: {e}')


def save_baseline():
    try:
        ensure_persist_dir()
        with open(PERSIST_PATH, 'w') as f:
            json.dump(ip_mac_table, f)
    except Exception as e:
        print(f'[WARN] Failed to persist baseline: {e}')


def play_local_siren(alert_obj, duration=5):
    def _play():
        system = platform.system()
        end = time.time() + duration
        siren_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets', 'siren.wav'))

        if system == 'Windows':
            if os.path.exists(siren_file) and winsound:
                while time.time() < end:
                    winsound.PlaySound(siren_file, winsound.SND_FILENAME)
            elif winsound:
                while time.time() < end:
                    winsound.Beep(1200, 300)
                    winsound.Beep(800, 300)

        elif system == 'Darwin':
            if os.path.exists(siren_file):
                while time.time() < end:
                    try:
                        subprocess.run(['afplay', siren_file])
                    except Exception:
                        break
            else:
                mac_sounds = [
                    '/System/Library/Sounds/Sosumi.aiff',
                    '/System/Library/Sounds/Basso.aiff',
                    '/System/Library/Sounds/Funk.aiff',
                ]
                sound = next((s for s in mac_sounds if os.path.exists(s)), None)
                if sound:
                    while time.time() < end:
                        try:
                            subprocess.run(['afplay', sound])
                        except Exception:
                            break
                else:
                    try:
                        subprocess.run(['say', 'Alert! ARP Attack Detected!'])
                    except Exception:
                        pass

        else:
            if os.path.exists(siren_file):
                cmd = None
                if shutil.which('paplay'):
                    cmd = ['paplay', siren_file]
                elif shutil.which('aplay'):
                    cmd = ['aplay', siren_file]
                while time.time() < end and cmd:
                    try:
                        subprocess.run(cmd)
                    except Exception:
                        break
            else:
                if shutil.which('beep'):
                    while time.time() < end:
                        try:
                            subprocess.run(['beep', '-f', '1200', '-l', '300',
                                            '-D', '300', '-f', '800', '-l', '300', '-D', '300'])
                        except Exception:
                            break
                elif shutil.which('spd-say'):
                    try:
                        subprocess.run(['spd-say', 'Alert! Attack Detected!'])
                    except Exception:
                        pass
                else:
                    print('[ALERT] Attack detected (no local audio player available)')

    try:
        t = threading.Thread(target=_play, daemon=True)
        t.start()
    except Exception as e:
        print(f'[ERROR] Failed to start local siren: {e}')


def verify_mac_async(ip, baseline_mac, alert_obj):
    def _probe():
        try:
            if alert_obj.get('severity') in ('HIGH', 'MEDIUM'):
                _fire_alert(alert_obj)
                return

            confirmed_baseline = 0
            for _ in range(2):
                resp = sr1(ARP(pdst=ip), timeout=1, verbose=False)
                if resp is not None and resp.haslayer(ARP):
                    if resp.hwsrc.lower() == baseline_mac.lower():
                        confirmed_baseline += 1
                    else:
                        print(f'[VERIFY] {ip} responded with SPOOFED MAC {resp.hwsrc} — firing alert')
                        _fire_alert(alert_obj)
                        return

            if confirmed_baseline == 2:
                print(f'[VERIFY] {ip} responded with baseline MAC {baseline_mac} — ignoring transient mismatch')
                attack_tracker[ip] = []
                return

        except Exception as e:
            print(f'[WARN] verify_mac_async failed: {e}')

        _fire_alert(alert_obj)

    threading.Thread(target=_probe, daemon=True).start()


def _fire_alert(alert_obj):
    Alert.log_alert(alert_obj)

    try:
        if socketio:
            socketio.emit('new_alert', alert_obj)
    except Exception as e:
        print(f'[ERROR] Socket emit failed: {e}')

    threading.Thread(target=send_alert_email, args=(alert_obj,), daemon=True).start()
    emit_siren(alert_obj)

    try:
        play_local_siren(alert_obj, duration=5)
    except Exception as e:
        print(f'[WARN] local siren failed: {e}')

    print(f">>>>>> [ALERT SCAPY -> MONGO] {alert_obj['severity']} Attack from "
          f"{alert_obj['ip']} (Fake: {alert_obj['fake_mac']}, Old: {alert_obj['original_mac']})")


def _make_alert_id(now, ip):
    global _alert_counter
    with _alert_counter_lock:
        _alert_counter += 1
        counter = _alert_counter
    return f"{int(now * 1000)}_{counter}_{ip}"


def _prune_attack_tracker(now):
    global _last_prune_time
    if now - _last_prune_time < TRACKER_PRUNE_INTERVAL:
        return
    _last_prune_time = now
    stale_ips = [ip for ip, timestamps in attack_tracker.items()
                 if not any(now - t <= TIME_WINDOW for t in timestamps)]
    for ip in stale_ips:
        del attack_tracker[ip]
    if stale_ips:
        print(f'[INFO] Pruned {len(stale_ips)} stale entries from attack_tracker')


def send_alert_email(alert_obj):
    global last_email_time
    try:
        now = time.time()
        if now - last_email_time < EMAIL_RATE_LIMIT:
            print('[INFO] Email rate limit hit, skipping email')
            return
        smtp_host = os.getenv('SMTP_HOST')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_user = os.getenv('SMTP_USER')
        smtp_pass = os.getenv('SMTP_PASS')
        to_addr = os.getenv('ALERT_EMAIL_TO')

        if not (smtp_host and smtp_user and smtp_pass and to_addr):
            return

        msg = EmailMessage()
        msg['Subject'] = f"IDS Alert: {alert_obj.get('severity')} attack from {alert_obj.get('ip')}"
        msg['From'] = smtp_user
        msg['To'] = to_addr
        body = (
            f"Time: {alert_obj.get('time')}\n"
            f"IP: {alert_obj.get('ip')}\n"
            f"Fake MAC: {alert_obj.get('fake_mac')}\n"
            f"Original MAC: {alert_obj.get('original_mac')}\n"
            f"Severity: {alert_obj.get('severity')}"
        )
        msg.set_content(body)

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as s:
            s.starttls()
            s.login(smtp_user, smtp_pass)
            s.send_message(msg)
        last_email_time = now
        print('[INFO] Alert email sent')
    except Exception as e:
        print(f'[ERROR] Failed sending alert email: {e}')


def emit_siren(alert_obj):
    try:
        if socketio:
            socketio.emit('siren', {
                'ip': alert_obj.get('ip'),
                'severity': alert_obj.get('severity')
            })
    except Exception as e:
        print(f'[ERROR] Failed to emit siren event: {e}')


def active_arp_scan():
    """Actively scan entire subnet every ARP_SCAN_INTERVAL seconds and detect MAC changes."""
    # Wait for startup grace period to finish first
    grace_remaining = STARTUP_GRACE_SECONDS - (time.time() - START_TIME)
    if grace_remaining > 0:
        time.sleep(grace_remaining)

    print(f'[INFO] Active ARP scanner started — scanning {NETWORK_SUBNET} every {ARP_SCAN_INTERVAL}s')

    while True:
        try:
            now = time.time()
            # Send ARP requests to entire subnet
            answered, _ = srp(
                Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=NETWORK_SUBNET),
                timeout=2,
                verbose=False
            )

            for sent, received in answered:
                ip = received[ARP].psrc
                mac = received[ARP].hwsrc

                if ip in ("0.0.0.0", "255.255.255.255"):
                    continue
                if ip in WHITELIST_IPS:
                    continue

                if ip not in ip_mac_table:
                    # New device discovered — add to baseline
                    ip_mac_table[ip] = mac
                    save_baseline()
                    print(f'[SCAN] New device found: {ip} -> {mac}')
                    continue

                if ip_mac_table[ip].lower() != mac.lower():
                    # MAC mismatch detected via active scan
                    attack_tracker.setdefault(ip, []).append(now)
                    attack_tracker[ip] = [t for t in attack_tracker[ip] if now - t <= TIME_WINDOW]

                    count = len(attack_tracker[ip])
                    severity = "HIGH" if count >= ATTACK_THRESHOLD else "MEDIUM" if count >= 2 else "LOW"

                    alert_obj = {
                        "alert_id": _make_alert_id(now, ip),
                        "ip": ip,
                        "fake_mac": mac,
                        "original_mac": ip_mac_table[ip],
                        "real_mac": ip_mac_table[ip],
                        "severity": severity,
                        "time": time.ctime(now),
                        "timestamp": now
                    }

                    print(f'[SCAN] MAC mismatch detected for {ip} — expected {ip_mac_table[ip]}, got {mac}')
                    _fire_alert(alert_obj)

        except Exception as e:
            print(f'[ERROR] Active ARP scan failed: {e}')

        time.sleep(ARP_SCAN_INTERVAL)


def detect_arp_spoof(packet):
    if not packet.haslayer(ARP):
        return

    ip = packet[ARP].psrc
    mac = packet[ARP].hwsrc
    now = time.time()

    if ip in ("0.0.0.0", "255.255.255.255"):
        return

    if ip in WHITELIST_IPS:
        return

    _prune_attack_tracker(now)

    if now - START_TIME <= STARTUP_GRACE_SECONDS:
        if ip not in ip_mac_table:
            ip_mac_table[ip] = mac
            save_baseline()
        return

    if ip not in ip_mac_table:
        ip_mac_table[ip] = mac
        save_baseline()
        return

    if ip_mac_table[ip].lower() != mac.lower():
        attack_tracker.setdefault(ip, []).append(now)
        attack_tracker[ip] = [t for t in attack_tracker[ip] if now - t <= TIME_WINDOW]

        count = len(attack_tracker[ip])
        severity = "HIGH" if count >= ATTACK_THRESHOLD else "MEDIUM" if count >= 2 else "LOW"

        alert_obj = {
            "alert_id": _make_alert_id(now, ip),
            "ip": ip,
            "fake_mac": mac,
            "original_mac": ip_mac_table[ip],
            "real_mac": ip_mac_table[ip],
            "severity": severity,
            "time": time.ctime(now),
            "timestamp": now
        }

        verify_mac_async(ip, ip_mac_table[ip], alert_obj)


def run_sniffer():
    print(f"Background ARP Sniffer binding to interface: {conf.iface}")
    load_baseline()
    sniff(store=False, filter="arp", prn=detect_arp_spoof)


def start_sniffer_service(injected_socketio=None):
    global socketio
    socketio = injected_socketio

    # Start passive sniffer thread
    sniffer_thread = threading.Thread(target=run_sniffer, daemon=True)
    sniffer_thread.start()

    # Start active ARP scanner thread
    scanner_thread = threading.Thread(target=active_arp_scan, daemon=True)
    scanner_thread.start()

    print('[INFO] Both passive sniffer and active ARP scanner started')