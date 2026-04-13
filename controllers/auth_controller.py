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
    country_code = data.get("countryCode", "+91").strip()

    if not phone or not re.match(r"^\d{10}$", phone):
        return jsonify({"success": False, "message": "Valid 10-digit phone required"}), 400

    full_phone = f"{country_code}{phone}"

    twilio_sid   = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
    verify_sid   = os.getenv("TWILIO_VERIFY_SERVICE_SID")

    try:
        twilio_client = TwilioClient(twilio_sid, twilio_token)
        twilio_client.verify.v2.services(verify_sid).verifications.create(
            to=full_phone, channel="sms"
        )
    except Exception as e:
        print(f"[Twilio Error] {e}")
        return jsonify({"success": False, "message": "Failed to send OTP. Try again."}), 500

    return jsonify({"success": True, "message": "OTP sent successfully"}), 200


# ── POST /api/auth/verify-otp ───────────────────────────
def verify_otp():
    data = request.get_json()
    phone        = data.get("phone", "").strip()
    otp          = data.get("otp", "").strip()
    name         = data.get("name", "").strip()
    role         = data.get("role", "seeker")
    country_code = data.get("countryCode", "+91").strip()

    if not phone or not otp:
        return jsonify({"success": False, "message": "Phone and OTP required"}), 400

    full_phone = f"{country_code}{phone}"
    db = get_db()

    user = db.users.find_one({"phone": phone})
    is_new_user = user is None

    # Verify OTP via Twilio Verify
    try:
        twilio_client = TwilioClient(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
        check = twilio_client.verify.v2.services(os.getenv("TWILIO_VERIFY_SERVICE_SID")) \
                    .verification_checks.create(to=full_phone, code=otp)
        if check.status != "approved":
            return jsonify({"success": False, "message": "Invalid or expired OTP"}), 400
    except Exception as e:
        print(f"[Twilio Verify Error] {e}")
        return jsonify({"success": False, "message": "OTP verification failed"}), 400

    if is_new_user:
        if not name:
            return jsonify({"success": True, "isNewUser": True}), 200
        clean_role = role if role in ["seeker", "owner"] else "seeker"
        # Owners get 15 free credits (enough for 1 free listing to try the platform).
        # Seekers get 5 free credits (enough to unlock a couple of contacts).
        signup_credits = 15 if clean_role == "owner" else 5
        user_doc = {
            "name": name,
            "phone": phone,
            "email": "",
            "role": clean_role,
            "avatar": "",
            "credits": signup_credits,
            "wishlist": [],
            "owner_profile": {"is_verified": False},
            "created_at": datetime.utcnow(),
        }
        result = db.users.insert_one(user_doc)
        user = db.users.find_one({"_id": result.inserted_id})

    # Existing user: if they logged in via "List Your PG" (role=owner), upgrade their role
    if not is_new_user and role == "owner" and user.get("role") != "owner":
        extra_credits = 10  # top-up so they can post (owners need 15, seekers got 5)
        db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"role": "owner"}, "$inc": {"credits": extra_credits}}
        )
        user = db.users.find_one({"_id": user["_id"]})

    # Ensure existing users (created before credits system) have a credits field
    if user.get("credits") is None:
        db.users.update_one({"_id": user["_id"]}, {"$set": {"credits": 5}})
        user["credits"] = 5

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
        "credits": user.get("credits", 0),
        "owner_profile": user.get("owner_profile", {}),
    }
