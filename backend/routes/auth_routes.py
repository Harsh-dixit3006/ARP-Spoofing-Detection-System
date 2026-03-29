import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Blueprint, request, jsonify
from controllers.auth_controller import register_user, login_user

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    # In a production IDS, you might want to restrict 
    # registration to only certain IP addresses (Admin Only)
    return register_user()

@auth_bp.route('/login', methods=['POST'])
def login():
    # Tip: This is where you'd eventually add a 
    # 'Limiter' to prevent brute force attacks
    return login_user()