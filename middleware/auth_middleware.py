from functools import wraps
from flask import current_app, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from bson import ObjectId


def get_mongo():
    return current_app.mongo.db


def get_current_user():
    """Return current user dict from DB using JWT identity."""
    user_id = get_jwt_identity()
    db = get_mongo()
    user = db.users.find_one({"_id": ObjectId(user_id)})
    return user


def login_required(fn):
    """Decorator: requires valid JWT."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception as e:
            return jsonify({"success": False, "message": "Not authorized"}), 401
        return fn(*args, **kwargs)
    return wrapper


def owner_only(fn):
    """Decorator: requires JWT + role == 'owner'."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception:
            return jsonify({"success": False, "message": "Not authorized"}), 401
        user = get_current_user()
        if not user or user.get("role") != "owner":
            return jsonify({"success": False, "message": "Access denied: Owners only"}), 403
        return fn(*args, **kwargs)
    return wrapper


def optional_auth(fn):
    """Decorator: tries JWT but doesn't fail if absent."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request(optional=True)
        except Exception:
            pass
        return fn(*args, **kwargs)
    return wrapper
