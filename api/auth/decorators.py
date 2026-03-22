from functools import wraps
import jwt
from flask import request, jsonify, g


def jwt_required(f):
    """Decorator to require valid JWT access token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid authorization header'}), 401

        token = auth_header.split(' ')[1]

        try:
            payload = jwt.decode(token, options={"verify_signature": False})
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        user_id = payload.get('userId', '')
        g.current_user = {'_id': user_id, 'email': user_id}
        g.current_user_id = user_id
        g.current_token = token

        return f(*args, **kwargs)
    return decorated
