# yōmu! API v1.0.1 - Production Ready
from fastapi import FastAPI, HTTPException

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os


from pydantic import BaseModel
from ai_service import get_real_annotation, setup_ai, explain_text


app = FastAPI(title="yōmu! API")

# Enable CORS for the browser extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for the hackathon, or specify chrome-extension:// IDs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Mount static files directory
# We assume the 'static' folder is inside the 'backend' directory
static_path = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.on_event("startup")
async def startup_event():
    setup_ai()

class AnnotateRequest(BaseModel):
    text: str
    target_lang: str = "auto"

class ExplainRequest(BaseModel):
    text: str
    context: str = ""

class AnnotationResponse(BaseModel):
    annotated_html: str

@app.get("/")
def read_root():
    """
    Serves the landing page.
    """
    index_file = os.path.join(os.path.dirname(__file__), "static", "index.html")
    return FileResponse(index_file)


@app.get("/terms")
async def terms():
    terms_file = os.path.join(static_path, "terms.html")
    return FileResponse(terms_file)

@app.get("/privacy")
async def privacy():
    privacy_file = os.path.join(static_path, "privacy.html")
    return FileResponse(privacy_file)

@app.post("/api/annotate")

async def annotate(request: AnnotateRequest):
    """
    Endpoint to receive raw text and return text annotated with HTML ruby tags.
    Uses Google Gemini 2.0 Flash.

    """
    try:
        annotated = get_real_annotation(request.text, target_lang=request.target_lang)
        return {"status": "success", "annotated_html": annotated}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/explain")
async def explain(request: ExplainRequest):
    """
    Gemini-powered linguistic explanation.
    """
    try:
        explanation = await explain_text(request.text, request.context)

        return {"status": "success", "explanation": explanation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
