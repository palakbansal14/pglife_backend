# routes/wishlist_routes.py
from flask import Blueprint
from controllers.wishlist_controller import get_wishlist, toggle_wishlist
from middleware.auth_middleware import login_required

wishlist_bp = Blueprint("wishlist", __name__)
wishlist_bp.route("/",              methods=["GET"])(login_required(get_wishlist))
wishlist_bp.route("/<listing_id>/toggle", methods=["POST"])(login_required(toggle_wishlist))
