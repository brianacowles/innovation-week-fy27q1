import json
import os
import random
from typing import Any, Dict, List

import google.generativeai as genai
from dotenv import load_dotenv

# Make service self-contained when called outside app.py.
load_dotenv()

# Brand focus for this specific demo.
FOCUS_BRANDS = [
    "Corona",
    "Modelo",
    "Pacifico",
    "Victoria",
    "Heineken",
    "Tecate",
    "Bud Light",
    "Coors",
]


PROMPT = """
You are a retail shelf analysis assistant.

Analyze the uploaded beer shelf or cooler image and do the following:
1) Identify visible beer brands, with priority for Corona, Modelo, Pacifico, Victoria, Heineken, Tecate, Bud Light, and Coors.
2) Estimate visible product count per detected brand.
3) Estimate shelf share percentage per brand.
4) Provide short business insights.

Return JSON only. No markdown, no extra text.
Use this exact structure:
{
  "brands": [
    {
      "name": "Corona",
      "count": 12,
      "share_percent": 40
    }
  ],
  "summary": "Short summary sentence.",
  "insights": [
    "Insight 1",
    "Insight 2"
  ]
}

Rules:
- Keep count as integers.
- Keep share_percent as numbers from 0 to 100.
- Include only brands visible in the image.
- If uncertain, make best estimate.
""".strip()


DEFAULT_MODEL_CANDIDATES = [
    # Newer models first.
    "gemini-2.0-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash",
]

SKIP_MODEL_HINTS = ["embedding", "aqa", "tts", "imagen"]


def _extract_json_text(raw_text: str) -> str:
    """Extract JSON text even if model wraps it with markdown fences."""
    text = raw_text.strip()

    if text.startswith("```"):
        lines = text.splitlines()
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model response.")

    return text[start : end + 1]


def _normalize_and_enrich(result: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize output shape and fill calculated fields for frontend use."""
    brands = result.get("brands", [])
    clean_brands: List[Dict[str, Any]] = []

    for item in brands:
        name = str(item.get("name", "")).strip()
        if not name:
            continue

        count = item.get("count", 0)
        share_percent = item.get("share_percent", 0)

        try:
            count = int(round(float(count)))
        except Exception:
            count = 0

        try:
            share_percent = round(float(share_percent), 1)
        except Exception:
            share_percent = 0.0

        clean_brands.append(
            {
                "name": name,
                "count": max(0, count),
                "share_percent": max(0.0, min(100.0, share_percent)),
            }
        )

    # If shares are missing or all zero, calculate from counts.
    total_count = sum(item["count"] for item in clean_brands)
    shares_missing = not clean_brands or all(item["share_percent"] == 0 for item in clean_brands)

    if total_count > 0 and shares_missing:
        for item in clean_brands:
            item["share_percent"] = round((item["count"] / total_count) * 100, 1)

    # Add simple classification for visuals.
    for item in clean_brands:
        item["is_focus_brand"] = item["name"] in FOCUS_BRANDS

    result["brands"] = sorted(clean_brands, key=lambda x: x["count"], reverse=True)
    result["summary"] = str(result.get("summary", "No summary provided."))

    insights = result.get("insights", [])
    if not isinstance(insights, list):
        insights = [str(insights)]
    result["insights"] = [str(i) for i in insights][:5]

    result["used_mock_data"] = bool(result.get("used_mock_data", False))
    return result


def _get_model_candidates() -> List[str]:
    """Build ordered model candidates from env, API discovery, and defaults."""
    env_model = os.getenv("GEMINI_MODEL", "").strip()
    candidates: List[str] = []

    if env_model:
        candidates.append(env_model)

    # Discover models available to the current API key/project.
    try:
        discovered: List[str] = []
        for model in genai.list_models():
            supported_methods = getattr(model, "supported_generation_methods", []) or []
            if "generateContent" not in supported_methods:
                continue

            model_name = getattr(model, "name", "")
            if not model_name:
                continue

            if model_name.startswith("models/"):
                model_name = model_name.split("/", 1)[1]

            lowered = model_name.lower()
            if "gemini" not in lowered:
                continue
            if any(hint in lowered for hint in SKIP_MODEL_HINTS):
                continue

            discovered.append(model_name)

        # Put likely vision-friendly models first when discovered.
        discovered.sort(key=lambda name: ("flash" not in name.lower(), name.lower()))

        for model_name in discovered:
            if model_name not in candidates:
                candidates.append(model_name)
    except Exception:
        # Keep app simple and resilient: if discovery fails, rely on fallback list.
        pass

    for model_name in DEFAULT_MODEL_CANDIDATES:
        if model_name not in candidates:
            candidates.append(model_name)

    return candidates


def get_mock_analysis() -> Dict[str, Any]:
    """Return deterministic-feeling mock data so demos still work without API."""
    base = [
        {"name": "Corona", "count": random.randint(10, 16)},
        {"name": "Modelo", "count": random.randint(7, 13)},
        {"name": "Pacifico", "count": random.randint(4, 9)},
        {"name": "Victoria", "count": random.randint(2, 6)},
        {"name": "Heineken", "count": random.randint(3, 8)},
        {"name": "Bud Light", "count": random.randint(2, 7)},
        {"name": "Coors", "count": random.randint(1, 5)},
    ]

    total = sum(item["count"] for item in base)
    for item in base:
        item["share_percent"] = round((item["count"] / total) * 100, 1)

    mock = {
        "brands": sorted(base, key=lambda x: x["count"], reverse=True),
        "summary": "Corona leads visible shelf share, with Modelo as a strong second brand.",
        "insights": [
            "Eye-level space appears weighted toward Corona and Modelo.",
            "Competitor presence is meaningful but fragmented across multiple brands.",
            "Opportunity: increase Pacifico and Victoria facings to improve share visibility.",
        ],
        "used_mock_data": True,
    }
    return _normalize_and_enrich(mock)


def analyze_beer_shelf_image(image_bytes: bytes, filename: str = "upload.jpg") -> Dict[str, Any]:
    """Call Gemini Vision with the shelf image and return structured analysis JSON."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key:
        fallback = get_mock_analysis()
        fallback["warning"] = "GEMINI_API_KEY is not set. Showing mock analysis data."
        return fallback

    try:
        genai.configure(api_key=api_key)

        mime_type = "image/jpeg"
        lower_name = filename.lower()
        if lower_name.endswith(".png"):
            mime_type = "image/png"
        elif lower_name.endswith(".webp"):
            mime_type = "image/webp"

        model_candidates = _get_model_candidates()
        errors: List[str] = []

        for model_name in model_candidates:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(
                    [
                        PROMPT,
                        {
                            "mime_type": mime_type,
                            "data": image_bytes,
                        },
                    ],
                    generation_config={"temperature": 0.2},
                )

                raw_text = getattr(response, "text", "") or ""
                json_text = _extract_json_text(raw_text)
                parsed = json.loads(json_text)
                normalized = _normalize_and_enrich(parsed)
                normalized["used_mock_data"] = False
                normalized["model_used"] = model_name
                return normalized
            except Exception as model_exc:
                errors.append(f"{model_name}: {str(model_exc)}")

        fallback = get_mock_analysis()
        attempted = ", ".join(model_candidates[:6])
        error_preview = " | ".join(errors[:2]) if errors else "No model error details available."
        fallback["warning"] = (
            "Gemini analysis failed for all configured models. "
            f"Attempted: {attempted}. "
            f"Showing mock analysis. Errors: {error_preview}"
        )
        fallback["model_attempts"] = model_candidates[:10]
        return fallback

    except Exception as exc:
        fallback = get_mock_analysis()
        fallback["warning"] = f"Gemini setup failed. Showing mock analysis. Details: {str(exc)}"
        return fallback
