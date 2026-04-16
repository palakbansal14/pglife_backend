from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from pymongo import MongoClient
from dotenv import load_dotenv
import certifi
import os

load_dotenv()


app = Flask(__name__)
app.url_map.strict_slashes = False

# ── Config ──────────────────────────────────────────────
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "change-this-secret")
from datetime import timedelta
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=7)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB upload limit

# ── MongoDB ──────────────────────────────────────────────
_mongo_client = MongoClient(
    os.getenv("MONGO_URI"),
    tls=True,
    tlsCAFile=certifi.where(),
)

class _MongoWrapper:
    @property
    def db(self):
        return _mongo_client.get_default_database()

mongo = _MongoWrapper()

# ── Extensions ──────────────────────────────────────────
jwt = JWTManager(app)
CORS(app, origins="*")

# ── Make mongo accessible everywhere ────────────────────
app.mongo = mongo

# ── Register Blueprints ─────────────────────────────────
from routes.auth_routes import auth_bp
from routes.listing_routes import listing_bp
from routes.wishlist_routes import wishlist_bp
from routes.review_routes import review_bp
from routes.owner_routes import owner_bp
from routes.chat_routes import chat_bp
from routes.credits_routes import credits_bp

app.register_blueprint(auth_bp,     url_prefix="/api/auth")
app.register_blueprint(listing_bp,  url_prefix="/api/listings")
app.register_blueprint(wishlist_bp, url_prefix="/api/wishlist")
app.register_blueprint(review_bp,   url_prefix="/api/reviews")
app.register_blueprint(owner_bp,    url_prefix="/api/owner")
app.register_blueprint(chat_bp,     url_prefix="/api/chat")
app.register_blueprint(credits_bp,  url_prefix="/api/credits")

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
    is_dev = os.getenv("FLASK_ENV", "development") == "development"
    app.run(debug=is_dev, port=port, host="0.0.0.0")
