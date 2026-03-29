from flask import request, jsonify, current_app
from bson import ObjectId
from datetime import datetime
from utils.helpers import serialize
from middleware.auth_middleware import get_current_user


def get_db():
    return current_app.mongo.db


def get_reviews(listing_id):
    db = get_db()
    try:
        oid = ObjectId(listing_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid ID"}), 400

    reviews = list(db.reviews.find({"listing_id": listing_id}).sort("created_at", -1))
    for r in reviews:
        user = db.users.find_one({"_id": ObjectId(r["user_id"])}, {"name": 1, "avatar": 1})
        r["user"] = user
    return jsonify({"success": True, "reviews": serialize(reviews)}), 200


def create_review(listing_id):
    db = get_db()
    user = get_current_user()
    data = request.get_json()

    # Check duplicate
    existing = db.reviews.find_one({"listing_id": listing_id, "user_id": str(user["_id"])})
    if existing:
        return jsonify({"success": False, "message": "You already reviewed this listing"}), 400

    rating = data.get("rating")
    comment = data.get("comment", "").strip()

    if not rating or not (1 <= int(rating) <= 5):
        return jsonify({"success": False, "message": "Rating must be 1–5"}), 400
    if not comment:
        return jsonify({"success": False, "message": "Comment is required"}), 400

    review = {
        "listing_id": listing_id,
        "user_id": str(user["_id"]),
        "rating": int(rating),
        "comment": comment,
        "categories": data.get("categories", {}),
        "created_at": datetime.utcnow(),
    }
    result = db.reviews.insert_one(review)

    # Recalculate avg rating for listing
    all_reviews = list(db.reviews.find({"listing_id": listing_id}))
    avg = sum(r["rating"] for r in all_reviews) / len(all_reviews)
    db.listings.update_one(
        {"_id": ObjectId(listing_id)},
        {"$set": {"avg_rating": round(avg, 1), "review_count": len(all_reviews)}}
    )

    new_review = db.reviews.find_one({"_id": result.inserted_id})
    new_review["user"] = db.users.find_one({"_id": user["_id"]}, {"name": 1, "avatar": 1})
    return jsonify({"success": True, "review": serialize(new_review)}), 201


def delete_review(review_id):
    db = get_db()
    user = get_current_user()
    try:
        oid = ObjectId(review_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid ID"}), 400

    db.reviews.delete_one({"_id": oid, "user_id": str(user["_id"])})
    return jsonify({"success": True, "message": "Review deleted"}), 200
