from flask import Blueprint
from controllers.chat_controller import chat_message

chat_bp = Blueprint("chat", __name__)
chat_bp.route("/message", methods=["POST"])(chat_message)
