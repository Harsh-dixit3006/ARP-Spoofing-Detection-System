from scapy.all import sniff, ARP, srp, Ether
import time
import threading
import random
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

ip_mac_table = {}
attack_tracker = {}
alerts_history = []

TIME_WINDOW = 10
ATTACK_THRESHOLD = 3

# Get real MAC address
def get_real_mac(ip):
    try:
        arp_request = ARP(pdst=ip)
        broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
        answered = srp(broadcast/arp_request, timeout=2, verbose=False)[0]
        if answered:
            return answered[0][1].hwsrc
    except:
        return None

# Detection plan
def detect_arp_spoof(packet):
    if packet.haslayer(ARP) and packet[ARP].op == 2:
        ip = packet[ARP].psrc
        mac = packet[ARP].hwsrc
        now = time.time()

        if ip in ip_mac_table and ip_mac_table[ip] != mac:

            real_mac = get_real_mac(ip)

            if real_mac and real_mac != mac:
                attack_tracker.setdefault(ip, []).append(now)
                attack_tracker[ip] = [t for t in attack_tracker[ip] if now - t <= TIME_WINDOW]

                severity = "LOW"
                if len(attack_tracker[ip]) >= ATTACK_THRESHOLD:
                    severity = "HIGH"
                elif len(attack_tracker[ip]) == 2:
                    severity = "MEDIUM"

                alert_obj = {
                    "id": str(int(now * 1000)) + ip,
                    "ip": ip,
                    "fake_mac": mac,
                    "original_mac": ip_mac_table[ip],
                    "real_mac": real_mac,
                    "severity": severity,
                    "time": time.ctime(now),
                    "timestamp": now
                }

                alerts_history.insert(0, alert_obj)

                # limit history
                if len(alerts_history) > 100:
                    alerts_history.pop()

                print(f"[ALERT] {alert_obj}")

        else:
            ip_mac_table[ip] = mac

# Starting sniffer thread
def start_sniffer():
    print("Advanced ARP IDS Sniffer Started...")
    sniff(store=False, prn=detect_arp_spoof)

# API: Get alerts
@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    return jsonify({
        "status": "success",
        "total_alerts": len(alerts_history),
        "alerts": alerts_history,
        "active_attackers": list(attack_tracker.keys())
    })

#  API: Generate fake attack (FOR DEMO)
@app.route('/api/test-attack', methods=['POST'])
def generate_fake_attack():
    now = time.time()
    severity = random.choice(["LOW", "MEDIUM", "HIGH"])

    alert_obj = {
        "id": str(int(now * 1000)) + "demo",
        "ip": "192.168.1.100",
        "fake_mac": "11:22:33:44:55:66",
        "original_mac": "AA:BB:CC:DD:EE:FF",
        "real_mac": "AA:BB:CC:DD:EE:FF ",
        "severity": severity,
        "time": time.ctime(now),
        "timestamp": now
    }

    alerts_history.insert(0, alert_obj)
    
    # Add dummy attacker to show UNDER ATTACK status reliably
    attack_tracker["192.168.1.100"] = [now, now, now]

    if len(alerts_history) > 100:
        alerts_history.pop()

    return jsonify({"message": "Fake attack generated", "alert": alert_obj})

# API: Clear alerts (FOR DEMO)
@app.route('/api/clear-alerts', methods=['POST'])
def clear_alerts():
    alerts_history.clear()
    attack_tracker.clear()
    return jsonify({"message": "Dashboard reset"})

#  Main
if __name__ == '__main__':
    sniffer_thread = threading.Thread(target=start_sniffer, daemon=True)
    sniffer_thread.start()
    app.run(host='0.0.0.0', port=5073, debug=False)