# AI Retail Shelf Analysis Demo (Innovation Week)

A simple, visually polished Flask web app that analyzes a beer shelf image using Gemini Vision and returns:

- Detected brands
- Estimated product counts
- Estimated shelf share percentages
- AI summary and business insights

The app is intentionally beginner-friendly and easy to demo locally in under 2 minutes.

## Tech Stack

- Python Flask backend
- HTML/CSS/Bootstrap single-page frontend
- Google Gemini Vision API integration
- Chart.js for simple visual charts

## Project Structure

- app.py
- templates/index.html
- static/css/styles.css
- static/js/app.js
- services/gemini_service.py
- requirements.txt
- README.md

## 1) Setup

1. Create and activate a virtual environment:

   Windows PowerShell:

   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

2. Install dependencies:

   pip install -r requirements.txt

3. Configure environment variables:

   - Copy .env.example to .env
    - Add your Gemini key:

     GEMINI_API_KEY=your_real_key
    - Optional: if your account/project does not support the default model, set:

       GEMINI_MODEL=gemini-2.0-flash

4. Run the app:

   python app.py

5. Open browser:

   http://127.0.0.1:5000

## 2) How the Demo Works

1. Upload a beer shelf/cooler image.
2. Backend sends image to Gemini Vision with a JSON-only prompt.
3. Gemini returns brand counts, share estimates, summary, and insights.
4. Frontend renders:
   - Uploaded image
   - Brand table
   - Shelf share chart
   - Count chart
   - Summary and insights

## 3) Focus Brands

The analysis prompt prioritizes:

- Corona
- Modelo
- Pacifico
- Victoria
- Heineken
- Tecate
- Bud Light
- Coors

## 4) API Failure Fallback

If Gemini API fails or no API key is set, the backend returns realistic mock data.
This ensures your Innovation Week demo can continue without interruption.

The backend now also retries multiple model candidates automatically
(for example gemini-2.0-flash, gemini-1.5-flash-latest, gemini-1.5-flash)
before falling back to mock data.

## 5) Notes on Error Handling

The app includes basic checks for:

- Missing file
- Unsupported file type
- Empty upload
- Gemini failures
- Unexpected backend exceptions

## 6) Sample Demo Screenshots

A real screenshot is best captured after you run locally with your own test image.
Suggested captures:

- Home screen before upload
- Results screen with chart and summary

You can store them in static/screenshots/ for presentation use.
This repo also includes a lightweight placeholder visual at static/screenshots/demo-placeholder.svg.

## 7) Optional OpenAI Vision Swap

If needed, replace services/gemini_service.py logic with OpenAI Vision API calls and keep the same JSON response shape.
