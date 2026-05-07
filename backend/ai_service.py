# ai_service.py
# Real Google AI Studio integration for yōmu! using the new google-genai SDK

from google import genai
import os

# Global client variable
client = None

def setup_ai():
    """
    Initializes the Google GenAI client using the GEMINI_API_KEY environment variable.
    """
    global client
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Warning: GEMINI_API_KEY not found in environment.")
        return
    client = genai.Client(api_key=api_key)

def get_real_annotation(text: str) -> str:
    """
    Actual function to call Google AI Studio (Gemini 1.5 Flash).
    Returns the text with <ruby> tags for Kanji/Hanzi.
    """
    global client
    if client is None:
        return text

    try:
        prompt = (
            "You are a linguistic engine. Transform the following text by wrapping all "
            "Japanese Kanji and Chinese Hanzi in standard HTML <ruby> tags. "
            "For Japanese, use Hiragana in the <rt> tag. For Chinese, use Pinyin. "
            "Return ONLY the transformed text. No markdown, no explanations.\n\n"
            f"Text: {text}"
        )
        
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt
        )
        
        if response and response.text:
            # Strip any accidental markdown blocks if Gemini adds them
            cleaned_text = response.text.strip().replace("```html", "").replace("```", "")
            return cleaned_text
        
        return text
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return text

def get_mock_annotation(text: str) -> str:
    """
    Fallback mock function.
    """
    return text.replace("漢字", "<ruby>漢字<rt>かんじ</rt></ruby>")
