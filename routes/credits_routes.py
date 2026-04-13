from flask import Blueprint
from controllers.credits_controller import get_credits, unlock_listing, purchase_credits
from middleware.auth_middleware import login_required

credits_bp = Blueprint("credits", __name__)

credits_bp.route("/", methods=["GET"])(login_required(get_credits))
credits_bp.route("/purchase", methods=["POST"])(login_required(purchase_credits))
credits_bp.route("/listings/<listing_id>/unlock", methods=["POST"])(login_required(unlock_listing))
