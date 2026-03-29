import os
import jwt
from functools import wraps
from flask import request, jsonify

# Use a strong fallback or ensure the ENV is set in production
JWT_SECRET = os.getenv("JWT_SECRET", "super_secret_jwt_key")

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Standard Bearer Token extraction
        if 'Authorization' in request.headers:
            parts = request.headers['Authorization'].split()
            if len(parts) == 2 and parts[0] == 'Bearer':
                token = parts[1]

        if not token:
            return jsonify({'message': 'Access Denied: No token provided!'}), 401
  
        try:
            # Decoding with strict algorithm check
            data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            current_user_id = data.get('id')
            
            if not current_user_id:
                return jsonify({'message': 'Invalid Token Payload!'}), 401
                
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid!'}), 401
        except Exception as e:
            return jsonify({'message': f'Authentication Error: {str(e)}'}), 401

        # Pass the ID to the route
        return f(current_user_id, *args, **kwargs)
        
    return decorated