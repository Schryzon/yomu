from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from ai_service import get_mock_annotation

app = FastAPI(title="yōmu! API")

class AnnotationRequest(BaseModel):
    text: str
    target_lang: str = "auto" # Could be 'ja', 'zh', 'ar', or 'auto'

class AnnotationResponse(BaseModel):
    annotated_html: str

@app.get("/")
def health_check():
    return {"status": "ok", "message": "yōmu! backend is running."}

@app.post("/api/annotate", response_model=AnnotationResponse)
async def annotate_text(request: AnnotationRequest):
    """
    Endpoint to receive raw text and return text annotated with HTML ruby tags.
    Currently uses a mock service.
    """
    try:
        annotated = get_mock_annotation(request.text)
        return AnnotationResponse(annotated_html=annotated)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
