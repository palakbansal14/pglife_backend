from flask import request, jsonify, current_app
from flask_jwt_extended import create_access_token, get_jwt_identity
from datetime import datetime, timedelta
from bson import ObjectId
import re
import os
from twilio.rest import Client as TwilioClient

from utils.helpers import generate_otp, serialize
from middleware.auth_middleware import get_current_user


def get_db():
    return current_app.mongo.db


# ── POST /api/auth/check-user ───────────────────────────
def check_user():
    data = request.get_json()
    phone = data.get("phone", "").strip()
    if not phone or not re.match(r"^\d{10}$", phone):
        return jsonify({"success": False, "message": "Valid 10-digit phone required"}), 400
    db = get_db()
    user = db.users.find_one({"phone": phone})
    return jsonify({"success": True, "isNewUser": user is None}), 200


# ── POST /api/auth/send-otp ─────────────────────────────
def send_otp():
    data = request.get_json()
    phone = data.get("phone", "").strip()

    if not phone or not re.match(r"^\d{10}$", phone):
        return jsonify({"success": False, "message": "Valid 10-digit phone required"}), 400

    db = get_db()
    otp = generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    # Delete old OTPs for this phone
    db.otps.delete_many({"phone": phone})
    db.otps.insert_one({"phone": phone, "otp": otp, "expires_at": expires_at})

    print(f"[DEV] OTP for {phone}: {otp}")
    return jsonify({"success": True, "message": "OTP sent successfully", "otp": otp}), 200


# ── POST /api/auth/verify-otp ───────────────────────────
def verify_otp():
    data = request.get_json()
    phone = data.get("phone", "").strip()
    otp   = data.get("otp", "").strip()
    name  = data.get("name", "").strip()
    role  = data.get("role", "seeker")

    if not phone or not otp:
        return jsonify({"success": False, "message": "Phone and OTP required"}), 400

    db = get_db()

    user = db.users.find_one({"phone": phone})
    is_new_user = user is None

    # If new user and name provided — skip OTP re-verify (already verified in step 2)
    if is_new_user and name:
        pass
    else:
        # Verify OTP from MongoDB
        otp_doc = db.otps.find_one({"phone": phone, "otp": otp})
        if not otp_doc or otp_doc["expires_at"] < datetime.utcnow():
            return jsonify({"success": False, "message": "Invalid or expired OTP"}), 400
        db.otps.delete_many({"phone": phone})

    if is_new_user:
        if not name:
            return jsonify({"success": True, "isNewUser": True}), 200
        user_doc = {
            "name": name,
            "phone": phone,
            "email": "",
            "role": role if role in ["seeker", "owner"] else "seeker",
            "avatar": "",
            "wishlist": [],
            "owner_profile": {"is_verified": False},
            "created_at": datetime.utcnow(),
        }
        result = db.users.insert_one(user_doc)
        user = db.users.find_one({"_id": result.inserted_id})

    token = create_access_token(identity=str(user["_id"]))

    return jsonify({
        "success": True,
        "isNewUser": is_new_user,
        "token": token,
        "user": _format_user(user),
    }), 200


# ── GET /api/auth/me ────────────────────────────────────
def get_me():
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404

    db = get_db()
    # Populate wishlist
    wishlist_ids = [ObjectId(i) for i in user.get("wishlist", [])]
    wishlist = list(db.listings.find(
        {"_id": {"$in": wishlist_ids}},
        {"title": 1, "city": 1, "monthly_rent": 1, "images": 1}
    ))

    user_data = _format_user(user)
    user_data["wishlist"] = serialize(wishlist)
    return jsonify({"success": True, "user": user_data}), 200


# ── PUT /api/auth/profile ────────────────────────────────
def update_profile():
    db = get_db()
    user = get_current_user()
    data = request.get_json()

    db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"name": data.get("name", user["name"]), "email": data.get("email", user.get("email", ""))}}
    )
    updated = db.users.find_one({"_id": user["_id"]})
    return jsonify({"success": True, "user": _format_user(updated)}), 200


# ── Helper ───────────────────────────────────────────────
def _format_user(user):
    return {
        "_id": str(user["_id"]),
        "name": user.get("name", ""),
        "phone": user.get("phone", ""),
        "email": user.get("email", ""),
        "role": user.get("role", "seeker"),
        "avatar": user.get("avatar", ""),
        "owner_profile": user.get("owner_profile", {}),
    }
