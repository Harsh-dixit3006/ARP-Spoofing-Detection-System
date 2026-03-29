import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import jsonify, request
from models.alert import Alert
import time
import random

_socketio_instance = None

def set_socketio(sio):
    global _socketio_instance
    _socketio_instance = sio
    print("[INFO] SocketIO instance registered in alert_controller")

def _get_socketio():
    return _socketio_instance


def get_alerts():
    try:
        alerts = Alert.get_recent_alerts(limit=100)
        active_attackers = Alert.get_active_attackers()
        
        collection = Alert.get_collection()
        total_alerts = 0
        
        if collection is not None:
            try:
                total_alerts = collection.count_documents({})
            except Exception:
                total_alerts = len(alerts)
        else:
            total_alerts = len(alerts)

        return jsonify({
            "status": "success",
            "total_alerts": total_alerts,
            "alerts": alerts,
            "active_attackers": active_attackers
        }), 200
    except Exception as e:
        print(f"[ERROR] Alert Fetch Failed: {e}")
        return jsonify({
            "status": "error",
            "total_alerts": 0,
            "alerts": [],
            "active_attackers": []
        }), 200


def clear_alerts():
    Alert.clear_all()
    sio = _get_socketio()
    if sio:
        try:
            sio.emit('siren_stop', {"message": "All clear"}, namespace='/')
        except Exception as e:
            print(f"[WARNING] SocketIO emit failed: {e}")
    else:
        print("[WARNING] SocketIO not available — skipping emit")
    return jsonify({"message": "Dashboard reset"}), 200


def trigger_test_attack():
    now = time.time()
    severity = random.choice(["LOW", "MEDIUM", "HIGH"])

    alert_obj = {
        "alert_id": f"{int(now * 1000)}_demo",
        "ip": "192.168.1.100",
        "fake_mac": "11:22:33:44:55:66",
        "original_mac": "AA:BB:CC:DD:EE:FF",
        "real_mac": "AA:BB:CC:DD:EE:FF",
        "severity": severity,
        "time": time.ctime(now),
        "timestamp": now
    }
    
    Alert.log_alert(alert_obj)

    sio = _get_socketio()
    if sio:
        try:
            sio.emit('new_alert', alert_obj, namespace='/')
            sio.emit('siren', {
                'ip': alert_obj['ip'],
                'severity': alert_obj['severity']
            }, namespace='/')
        except Exception as e:
            print(f"[WARNING] SocketIO emit failed: {e}")
    else:
        print("[WARNING] SocketIO not available — skipping emit")

    return jsonify({"message": "Fake attack generated & broadcasted", "alert": alert_obj}), 201

