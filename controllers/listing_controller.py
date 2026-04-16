from flask import request, jsonify, current_app
from flask_jwt_extended import get_jwt_identity
from bson import ObjectId
from datetime import datetime
import re

from utils.helpers import serialize, paginate
from config.db import upload_image, delete_image
from middleware.auth_middleware import get_current_user

# Credits required to post a new listing (must match credits_controller.py)
LISTING_COST = 15


def get_db():
    return current_app.mongo.db


# ── GET /api/listings ────────────────────────────────────
def get_listings():
    db = get_db()
    args = request.args

    query = {"is_active": True}

    # Filters
    if args.get("city"):
        query["city"] = args["city"]
    if args.get("gender") and args["gender"] != "Any":
        query["gender_preference"] = {"$in": [args["gender"], "Any"]}
    if args.get("locality"):
        query["locality"] = {"$regex": args["locality"], "$options": "i"}

    min_b = args.get("minBudget")
    max_b = args.get("maxBudget")
    if min_b or max_b:
        query["monthly_rent"] = {}
        if min_b: query["monthly_rent"]["$gte"] = int(min_b)
        if max_b: query["monthly_rent"]["$lte"] = int(max_b)

    if args.get("amenities"):
        for a in args["amenities"].split(","):
            query[f"amenities.{a.strip()}"] = True

    # Sort
    sort_map = {
        "newest":     [("created_at", -1)],
        "oldest":     [("created_at", 1)],
        "price-low":  [("monthly_rent", 1)],
        "price-high": [("monthly_rent", -1)],
        "rating":     [("avg_rating", -1)],
    }
    sort = sort_map.get(args.get("sort", "newest"), [("created_at", -1)])

    page  = int(args.get("page", 1))
    limit = int(args.get("limit", 12))
    total = db.listings.count_documents(query)

    cursor = db.listings.find(query).sort(sort).skip((page - 1) * limit).limit(limit)
    listings = []
    for l in cursor:
        # Listing cards: show owner name only — phone/address/title/locality are gated behind unlock
        owner = db.users.find_one({"_id": l.get("owner_id")}, {"name": 1, "owner_profile": 1})
        l["owner"] = owner
        l.pop("address", None)    # never expose full address in listing cards
        l.pop("title", None)      # title revealed only on unlocked detail page
        l.pop("locality", None)   # exact area revealed only on unlocked detail page
        listings.append(serialize(l))

    return jsonify({
        "success": True,
        "total": total,
        "pages": max(1, -(-total // limit)),  # ceil division
        "currentPage": page,
        "listings": listings,
    }), 200


# ── GET /api/listings/map ────────────────────────────────
def get_map_listings():
    db = get_db()
    args = request.args
    query = {"is_active": True, "coordinates": {"$exists": True}}

    if args.get("city"):   query["city"] = args["city"]
    if args.get("gender") and args["gender"] != "Any":
        query["gender_preference"] = {"$in": [args["gender"], "Any"]}
    min_b = args.get("minBudget")
    max_b = args.get("maxBudget")
    if min_b or max_b:
        query["monthly_rent"] = {}
        if min_b: query["monthly_rent"]["$gte"] = int(min_b)
        if max_b: query["monthly_rent"]["$lte"] = int(max_b)

    fields = {"title": 1, "city": 1, "locality": 1, "monthly_rent": 1,
              "gender_preference": 1, "coordinates": 1, "images": 1, "avg_rating": 1}
    listings = list(db.listings.find(query, fields).limit(200))
    return jsonify({"success": True, "listings": serialize(listings)}), 200


# ── GET /api/listings/<id> ───────────────────────────────
def get_listing(listing_id):
    from controllers.credits_controller import UNLOCK_COST
    db = get_db()
    try:
        oid = ObjectId(listing_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid ID"}), 400

    listing = db.listings.find_one_and_update(
        {"_id": oid},
        {"$inc": {"view_count": 1}},
        return_document=True
    )
    if not listing:
        return jsonify({"success": False, "message": "Listing not found"}), 404

    owner = db.users.find_one(
        {"_id": listing.get("owner_id")},
        {"name": 1, "phone": 1, "avatar": 1, "owner_profile": 1}
    )
    listing["owner"] = owner

    listing_data = serialize(listing)

    # ── Access control: hide address & phone unless unlocked ──
    user_id = get_jwt_identity()  # None if request has no JWT (optional_auth)
    is_unlocked = False

    if user_id:
        # Owner always sees their own listing in full
        if str(listing.get("owner_id")) == user_id:
            is_unlocked = True
        else:
            unlock = db.unlocks.find_one({
                "user_id": ObjectId(user_id),
                "listing_id": oid,
            })
            is_unlocked = unlock is not None

    if not is_unlocked:
        listing_data.pop("address", None)
        if listing_data.get("owner"):
            listing_data["owner"].pop("phone", None)
        listing_data["isLocked"] = True
        listing_data["unlockCost"] = UNLOCK_COST
    else:
        listing_data["isLocked"] = False

    return jsonify({"success": True, "listing": listing_data}), 200


# ── POST /api/listings ───────────────────────────────────
def create_listing():
    db = get_db()
    user = get_current_user()

    # Check owner has enough credits to post a listing
    current_credits = user.get("credits", 0)
    if current_credits < LISTING_COST:
        return jsonify({
            "success": False,
            "message": f"Insufficient credits. Posting a listing costs {LISTING_COST} credits. "
                       f"You have {current_credits} credits.",
            "required": LISTING_COST,
            "available": current_credits,
        }), 402

    data = request.form.to_dict()
    files = request.files.getlist("images")

    # Upload images to Cloudinary
    images = []
    for f in files[:10]:
        try:
            result = upload_image(f)
            images.append(result)
        except Exception as e:
            print(f"Image upload error: {e}")

    # Parse amenities (sent as JSON string or individual fields)
    import json
    amenities = {}
    raw_amenities = data.get("amenities", "{}")
    try:
        amenities = json.loads(raw_amenities)
    except Exception:
        pass

    house_rules = []
    raw_rules = data.get("houseRules", "[]")
    try:
        house_rules = json.loads(raw_rules)
    except Exception:
        pass

    sharing_type = []
    raw_sharing = data.get("sharingType", "[]")
    try:
        sharing_type = json.loads(raw_sharing)
    except Exception:
        pass

    doc = {
        "owner_id": user["_id"],
        "title": data.get("title", ""),
        "description": data.get("description", ""),
        "city": data.get("city", ""),
        "locality": data.get("locality", ""),
        "address": data.get("address", ""),
        "monthly_rent": int(data.get("monthlyRent") or 0),
        "security_deposit": int(data.get("securityDeposit") or 0),
        "pg_type": data.get("pgType", "PG"),
        "gender_preference": data.get("genderPreference", "Any"),
        "sharing_type": sharing_type,
        "available_rooms": int(data.get("availableRooms") or 0),
        "amenities": amenities,
        "house_rules": house_rules,
        "images": images,
        "is_active": True,
        "is_verified": False,
        "avg_rating": 0,
        "review_count": 0,
        "view_count": 0,
        "saved_count": 0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    result = db.listings.insert_one(doc)

    # Deduct credits from the owner after successful listing creation
    db.users.update_one({"_id": user["_id"]}, {"$inc": {"credits": -LISTING_COST}})

    new_listing = db.listings.find_one({"_id": result.inserted_id})
    return jsonify({
        "success": True,
        "listing": serialize(new_listing),
        "credits_remaining": current_credits - LISTING_COST,
    }), 201


# ── PUT /api/listings/<id> ───────────────────────────────
def update_listing(listing_id):
    db = get_db()
    user = get_current_user()

    try:
        oid = ObjectId(listing_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid ID"}), 400

    listing = db.listings.find_one({"_id": oid, "owner_id": user["_id"]})
    if not listing:
        return jsonify({"success": False, "message": "Not found or unauthorized"}), 404

    import json
    data = request.get_json() or {}

    update = {"updated_at": datetime.utcnow()}
    for field in ["title", "description", "monthly_rent", "security_deposit",
                  "available_rooms", "gender_preference", "house_rules", "amenities"]:
        snake = _to_snake(field)
        if field in data:
            update[snake] = data[field]

    db.listings.update_one({"_id": oid}, {"$set": update})
    updated = db.listings.find_one({"_id": oid})
    return jsonify({"success": True, "listing": serialize(updated)}), 200


# ── DELETE /api/listings/<id> ────────────────────────────
def delete_listing(listing_id):
    db = get_db()
    user = get_current_user()

    try:
        oid = ObjectId(listing_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid ID"}), 400

    listing = db.listings.find_one({"_id": oid, "owner_id": user["_id"]})
    if not listing:
        return jsonify({"success": False, "message": "Not found or unauthorized"}), 404

    # Delete images from Cloudinary
    for img in listing.get("images", []):
        if img.get("public_id"):
            try: delete_image(img["public_id"])
            except Exception: pass

    db.listings.delete_one({"_id": oid})
    return jsonify({"success": True, "message": "Listing deleted"}), 200


def _to_snake(name):
    """Convert camelCase to snake_case."""
    s = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s).lower()
