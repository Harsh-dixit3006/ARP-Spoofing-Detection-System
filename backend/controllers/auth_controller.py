import os, sys
# Ensure backend is resolvable as a top-level package when modules are run directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import jwt
import bcrypt
import datetime
from flask import request, jsonify
from models.user import User

JWT_SECRET = os.getenv("JWT_SECRET", "super_secret_jwt_key")

def register_user():
    data = request.json
    if not data:
        return jsonify({"message": "Request body is required"}), 400

    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not name or not email or not password:
        return jsonify({"message": "Please add all fields"}), 400

    email = email.lower().strip()  # Normalize email

    # Check if user exists
    if User.get_user_by_email(email):
        return jsonify({"message": "User already exists"}), 400

    # Hash Password
    salt = bcrypt.gensalt()
    # Decode to utf-8 to store as a string in MongoDB for better compatibility
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    user_data = {
        "name": name,
        "email": email,
        "password_hash": hashed_password,
        "role": "admin", # Defaulting to admin for an IDS tool
        "created_at": datetime.datetime.now(datetime.timezone.utc)
    }

    user_id = User.create_user(user_data)
    
    if user_id and user_id != "exists":
        # Use timezone-aware UTC
        expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
        token = jwt.encode({
            "id": str(user_id),
            "exp": expire
        }, JWT_SECRET, algorithm="HS256")
        
        return jsonify({
            "_id": str(user_id),
            "name": name,
            "email": email,
            "token": token
        }), 201

    return jsonify({"message": "Invalid user data or user already exists"}), 400

def login_user():
    data = request.json
    if not data:
        return jsonify({"message": "Request body is required"}), 400

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    email = email.lower().strip()
    user = User.get_user_by_email(email)

    # Check password (re-encode the stored hash string back to bytes for bcrypt)
    if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
        token = jwt.encode({
            "id": str(user['_id']),
            "exp": expire
        }, JWT_SECRET, algorithm="HS256")
        
        return jsonify({
            "_id": str(user['_id']),
            "name": user['name'],
            "email": user['email'],
            "token": token
        }), 200
        
    return jsonify({"message": "Invalid credentials"}), 401