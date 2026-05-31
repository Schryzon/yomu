# yōmu! Backend

This directory contains the FastAPI-powered linguistic engine that drives the yōmu! experience.

## Overview
The backend is responsible for:
- **Japanese Transliteration**: Using `pykakasi` to add Furigana to Kanji.
- **Chinese Pinyin**: Using `pypinyin` to add tonal guides to Hanzi.
- **Multi-Script Transliteration**: Handling Arabic, Cyrillic, Devanagari, and Balinese (Aksara Bali) script conversion.
- **Deep Analysis**: Integrating with **Gemini Flash-latest** to provide grammar and contextual meaning breakdowns.
- **Error Monitoring**: Integrated with Discord Webhooks for real-time developer alerts on API failures or rate limits.

## Structure
- `main.py`: The FastAPI application entry point and route handlers.
- `ai_service.py`: Core logic for linguistic processing and Gemini integration.
- `static/`: Assets and source code for the yōmu! landing page and web demo.
- `Dockerfile`: Production-ready container configuration for Google Cloud Run.

## Local Development
1. Ensure Python 3.12+ is installed.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the development server:
   ```bash
   uvicorn main:app --reload
   ```

#JuaraVibeCoding
