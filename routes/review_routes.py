from flask import Blueprint
from controllers.review_controller import get_reviews, create_review, delete_review
from middleware.auth_middleware import login_required

review_bp = Blueprint("reviews", __name__)
review_bp.route("/<listing_id>",   methods=["GET"])(get_reviews)
review_bp.route("/<listing_id>",   methods=["POST"])(login_required(create_review))
review_bp.route("/<review_id>",    methods=["DELETE"])(login_required(delete_review))
