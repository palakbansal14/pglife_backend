from flask import jsonify, current_app
from bson import ObjectId
from utils.helpers import serialize
from middleware.auth_middleware import get_current_user


def get_db():
    return current_app.mongo.db


def get_my_listings():
    db = get_db()
    user = get_current_user()
    listings = list(db.listings.find({"owner_id": user["_id"]}).sort("created_at", -1))
    return jsonify({"success": True, "listings": serialize(listings)}), 200


def get_stats():
    db = get_db()
    user = get_current_user()
    listings = list(db.listings.find({"owner_id": user["_id"]}))

    total = len(listings)
    active = sum(1 for l in listings if l.get("is_active"))
    total_views = sum(l.get("view_count", 0) for l in listings)
    total_saves = sum(l.get("saved_count", 0) for l in listings)
    avg_rating = (
        sum(l.get("avg_rating", 0) for l in listings) / total
        if total > 0 else 0
    )

    return jsonify({
        "success": True,
        "stats": {
            "totalListings": total,
            "activeListings": active,
            "totalViews": total_views,
            "totalSaves": total_saves,
            "avgRating": round(avg_rating, 1),
        }
    }), 200


def toggle_status(listing_id):
    db = get_db()
    user = get_current_user()
    try:
        oid = ObjectId(listing_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid ID"}), 400

    listing = db.listings.find_one({"_id": oid, "owner_id": user["_id"]})
    if not listing:
        return jsonify({"success": False, "message": "Not found or unauthorized"}), 404

    new_status = not listing.get("is_active", True)
    db.listings.update_one({"_id": oid}, {"$set": {"is_active": new_status}})
    return jsonify({"success": True, "isActive": new_status}), 200
