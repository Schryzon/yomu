from fastapi import FastAPI, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os

from pydantic import BaseModel, Field
from ai_service import get_real_annotation, setup_ai, explain_text


app = FastAPI(title="yōmu! API")

# Enable CORS for the browser extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for the hackathon, or specify chrome-extension:// IDs
    allow_credentials=False,
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
    text: str = Field(..., max_length=5000)
    target_lang: str = Field(default="auto", max_length=50)

class ExplainRequest(BaseModel):
    text: str = Field(..., max_length=500)
    context: str = Field(default="", max_length=5000)
    native_lang: str = Field(default="English", max_length=50)

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
async def annotate(request: AnnotateRequest, x_yomu_client: str = Header(None)):
    """
    Endpoint to receive raw text and return text annotated with HTML ruby tags.
    """
    if x_yomu_client != "yomu-ext-v1":
        raise HTTPException(status_code=403, detail="Unauthorized client")
        
    try:
        annotated = await get_real_annotation(request.text, target_lang=request.target_lang)
        return {"status": "success", "annotated_html": annotated}

    except Exception:
        # Detailed error is sent to Discord in ai_service.get_real_annotation
        raise HTTPException(status_code=500, detail="Internal Annotation Service Error")

@app.post("/api/explain")
async def explain(request: ExplainRequest, x_yomu_client: str = Header(None)):
    """
    Gemini-powered linguistic explanation.
    """
    if x_yomu_client != "yomu-ext-v1":
        raise HTTPException(status_code=403, detail="Unauthorized client")
        
    try:
        explanation = await explain_text(request.text, request.context, request.native_lang)

        return {"status": "success", "explanation": explanation}
    except Exception:
        # Detailed error is sent to Discord in ai_service.explain_text
        raise HTTPException(status_code=500, detail="Internal Deep Analysis Error")
