import cloudinary
import cloudinary.uploader
import os
from dotenv import load_dotenv

load_dotenv()

# ── Cloudinary config ────────────────────────────────────
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

def upload_image(file, folder="pglife/listings"):
    """Upload a single file to Cloudinary and return url + public_id."""
    result = cloudinary.uploader.upload(
        file,
        folder=folder,
        transformation=[{"width": 1200, "height": 800, "crop": "limit", "quality": "auto"}],
    )
    return {"url": result["secure_url"], "public_id": result["public_id"]}

def delete_image(public_id):
    """Delete an image from Cloudinary by public_id."""
    cloudinary.uploader.destroy(public_id)
