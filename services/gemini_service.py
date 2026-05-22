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

SURVEY_TYPES = {"shelf", "display", "menu", "draft"}


SHELF_PROMPT = """
You are a retail execution expert for Constellation Brands beer products (Modelo, Corona, Pacifico, Victoria).

Analyze the uploaded beer shelf or cooler image and evaluate it against the CY26 Off-Premise Retail Execution Standards (RES).

=== STEP 1: BRAND DETECTION ===
Identify all visible beer brands. Priority Constellation brands: Corona Extra, Corona Light, Modelo Especial, Modelo Chelada, Modelo Negra, Pacifico, Victoria. Also note key competitors: Heineken, Tecate, Bud Light, Coors.
Estimate visible product count per brand and shelf share percentage.

=== STEP 2: CY26 RES COMPLIANCE EVALUATION ===
Evaluate the shelf/display against these CY26 standards:

SPACE MANAGEMENT & MERCHANDISING:
- Vertical brand blocking: each brand should occupy a vertical column (not scattered horizontally). Increases sales 20-40%.
- Pack size order: smallest packs (6pk) on top shelf, largest packs (24pk, cases) on bottom shelf/well.
- Cold box priority: Constellation share of cold box space should exceed their share of market.
- Days of supply: key SKUs (Corona Extra 12pk bottle, Corona Extra 6pk bottle, Modelo Especial 12pk can, Modelo Especial 12pk bottle, Modelo Especial 18pk can, Modelo Especial 6pk bottle) must have at least 3 days of supply — thin or empty facings are a concern.
- Single-serves: placed at eye level; highest-selling SKUs near the door handle.
- Modelo Cheladas should be shelved with traditional beer (not isolated).
- Pacifico should be placed adjacent to the craft beer section.

DISPLAYS:
- Displays must be properly merchandised, correctly priced, and show only 1 price point.
- Constellation's % share of cases on display (COD) must exceed Constellation's $ share of market.
- Corona Family and Casa Modelo (Modelo) displays must be physically separated from each other.
- If account stocks cans, cans must appear on the display.
- Displays should be built for every Constellation beer ad/feature.
- Displays should be in the most impactful, highest-traffic store location.

PRICING:
- Cans must be priced below bottles of the same brand/pack size.
- Core brands (Corona Core, Modelo Especial & Negra, Pacifico, Victoria) should be line-priced within the same pack size.
- Value curve index: 6pk ~120, 18pk ~90, 24pk ~80 relative to 12pk price per unit.
- All pricing must be visible and accurate for every package.
- Modelo Chelada & Modelo AABs priced equal to or higher than Modelo 24oz can.

DISTRIBUTION (SKU COVERAGE):
- Core Gaintain SKUs that should be present: Corona Extra 6pk bottle, Modelo Especial 6pk bottle, Modelo Especial 12pk can, Modelo Especial 12pk bottle, Modelo Especial 18pk can, Modelo Especial 24oz can.
- Note any gaps in core SKU presence.

=== STEP 3: SCORING ===
Assign an overall compliance score from 0-100 based on how well the shelf meets CY26 RES standards.

Return JSON only. No markdown, no extra text. Use this exact structure:
{
  "brands": [
    {
      "name": "Corona",
      "count": 12,
      "share_percent": 40
    }
  ],
  "summary": "One or two sentence summary of what you see on the shelf.",
  "insights": [
    "Insight about Constellation performance.",
    "Insight about competitor presence.",
    "Insight about opportunity or risk."
  ],
  "display_feedback": {
    "compliance_score": 72,
    "strengths": [
      "Vertical brand blocking is well executed for Modelo and Corona."
    ],
    "improvement_areas": [
      "Pack size order is not followed — large packs appear above smaller ones."
    ],
    "priority_actions": [
      "Move 24pk and 18pk SKUs to the bottom shelf; 6pk to the top shelf.",
      "Ensure cans are present on any active display."
    ]
  }
}

Rules:
- count must be integers.
- share_percent must be numbers 0-100.
- compliance_score must be an integer 0-100.
- Include only brands visible in the image.
- If uncertain about any standard, make a reasonable assessment based on visible evidence.
- strengths, improvement_areas, and priority_actions should each have 2-4 specific items.
- Be specific — reference what is actually visible in the image, not generic advice.
- priority_actions should be sorted most impactful first.
""".strip()

DISPLAY_PROMPT = """
You are a retail execution expert for Constellation Brands beer products.

Analyze the uploaded display image and evaluate beer display execution quality.

Return JSON only with this structure:
{
    "brands": [
        {"name": "Corona", "count": 12, "share_percent": 35}
    ],
    "summary": "One or two sentence summary.",
    "insights": ["Insight 1", "Insight 2"],
    "display_feedback": {
        "compliance_score": 70,
        "strengths": ["Strength 1", "Strength 2"],
        "improvement_areas": ["Gap 1", "Gap 2"],
        "priority_actions": ["Action 1", "Action 2"]
    },
    "survey_findings": {
        "observations": ["Observation 1", "Observation 2"],
        "opportunities": ["Opportunity 1", "Opportunity 2"],
        "evidence_checklist": ["Display location captured", "Pricing visible"]
    }
}

Rules:
- Brands: include visible beer brands and estimated case/facing counts on the display.
- compliance_score: integer 0-100.
- observations/opportunities/evidence_checklist: 2-5 concise, specific bullets each.
""".strip()

MENU_PROMPT = """
You are a retail execution analyst for on-premise menu audits.

Analyze the uploaded menu image for Constellation and competitor beer presence.

Return JSON only with this structure:
{
    "brands": [
        {"name": "Modelo", "count": 3, "share_percent": 30}
    ],
    "summary": "One or two sentence summary.",
    "insights": ["Insight 1", "Insight 2"],
    "survey_findings": {
        "observations": ["Observation 1", "Observation 2"],
        "opportunities": ["Opportunity 1", "Opportunity 2"],
        "evidence_checklist": ["Menu section captured", "Prices readable"]
    }
}

Rules:
- count should represent number of visible menu mentions/listings per brand.
- share_percent should represent estimated share of menu mentions.
- If visible, include pricing-related insights in observations.
- Keep insights specific to what is visible, not generic.
""".strip()

DRAFT_PROMPT = """
You are a retail execution analyst for draft handle audits.

Analyze the uploaded tap handle photo for brand presence and tap share.

Return JSON only with this structure:
{
    "brands": [
        {"name": "Pacifico", "count": 2, "share_percent": 20}
    ],
    "summary": "One or two sentence summary.",
    "insights": ["Insight 1", "Insight 2"],
    "survey_findings": {
        "observations": ["Observation 1", "Observation 2"],
        "opportunities": ["Opportunity 1", "Opportunity 2"],
        "evidence_checklist": ["All tap handles visible", "Brand names readable"]
    }
}

Rules:
- count should represent number of visible tap handles per brand.
- share_percent should represent estimated share of tap lineup.
- Highlight Constellation draft presence and whitespace opportunity.
- Keep outputs concise and evidence-based.
""".strip()

PROMPTS_BY_SURVEY_TYPE = {
        "shelf": SHELF_PROMPT,
        "display": DISPLAY_PROMPT,
        "menu": MENU_PROMPT,
        "draft": DRAFT_PROMPT,
}


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

    # Normalize display_feedback from CY26 RES evaluation.
    df = result.get("display_feedback", {})
    if not isinstance(df, dict):
        df = {}

    try:
        score = int(round(float(df.get("compliance_score", 0) or 0)))
    except Exception:
        score = 0

    result["display_feedback"] = {
        "compliance_score": min(100, max(0, score)),
        "strengths": [str(s) for s in (df.get("strengths") or [])[:4]],
        "improvement_areas": [str(s) for s in (df.get("improvement_areas") or [])[:4]],
        "priority_actions": [str(s) for s in (df.get("priority_actions") or [])[:4]],
    }

    findings = result.get("survey_findings", {})
    if not isinstance(findings, dict):
        findings = {}

    result["survey_findings"] = {
        "observations": [str(s) for s in (findings.get("observations") or [])[:5]],
        "opportunities": [str(s) for s in (findings.get("opportunities") or [])[:5]],
        "evidence_checklist": [str(s) for s in (findings.get("evidence_checklist") or [])[:5]],
    }

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
        "summary": "Corona leads visible shelf share, with Modelo as a strong second brand. Constellation portfolio holds dominant cold box presence.",
        "insights": [
            "Eye-level space appears weighted toward Corona and Modelo — consistent with core brand priority.",
            "Competitor presence is meaningful but fragmented across multiple brands.",
            "Opportunity: increase Pacifico and Victoria facings to strengthen portfolio depth.",
        ],
        "display_feedback": {
            "compliance_score": 65,
            "strengths": [
                "Modelo Especial and Corona Extra each hold dominant facing counts, reflecting strong core SKU support.",
                "Constellation brands collectively occupy a majority of visible cold box space.",
            ],
            "improvement_areas": [
                "Vertical brand blocking appears inconsistent — some SKUs from different brands are intermixed on the same shelf row.",
                "Pack size order may not be followed; verify smallest packs (6pk) are on the top shelf and largest packs (24pk/cases) are on the bottom.",
                "Pricing tags are not visible for all packages — all packages must show accurate, visible pricing per CY26 standards.",
            ],
            "priority_actions": [
                "Confirm price tags are visible and accurate for every SKU on shelf — this is a key CY26 compliance requirement.",
                "Reblock brands into clean vertical columns to act as navigational guideposts and improve shopability.",
                "Verify that Modelo Especial 12pk can and Corona Extra 12pk bottle each have at least 3 days of supply (thin facings risk out-of-stocks on peak weekend days).",
            ],
        },
        "used_mock_data": True,
    }
    return _normalize_and_enrich(mock)


def analyze_visit_image(
    image_bytes: bytes,
    filename: str = "upload.jpg",
    survey_type: str = "shelf",
) -> Dict[str, Any]:
    """Call Gemini Vision for a survey type and return structured analysis JSON."""
    normalized_survey_type = survey_type.strip().lower() if survey_type else "shelf"
    if normalized_survey_type not in SURVEY_TYPES:
        normalized_survey_type = "shelf"

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
                        PROMPTS_BY_SURVEY_TYPE[normalized_survey_type],
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
                normalized["survey_type"] = normalized_survey_type
                return normalized
            except Exception as model_exc:
                errors.append(f"{model_name}: {str(model_exc)}")

        fallback = get_mock_analysis()
        fallback["survey_type"] = normalized_survey_type
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
        fallback["survey_type"] = normalized_survey_type
        fallback["warning"] = f"Gemini setup failed. Showing mock analysis. Details: {str(exc)}"
        return fallback


def analyze_beer_shelf_image(image_bytes: bytes, filename: str = "upload.jpg") -> Dict[str, Any]:
    """Backward-compatible wrapper for existing shelf analyzer usage."""
    return analyze_visit_image(image_bytes=image_bytes, filename=filename, survey_type="shelf")
