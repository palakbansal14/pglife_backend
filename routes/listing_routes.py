from flask import Blueprint
from controllers.listing_controller import (
    get_listings, get_map_listings, get_listing,
    create_listing, update_listing, delete_listing
)
from middleware.auth_middleware import login_required, owner_only, optional_auth

listing_bp = Blueprint("listings", __name__)

listing_bp.route("/",           methods=["GET"])(get_listings)
listing_bp.route("/map",        methods=["GET"])(get_map_listings)
listing_bp.route("/<listing_id>", methods=["GET"])(optional_auth(get_listing))
listing_bp.route("/",           methods=["POST"])(owner_only(create_listing))
listing_bp.route("/<listing_id>", methods=["PUT"])(owner_only(update_listing))
listing_bp.route("/<listing_id>", methods=["DELETE"])(owner_only(delete_listing))
