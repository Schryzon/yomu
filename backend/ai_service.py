# ai_service.py
# Offline local NLP integration for yōmu! using pykakasi
import os
import pykakasi
from pypinyin import pinyin, Style
from langdetect import detect_langs
from google import genai
from dotenv import load_dotenv
import re

load_dotenv()

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None



# Global dictionary instance
kks = None

def setup_ai():
    """
    Initializes the local pykakasi dictionary in memory.
    """
    global kks
    kks = pykakasi.kakasi()

# Arabic Transliteration Mapping (Buckwalter-ish but readable)
AR_MAP = {
    'ا': 'a', 'ب': 'b', 'ت': 't', 'ث': 'th', 'ج': 'j', 'ح': 'h', 'خ': 'kh',
    'د': 'd', 'ذ': 'dh', 'ر': 'r', 'ز': 'z', 'س': 's', 'ش': 'sh', 'ص': 's',
    'ض': 'd', 'ط': 't', 'ظ': 'z', 'ع': 'a', 'غ': 'gh', 'ف': 'f', 'ق': 'q',
    'ك': 'k', 'ل': 'l', 'م': 'm', 'ن': 'n', 'ه': 'h', 'و': 'w', 'ي': 'y',
    'ة': 'h', 'ء': '\'', 'أ': 'a', 'إ': 'i', 'ؤ': 'u', 'ئ': 'i', 'ى': 'a',
    'آ': 'aa', 'لا': 'la'
}


def get_real_annotation(text: str, target_lang: str = "auto") -> str:
    """
    Analyzes the text and wraps it in ruby tags based on the target language.
    """
    global kks
    if not text:
        return text

    # Handle batch processing if delimiter is present
    delimiter = "\n|||\n"
    if delimiter in text:
        parts = text.split(delimiter)
        annotated_parts = []
        for part in parts:
            annotated_parts.append(get_real_annotation(part.strip(), target_lang))
        return delimiter.join(annotated_parts)

    # Language detection logic
    if target_lang == "auto":
        try:
            # We only detect if there's enough text
            if len(text.strip()) > 0:
                langs = detect_langs(text)
                top_lang = langs[0].lang
                if top_lang == 'zh-cn' or top_lang == 'zh-tw' or top_lang == 'zh':
                    target_lang = "zh"
                elif top_lang == 'ja':
                    target_lang = "ja"
                elif top_lang == 'ar':
                    target_lang = "ar"
                elif top_lang == 'ru':
                    target_lang = "ru"
                elif top_lang == 'hi':
                    target_lang = "hi"
                else:
                    target_lang = "ja"



            else:
                return text
        except:
            target_lang = "ja"

    try:
        if target_lang == 'ja':
            return process_single_text(text)
        elif target_lang == 'zh':
            return process_chinese_text(text)
        elif target_lang == 'ar':
            return process_arabic_text(text)
        elif target_lang == 'ru':
            return process_russian_text(text)
        elif target_lang == 'hi':
            return process_hindi_text(text)
        
        return text

    except Exception as e:
        print(f"Annotation Error: {e}")
        return text


def process_single_text(text: str) -> str:
    """
    Helper function to process a single string with pykakasi.
    Ensures only Kanji-containing segments get ruby tags.
    """
    if not text:
        return text
        
    result = kks.convert(text)
    annotated_html = ""
    for item in result:
        orig = item['orig']
        hira = item['hira']
        
        # Check if the segment actually contains Kanji
        # (Japanese Kanji range: 4E00-9FAF)
        has_kanji = any('\u4e00' <= c <= '\u9faf' for c in orig)
        
        if has_kanji and orig != hira:
            annotated_html += f"<ruby>{orig}<rt>{hira}</rt></ruby>"
        else:
            annotated_html += orig
            
    return annotated_html


def process_chinese_text(text: str) -> str:
    """
    Uses pypinyin to wrap Chinese characters in <ruby> tags with Pinyin.
    Latin script and punctuation are preserved as-is.
    """
    # Use pinyin() with errors=default to preserve non-chinese chars
    # We use heteronym=False to get the most common reading
    result = pinyin(text, style=Style.TONE, errors='default')
    annotated_html = ""
    
    # We need to map the pinyin results back to the original characters
    # Since pinyin() might group characters, we'll process character by character
    # for maximum precision with ruby tags.
    for char in text:
        # Check if it's a Hanzi
        if '\u4e00' <= char <= '\u9fff':
            # Get pinyin for this single character
            py = pinyin(char, style=Style.TONE, errors='default')[0][0]
            annotated_html += f"<ruby>{char}<rt>{py}</rt></ruby>"
        else:
            annotated_html += char
                
    return annotated_html


# Russian Transliteration Mapping (ISO 9 / standard)
RU_MAP = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo', 'ж': 'zh',
    'з': 'z', 'и': 'i', 'й': 'j', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o',
    'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'c',
    'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ъ': '"', 'ы': 'y', 'ь': "'", 'э': 'e', 'ю': 'yu', 'я': 'ya',
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo', 'Ж': 'Zh',
    'З': 'Z', 'И': 'I', 'Й': 'J', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O',
    'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U', 'Ф': 'F', 'Х': 'H', 'Ц': 'C',
    'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch', 'Ъ': '"', 'Ы': 'Y', 'Ь': "'", 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
}

# Hindi Transliteration Mapping (Simplified Devanagari)
HI_MAP = {
    'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo', 'ऋ': 'ri', 'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au',
    'क': 'ka', 'ख': 'kha', 'ग': 'ga', 'घ': 'gha', 'ङ': 'nga',
    'च': 'cha', 'छ': 'chha', 'ज': 'ja', 'झ': 'jha', 'ञ': 'nya',
    'ट': 'ta', 'ठ': 'tha', 'ड': 'da', 'ढ': 'dha', 'ण': 'na',
    'त': 'ta', 'थ': 'tha', 'द': 'da', 'ध': 'dha', 'न': 'na',
    'प': 'pa', 'फ': 'pha', 'ब': 'ba', 'भ': 'bha', 'म': 'ma',
    'य': 'ya', 'र': 'ra', 'ल': 'la', 'व': 'va', 'श': 'sha', 'ष': 'sha', 'स': 'sa', 'ह': 'ha',
    'ा': 'a', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo', 'ृ': 'ri', 'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', 'ं': 'n'
}

def process_hindi_text(text: str) -> str:
    """
    Lightweight Hindi transliteration.
    """
    annotated_html = ""
    hindi_pattern = re.compile(r'[\u0900-\u097F]')
    
    for char in text:
        if hindi_pattern.match(char):
            trans = HI_MAP.get(char, char)
            annotated_html += f"<ruby>{char}<rt>{trans}</rt></ruby>"
        else:
            annotated_html += char
            
    return annotated_html

def process_russian_text(text: str) -> str:

    """
    Lightweight Russian transliteration.
    """
    annotated_html = ""
    russian_pattern = re.compile(r'[\u0400-\u04FF]')
    
    for char in text:
        if russian_pattern.match(char):
            trans = RU_MAP.get(char, char)
            annotated_html += f"<ruby>{char}<rt>{trans}</rt></ruby>"
        else:
            annotated_html += char
            
    return annotated_html

def process_arabic_text(text: str) -> str:

    """
    Lightweight Arabic transliteration.
    Wraps Arabic characters in ruby tags with their Latin equivalents.
    """
    annotated_html = ""
    # Regex to catch Arabic characters
    arabic_pattern = re.compile(r'[\u0600-\u06FF]')
    
    for char in text:
        if arabic_pattern.match(char):
            # Use mapping if exists, otherwise keep char
            trans = AR_MAP.get(char, char)
            annotated_html += f"<ruby>{char}<rt>{trans}</rt></ruby>"
        else:
            annotated_html += char
            
    return annotated_html

async def explain_text(text: str, context: str = "") -> str:
    """
    Uses Gemini to explain the grammar and meaning of the text.
    """
    if not client:
        return "Gemini API key not configured."
    
    prompt = f"""
    You are yōmu! (ヨォム), a linguistic AI assistant. 
    Analyze the following text: "{text}"
    Context (if available): "{context}"
    
    Provide a concise explanation for a language learner. 
    Include:
    1. Meaning in English.
    2. Grammar breakdown (if applicable).
    3. How to use it in a sentence.
    
    Keep it cinematic, helpful, and very brief (max 100 words).
    Use simple HTML formatting (e.g., <strong>, <br>).
    """
    
    try:
        # Using the newer SDK method with a current model
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )

        return response.text
    except Exception as e:
        print(f"Gemini Error: {e}")
        return f"Could not generate explanation: {str(e)}"


def get_mock_annotation(text: str) -> str:



    """
    Fallback mock function.
    """
    return text.replace("漢字", "<ruby>漢字<rt>かんじ</rt></ruby>")
