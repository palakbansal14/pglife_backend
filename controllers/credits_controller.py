from flask import jsonify, current_app, request
from bson import ObjectId
from datetime import datetime

from middleware.auth_middleware import get_current_user

# ── Credit packages ──────────────────────────────────────
PACKAGES = {
    "starter": {"credits": 20,  "price": 99},
    "popular": {"credits": 50,  "price": 199},
    "pro":     {"credits": 120, "price": 399},
}

# ── Constants (must match listing_controller.py) ─────────
UNLOCK_COST = 2    # credits to unlock a listing's contact details
LISTING_COST = 15  # credits required to post a new listing


def get_db():
    return current_app.mongo.db


# ── GET /api/credits ─────────────────────────────────────
def get_credits():
    """Return the logged-in user's current credit balance."""
    user = get_current_user()
    db = get_db()
    fresh = db.users.find_one({"_id": user["_id"]}, {"credits": 1})
    return jsonify({
        "success": True,
        "credits": fresh.get("credits", 0),
        "unlock_cost": UNLOCK_COST,
        "listing_cost": LISTING_COST,
    }), 200


# ── POST /api/listings/<id>/unlock ───────────────────────
def unlock_listing(listing_id):
    """
    Spend UNLOCK_COST credits to reveal the full address and owner
    phone number for a listing.  Idempotent – calling it again when
    already unlocked just returns success.
    """
    user = get_current_user()
    db = get_db()

    try:
        oid = ObjectId(listing_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid listing ID"}), 400

    # Verify listing exists
    listing = db.listings.find_one({"_id": oid, "is_active": True}, {"_id": 1, "owner_id": 1})
    if not listing:
        return jsonify({"success": False, "message": "Listing not found"}), 404

    # Owner can always see their own listing — no credit charge
    if listing.get("owner_id") == user["_id"]:
        return jsonify({"success": True, "message": "You own this listing", "already_unlocked": True}), 200

    # Already unlocked?
    existing = db.unlocks.find_one({"user_id": user["_id"], "listing_id": oid})
    if existing:
        return jsonify({"success": True, "message": "Already unlocked", "already_unlocked": True}), 200

    # Check credit balance
    fresh_user = db.users.find_one({"_id": user["_id"]}, {"credits": 1})
    credits = fresh_user.get("credits", 0)
    if credits < UNLOCK_COST:
        return jsonify({
            "success": False,
            "message": f"Insufficient credits. You need {UNLOCK_COST} credits to unlock contact details.",
            "required": UNLOCK_COST,
            "available": credits,
        }), 402  # 402 Payment Required

    # Deduct credits atomically and record the unlock
    db.users.update_one({"_id": user["_id"]}, {"$inc": {"credits": -UNLOCK_COST}})
    db.unlocks.insert_one({
        "user_id": user["_id"],
        "listing_id": oid,
        "unlocked_at": datetime.utcnow(),
        "credits_spent": UNLOCK_COST,
    })

    return jsonify({
        "success": True,
        "message": "Listing unlocked! You can now see the full address and owner contact.",
        "credits_remaining": credits - UNLOCK_COST,
    }), 200


# ── POST /api/credits/purchase ───────────────────────────
def purchase_credits():
    """
    Mock purchase endpoint — adds credits directly.
    In production, replace with a real payment gateway (Razorpay etc.)
    before adding credits.
    """
    user = get_current_user()
    db = get_db()

    data = request.get_json() or {}
    pkg_key = data.get("package", "").lower()

    if pkg_key not in PACKAGES:
        return jsonify({"success": False, "message": "Invalid package selected"}), 400

    pkg = PACKAGES[pkg_key]
    credits_to_add = pkg["credits"]

    db.users.update_one({"_id": user["_id"]}, {"$inc": {"credits": credits_to_add}})

    # Log the purchase
    db.credit_purchases.insert_one({
        "user_id": user["_id"],
        "package": pkg_key,
        "credits_added": credits_to_add,
        "amount_paid": pkg["price"],
        "purchased_at": datetime.utcnow(),
    })

    fresh = db.users.find_one({"_id": user["_id"]}, {"credits": 1})
    return jsonify({
        "success": True,
        "message": f"{credits_to_add} credits added to your account!",
        "credits_added": credits_to_add,
        "new_balance": fresh.get("credits", 0),
    }), 200
