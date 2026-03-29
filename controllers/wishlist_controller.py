from flask import jsonify, current_app
from bson import ObjectId
from utils.helpers import serialize
from middleware.auth_middleware import get_current_user


def get_db():
    return current_app.mongo.db


def get_wishlist():
    db = get_db()
    user = get_current_user()
    wishlist_ids = [ObjectId(i) for i in user.get("wishlist", []) if ObjectId.is_valid(i)]
    listings = list(db.listings.find({"_id": {"$in": wishlist_ids}}))

    # Populate owner info
    for l in listings:
        owner = db.users.find_one({"_id": l.get("owner_id")}, {"name": 1, "owner_profile": 1})
        l["owner"] = owner

    return jsonify({"success": True, "wishlist": serialize(listings)}), 200


def toggle_wishlist(listing_id):
    db = get_db()
    user = get_current_user()

    try:
        oid = ObjectId(listing_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid ID"}), 400

    wishlist = [str(i) for i in user.get("wishlist", [])]
    in_wishlist = listing_id in wishlist

    if in_wishlist:
        db.users.update_one({"_id": user["_id"]}, {"$pull": {"wishlist": listing_id}})
        db.listings.update_one({"_id": oid}, {"$inc": {"saved_count": -1}})
        saved = False
    else:
        db.users.update_one({"_id": user["_id"]}, {"$addToSet": {"wishlist": listing_id}})
        db.listings.update_one({"_id": oid}, {"$inc": {"saved_count": 1}})
        saved = True

    updated_user = db.users.find_one({"_id": user["_id"]})
    return jsonify({"success": True, "saved": saved, "wishlist": updated_user.get("wishlist", [])}), 200
