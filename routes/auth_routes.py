# routes/auth_routes.py
from flask import Blueprint
from controllers.auth_controller import send_otp, verify_otp, get_me, update_profile, check_user
from middleware.auth_middleware import login_required

auth_bp = Blueprint("auth", __name__)

auth_bp.route("/check-user",  methods=["POST"])(check_user)
auth_bp.route("/send-otp",    methods=["POST"])(send_otp)
auth_bp.route("/verify-otp",  methods=["POST"])(verify_otp)
auth_bp.route("/me",          methods=["GET"])(login_required(get_me))
auth_bp.route("/profile",     methods=["PUT"])(login_required(update_profile))
