from flask import Blueprint
from controllers.owner_controller import get_my_listings, get_stats, toggle_status
from middleware.auth_middleware import owner_only

owner_bp = Blueprint("owner", __name__)
owner_bp.route("/listings",              methods=["GET"])(owner_only(get_my_listings))
owner_bp.route("/stats",                 methods=["GET"])(owner_only(get_stats))
owner_bp.route("/listings/<listing_id>/toggle", methods=["PATCH"])(owner_only(toggle_status))
