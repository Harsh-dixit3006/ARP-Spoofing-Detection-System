import os, sys
# Make sure backend/ is on the import path so `controllers` and `models` imports resolve
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Blueprint, jsonify
from controllers.alert_controller import get_alerts, trigger_test_attack, clear_alerts
from routes.middleware import token_required

alert_bp = Blueprint('alerts', __name__)

@alert_bp.route('', methods=['GET'])
@token_required
def get_alerts_route(current_user_id):
    return get_alerts()

@alert_bp.route('/test-attack', methods=['POST'])
@token_required
def generate_fake_attack_route(current_user_id):
    return trigger_test_attack()

@alert_bp.route('/clear-alerts', methods=['DELETE'])
@token_required
def clear_alerts_route(current_user_id):
    return clear_alerts()