import base64
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from services.gemini_service import analyze_beer_shelf_image, get_mock_analysis

# Load environment variables from .env if present.
load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB upload limit

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def is_allowed_filename(filename: str) -> bool:
    """Check whether the uploaded file has an allowed image extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    """Render single-page frontend."""
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    """Accept an uploaded shelf image, run AI analysis, and return JSON."""
    if "image" not in request.files:
        return jsonify({"error": "No image file provided."}), 400

    uploaded_file = request.files["image"]

    if uploaded_file.filename == "":
        return jsonify({"error": "Please select an image file."}), 400

    if not is_allowed_filename(uploaded_file.filename):
        return jsonify({"error": "Unsupported file type. Use png, jpg, jpeg, or webp."}), 400

    try:
        image_bytes = uploaded_file.read()

        if not image_bytes:
            return jsonify({"error": "Uploaded file is empty."}), 400

        analysis_result = analyze_beer_shelf_image(
            image_bytes=image_bytes,
            filename=uploaded_file.filename,
        )

        # Return a small preview string so frontend can render the uploaded image.
        analysis_result["image_preview_base64"] = base64.b64encode(image_bytes).decode("utf-8")
        analysis_result["image_mime_type"] = uploaded_file.mimetype or "image/jpeg"

        return jsonify(analysis_result)

    except Exception as exc:
        # Safety fallback to keep demo moving even if unexpected errors happen.
        fallback = get_mock_analysis()
        fallback["warning"] = f"Unexpected backend error. Showing mock analysis. Details: {str(exc)}"
        return jsonify(fallback), 200


if __name__ == "__main__":
    app.run(debug=True)
