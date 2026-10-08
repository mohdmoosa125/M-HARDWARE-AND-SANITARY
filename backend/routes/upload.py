"""Secure image upload endpoint (admin only)."""
import os
import uuid
from flask import Blueprint, request, current_app
from werkzeug.utils import secure_filename
from utils import ok, fail, admin_required

upload_bp = Blueprint("upload", __name__, url_prefix="/api/upload")

FOLDERS = {"products", "categories", "gallery", "logo"}


def _allowed(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


@upload_bp.post("/<folder>")
@admin_required
def upload_file(folder):
    if folder not in FOLDERS:
        return fail("Invalid upload folder")

    if "file" not in request.files:
        return fail("No file part in the request")

    file = request.files["file"]
    if not file or file.filename == "":
        return fail("No file selected")

    if not _allowed(file.filename):
        return fail("Only PNG, JPG, JPEG, GIF and WEBP images are allowed")

    # Give the file a unique name so uploads never overwrite each other
    safe_name = secure_filename(file.filename)
    unique = f"{uuid.uuid4().hex[:12]}_{safe_name}"

    target_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], folder)
    os.makedirs(target_dir, exist_ok=True)
    file.save(os.path.join(target_dir, unique))

    url = f"/uploads/{folder}/{unique}"
    return ok({"url": url}, message="File uploaded")