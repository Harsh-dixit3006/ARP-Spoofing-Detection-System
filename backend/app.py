import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from flask import Flask, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')

def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    socketio.init_app(app)

    # Inject socketio into alert_controller AFTER init_app
    from controllers.alert_controller import set_socketio
    set_socketio(socketio)

    from routes.auth_routes import auth_bp
    from routes.alert_routes import alert_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(alert_bp, url_prefix='/api/alerts')

    @app.route('/api/health', methods=['GET'])
    def health_check():
        from models.db import get_db_status
        db_ok = get_db_status()
        return jsonify({
            "status": "ok" if db_ok else "degraded",
            "database": "connected" if db_ok else "disconnected",
            "sniffer": os.getenv('IDS_DISABLE_SNIFFER', '0') != '1'
        }), 200 if db_ok else 503

    if os.getenv('IDS_DISABLE_SNIFFER', '0') != '1':
        try:
            from services.sniffer import start_sniffer_service
            start_sniffer_service(socketio)
            print("[INFO] ARP Sniffer Service started successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to start Sniffer Service: {e}")
    else:
        print("[INFO] ARP Sniffer startup skipped (IDS_DISABLE_SNIFFER=1)")

    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv("PORT", 5001))
    print(f"[INFO] Starting ARP IDS Backend on port {port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=False, use_reloader=False)