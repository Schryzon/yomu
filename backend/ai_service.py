# ai_service.py
# Offline local NLP integration for yōmu! using pykakasi
import os
import pykakasi
from pypinyin import pinyin, Style
from langdetect import detect_langs
from google import genai
from dotenv import load_dotenv
import re
import httpx
import json
import datetime
import asyncio

load_dotenv()

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None

# Developer Alerts
WEBHOOK_URL = os.getenv("DEVELOPER_WEBHOOK_URL")
OWNER_ID = os.getenv("WEBHOOK_OWNER_ID")

async def send_developer_alert(error_msg: str, context: str = None):
    """
    Delivers raw error details straight to the developer via Discord (Non-blocking).
    """
    if not WEBHOOK_URL:
        return

    mention = f"<@{OWNER_ID}> " if OWNER_ID else ""
    payload = {
        "content": f"{mention}🚨 **yōmu! Developer Alert**",
        "embeds": [{
            "title": "Gemini API Error",
            "description": f"```{error_msg}```",
            "color": 15158332, # Red
            "fields": [
                {"name": "Timestamp", "value": datetime.datetime.now().isoformat(), "inline": True},
                {"name": "Context", "value": context if context else "N/A", "inline": False}
            ],
            "footer": {"text": "yōmu! Production Layer"}
        }]
    }

    try:
        async with httpx.AsyncClient() as client:
            await client.post(WEBHOOK_URL, json=payload, timeout=5.0)
    except Exception as e:
        print(f"Failed to send webhook: {e}")



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


async def get_real_annotation(text: str, target_lang: str = "auto") -> str:
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
            annotated_parts.append(await get_real_annotation(part.strip(), target_lang))
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
                elif re.search(r'[\u1B00-\u1B7F]', text):
                    target_lang = "ban" # Balinese ISO code
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
        elif target_lang == 'ban':
            return process_balinese_text(text)
        
        return text

    except Exception as e:
        error_msg = str(e)
        print(f"Annotation Error: {error_msg}")
        
        # Deliver to developer (awaiting now!)
        await send_developer_alert(error_msg, context=f"Annotation Batch: {text[:100]}...")
        
        if "429" in error_msg:
            print("CRITICAL: Gemini Rate Limit (429) hit during annotation.")
        return text


def process_single_text(text: str) -> str:
    """
    Helper function to process a single string with pykakasi.
    Protects Latin/special characters by only processing Japanese script blocks.
    """
    if not text:
        return text
        
    # Regex to identify Japanese script blocks (Kanji, Hiragana, Katakana, and Japanese punctuation)
    # This ensures "yōmu!" and other Latin text is never even seen by pykakasi.
    jp_pattern = re.compile(r'([\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF\u3000-\u303F]+)')
    parts = jp_pattern.split(text)
    
    annotated_html = ""
    for part in parts:
        if not part:
            continue
            
        # If the part matches our Japanese script pattern, process it
        if jp_pattern.match(part):
            result = kks.convert(part)
            for item in result:
                orig = item['orig']
                hira = item['hira']
                
                # Double check for Kanji to apply ruby
                has_kanji = any('\u4e00' <= c <= '\u9faf' for c in orig)
                if has_kanji and orig != hira:
                    annotated_html += f"<ruby>{orig}<rt>{hira}</rt></ruby>"
                else:
                    annotated_html += orig
        else:
            # It's Latin, numbers, or other scripts - keep it EXACTLY as is
            annotated_html += part
            
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

# Balinese Transliteration Mapping (Wianjana & Pangangge)
BALI_MAP = {
    # Consonants (Inherent 'a')
    '\u1B13': 'ha', '\u1B14': 'na', '\u1B15': 'ca', '\u1B16': 'ra', '\u1B17': 'ka',
    '\u1B18': 'da', '\u1B19': 'ta', '\u1B1A': 'sa', '\u1B1B': 'wa', '\u1B1C': 'la',
    '\u1B1D': 'ma', '\u1B1E': 'ga', '\u1B1F': 'ba', '\u1B20': 'nga', '\u1B21': 'pa',
    '\u1B22': 'ja', '\u1B23': 'ya', '\u1B24': 'nya',
    # Vowel Signs (Pangangge)
    '\u1B35': 'e',  '\u1B36': 'i',  '\u1B37': 'i',  '\u1B38': 'u',  '\u1B39': 'u',
    '\u1B3E': 'e',  '\u1B40': 'o',  '\u1B3A': 'ra', '\u1B3C': 'la',
    # Final Consonants
    '\u1B02': 'ng', '\u1B03': 'r',  '\u1B04': 'h',
    # Adeg-adeg (Killer)
    '\u1B44': '' 
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
    """
    annotated_html = ""
    arabic_pattern = re.compile(r'[\u0600-\u06FF]')
    for char in text:
        if arabic_pattern.match(char):
            trans = AR_MAP.get(char, char)
            annotated_html += f"<ruby>{char}<rt>{trans}</rt></ruby>"
        else:
            annotated_html += char
    return annotated_html

def process_balinese_text(text: str) -> str:
    """
    Advanced Balinese transliteration handling Adeg-adeg and Pangangge.
    """
    annotated_html = ""
    # Regex to catch Balinese script characters
    bali_pattern = re.compile(r'[\u1B00-\u1B7F]')
    
    i = 0
    while i < len(text):
        char = text[i]
        
        if bali_pattern.match(char):
            # Consonant or special mark
            trans = BALI_MAP.get(char, "")
            
            if not trans:
                annotated_html += char
                i += 1
                continue

            # Peak ahead to see if it's killed or modified
            next_char = text[i+1] if i + 1 < len(text) else ""
            
            if next_char == '\u1B44': # Adeg-adeg
                trans = trans[:-1] if trans.endswith('a') else trans
                annotated_html += f"<ruby>{char}<rt>{trans}</rt></ruby>"
                i += 2 # Skip adeg-adeg
                continue
            
            elif next_char in ['\u1B35', '\u1B36', '\u1B37', '\u1B38', '\u1B39', '\u1B3E', '\u1B40']: # Vowels
                vowel = BALI_MAP.get(next_char, 'a')
                trans = (trans[:-1] if trans.endswith('a') else trans) + vowel
                # Combine char + vowel in ruby for clarity
                annotated_html += f"<ruby>{char}{next_char}<rt>{trans}</rt></ruby>"
                i += 2
                continue
            
            else:
                # Inherent 'a' remains
                annotated_html += f"<ruby>{char}<rt>{trans}</rt></ruby>"
                i += 1
        else:
            annotated_html += char
            i += 1
            
    return annotated_html

async def explain_text(text: str, context: str = "") -> str:
    """
    Uses Gemini to explain the grammar and meaning of the text.
    """
    if not client:
        return "Gemini API key not configured."
    
    prompt = f"""
    You are yōmu! (ヨォム), a linguistic AI assistant. 
    Analyze the following user-provided text within the brackets: 
    [[ {text} ]]
    
    Context (if available): "{context}"
    
    Provide a concise explanation for a language learner. 
    Include:
    1. Meaning in English.
    2. Grammar breakdown (if applicable).
    3. How to use it in a sentence.
    
    Keep it cinematic, helpful, and very brief (max 100 words).
    Use ONLY the following HTML tags for formatting: <strong>, <br>, <em>.
    """
    
    try:
        # Using the newer SDK method with a current model
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )

        return response.text
    except Exception as e:
        error_msg = str(e)
        print(f"Gemini Error: {error_msg}")
        
        # Deliver to developer (awaiting now!)
        await send_developer_alert(error_msg, context=f"Deep Analysis: {text[:100]}")
        
        if "429" in error_msg:
            return "<strong>Quota Exceeded (429)</strong><br>Gemini is currently catching its breath. Please wait a minute before trying deep analysis again."
        elif "RESOURCE_EXHAUSTED" in error_msg:
            return "<strong>Resource Exhausted</strong><br>The free tier limit for Gemini 2.0 Flash has been reached. Try again in a moment."
            
        return f"Could not generate explanation: {error_msg}"


def get_mock_annotation(text: str) -> str:



    """
    Fallback mock function.
    """
    return text.replace("漢字", "<ruby>漢字<rt>かんじ</rt></ruby>")
