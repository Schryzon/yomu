# ai_service.py
# Skeleton for Google AI Studio integration

# import google.generativeai as genai
# import os

def setup_ai():
    """
    Initializes the Google GenAI client.
    Call this when API keys are available.
    """
    # api_key = os.environ.get("GEMINI_API_KEY")
    # genai.configure(api_key=api_key)
    pass

def get_mock_annotation(text: str) -> str:
    """
    Mock function that fakes the AI response.
    If it sees '漢字', it wraps it.
    """
    # Just a simple mock replacement for testing the skeleton.
    return text.replace("漢字", "<ruby>漢字<rt>かんじ</rt></ruby>")

def get_real_annotation(text: str) -> str:
    """
    Actual function to call Google AI Studio (Gemini).
    Prompt structure idea:
    'You are a linguistic engine. Given the text below, return it exactly as is, 
    but wrap any Japanese Kanji in standard HTML <ruby> and <rt> tags with hiragana.
    Do the same for Chinese Hanzi (with pinyin). 
    Return ONLY the HTML string.'
    """
    # model = genai.GenerativeModel('gemini-1.5-pro-latest')
    # response = model.generate_content(...)
    # return response.text
    pass
