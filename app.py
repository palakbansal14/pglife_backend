from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_pymongo import PyMongo
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

# ── Config ──────────────────────────────────────────────
app.config["MONGO_URI"] = os.getenv("MONGO_URI")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "change-this-secret")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False  # No expiry (or set timedelta)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB upload limit

# ── Extensions ──────────────────────────────────────────
mongo = PyMongo(app)
jwt = JWTManager(app)
CORS(app, origins=[os.getenv("FRONTEND_URL", "http://localhost:5173")], supports_credentials=True)

# ── Make mongo accessible everywhere ────────────────────
app.mongo = mongo

# ── Register Blueprints ─────────────────────────────────
from routes.auth_routes import auth_bp
from routes.listing_routes import listing_bp
from routes.wishlist_routes import wishlist_bp
from routes.review_routes import review_bp
from routes.owner_routes import owner_bp
from routes.chat_routes import chat_bp

app.register_blueprint(auth_bp,     url_prefix="/api/auth")
app.register_blueprint(listing_bp,  url_prefix="/api/listings")
app.register_blueprint(wishlist_bp, url_prefix="/api/wishlist")
app.register_blueprint(review_bp,   url_prefix="/api/reviews")
app.register_blueprint(owner_bp,    url_prefix="/api/owner")
app.register_blueprint(chat_bp,     url_prefix="/api/chat")

# ── Health check ─────────────────────────────────────────
@app.route("/")
def index():
    return {"message": "PG Life Flask API is running 🚀", "version": "1.0.0"}

# ── Error handlers ───────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return {"success": False, "message": "Route not found"}, 404

@app.errorhandler(500)
def server_error(e):
    return {"success": False, "message": "Internal server error"}, 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(debug=True, port=port)
