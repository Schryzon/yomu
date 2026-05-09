# ai_service.py
# Offline local NLP integration for yōmu! using pykakasi

import pykakasi

# Global dictionary instance
kks = None

def setup_ai():
    """
    Initializes the local pykakasi dictionary in memory.
    """
    global kks
    kks = pykakasi.kakasi()

def get_real_annotation(text: str) -> str:
    """
    Uses pykakasi to locally tokenize the text and wrap Kanji in <ruby> tags.
    """
    global kks
    if kks is None:
        return text

    try:
        # Check if the text contains the batch delimiter
        delimiter = "\n|||\n"
        if delimiter in text:
            parts = text.split(delimiter)
            annotated_parts = []
            for part in parts:
                annotated_parts.append(process_single_text(part.strip()))
            return delimiter.join(annotated_parts)
        else:
            return process_single_text(text)
    except Exception as e:
        print(f"pykakasi Error: {e}")
        return text

def process_single_text(text: str) -> str:
    """
    Helper function to process a single string with pykakasi.
    """
    if not text:
        return text
        
    result = kks.convert(text)
    annotated_html = ""
    for item in result:
        orig = item['orig']
        hira = item['hira']
        
        # If the original text contains Kanji (meaning it's different from its hiragana conversion)
        # We wrap it in ruby tags. 
        if orig != hira and orig != item['kana']:
            annotated_html += f"<ruby>{orig}<rt>{hira}</rt></ruby>"
        else:
            annotated_html += orig
            
    return annotated_html

def get_mock_annotation(text: str) -> str:
    """
    Fallback mock function.
    """
    return text.replace("漢字", "<ruby>漢字<rt>かんじ</rt></ruby>")
