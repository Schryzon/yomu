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
                
                # Colloquial overrides for common Kanji readings (e.g. 身体 -> からだ instead of しんたい)
                reading_overrides = {
                    "身体": "からだ",
                }
                if orig in reading_overrides:
                    hira = reading_overrides[orig]
                
                # Double check for Kanji to apply ruby
                has_kanji = any('\u4e00' <= c <= '\u9faf' for c in orig)
                if has_kanji and orig != hira:
                    # Split mixed Kanji/Okurigana to keep Hiragana/Katakana okurigana unannotated
                    # Example: orig="積み上げ", hira="つみあげ" -> "<ruby>積<rt>つ</rt></ruby>み<ruby>上<rt>あ</rt></ruby>げ"
                    kanji_pattern = re.compile(r'([\u4e00-\u9faf]+)')
                    kanji_parts = kanji_pattern.split(orig)
                    
                    aligned_html = ""
                    hira_idx = 0
                    
                    for idx, kp in enumerate(kanji_parts):
                        if not kp:
                            continue
                        
                        if kanji_pattern.match(kp):
                            # Kanji block: find the next non-kanji anchor to determine hira slice
                            next_anchor = kanji_parts[idx+1] if idx + 1 < len(kanji_parts) else None
                            if next_anchor:
                                # Lock alignment search window by starting after the minimum reading characters
                                search_start = hira_idx + len(kp)
                                next_idx = hira.find(next_anchor, search_start)
                                if next_idx == -1:
                                    next_idx = hira.find(next_anchor, hira_idx)
                                    
                                if next_idx != -1:
                                    kanji_hira = hira[hira_idx:next_idx]
                                    aligned_html += f"<ruby>{kp}<rt>{kanji_hira}</rt></ruby>"
                                    hira_idx = next_idx
                                else:
                                    kanji_hira = hira[hira_idx:]
                                    aligned_html += f"<ruby>{kp}<rt>{kanji_hira}</rt></ruby>"
                                    hira_idx = len(hira)
                            else:
                                kanji_hira = hira[hira_idx:]
                                aligned_html += f"<ruby>{kp}<rt>{kanji_hira}</rt></ruby>"
                                hira_idx = len(hira)
                        else:
                            # Okurigana character: append as plain text and advance reading pointer
                            aligned_html += kp
                            hira_idx += len(kp)
                            
                    annotated_html += f'<span class="yomu-word" data-word="{orig}">{aligned_html}</span>'
                else:
                    annotated_html += orig
        else:
            # It's Latin, numbers, or other scripts - keep it EXACTLY as is
            annotated_html += part
            
    # Post-process common Arabic numeral counters that pykakasi splits incorrectly
    replacements = {
        '1<ruby>人<rt>にん</rt></ruby>': '<ruby>1人<rt>ひとり</rt></ruby>',
        '2<ruby>人<rt>にん</rt></ruby>': '<ruby>2人<rt>ふたり</rt></ruby>',
        '1<ruby>日<rt>にち</rt></ruby>': '<ruby>1日<rt>ついたち</rt></ruby>',
        '2<ruby>日<rt>にち</rt></ruby>': '<ruby>2日<rt>ふつか</rt></ruby>',
        '3<ruby>日<rt>にち</rt></ruby>': '<ruby>3日<rt>みっか</rt></ruby>',
        '4<ruby>日<rt>にち</rt></ruby>': '<ruby>4日<rt>よっか</rt></ruby>',
        '5<ruby>日<rt>にち</rt></ruby>': '<ruby>5日<rt>いつか</rt></ruby>',
        '6<ruby>日<rt>にち</rt></ruby>': '<ruby>6日<rt>むいか</rt></ruby>',
        '7<ruby>日<rt>にち</rt></ruby>': '<ruby>7日<rt>なのか</rt></ruby>',
        '8<ruby>日<rt>にち</rt></ruby>': '<ruby>8日<rt>ようか</rt></ruby>',
        '9<ruby>日<rt>にち</rt></ruby>': '<ruby>9日<rt>ここのか</rt></ruby>',
        '10<ruby>日<rt>にち</rt></ruby>': '<ruby>10日<rt>とおか</rt></ruby>',
        '20<ruby>日<rt>にち</rt></ruby>': '<ruby>20日<rt>はつか</rt></ruby>'
    }
    for bad, good in replacements.items():
        annotated_html = annotated_html.replace(bad, good)
            
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
            annotated_html += f'<span class="yomu-word" data-word="{char}"><ruby>{char}<rt>{py}</rt></ruby></span>'
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
    # Consonants (Inherent 'a') - Corrected Unicode order
    '\u1B13': 'ka', '\u1B14': 'kha', '\u1B15': 'ga', '\u1B16': 'gha', '\u1B17': 'nga',
    '\u1B18': 'ca', '\u1B19': 'cha', '\u1B1A': 'ja', '\u1B1B': 'jha', '\u1B1C': 'nya',
    '\u1B1D': 'ta', '\u1B1E': 'tha', '\u1B1F': 'da', '\u1B20': 'dha', '\u1B21': 'na',
    '\u1B22': 'ta', '\u1B23': 'tha', '\u1B24': 'da', '\u1B25': 'dha', '\u1B26': 'na',
    '\u1B27': 'pa', '\u1B28': 'pha', '\u1B29': 'ba', '\u1B2A': 'bha', '\u1B2B': 'ma',
    '\u1B2C': 'ya', '\u1B2D': 'ra', '\u1B2E': 'la', '\u1B2F': 'wa', '\u1B30': 'sa',
    '\u1B31': 'sa', '\u1B32': 'sa', '\u1B33': 'ha',
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
    Lightweight Hindi transliteration (Word-level to preserve shaping).
    """
    annotated_html = ""
    hindi_pattern = re.compile(r'([\u0900-\u097F]+)')
    parts = hindi_pattern.split(text)
    
    for part in parts:
        if not part:
            continue
        if hindi_pattern.match(part):
            trans = "".join(HI_MAP.get(char, char) for char in part)
            annotated_html += f'<span class="yomu-word" data-word="{part}"><ruby>{part}<rt>{trans}</rt></ruby></span>'
        else:
            annotated_html += part
            
    return annotated_html

def process_russian_text(text: str) -> str:
    """
    Lightweight Russian transliteration (Word-level).
    Supports standard, supplementary, and all extended Cyrillic Unicode blocks.
    """
    annotated_html = ""
    russian_pattern = re.compile(r'([\u0400-\u04FF\u0500-\u052F\u2DE0-\u2DFF\uA640-\uA69F\u1C80-\u1C8F]+)')
    parts = russian_pattern.split(text)
    
    for part in parts:
        if not part:
            continue
        if russian_pattern.match(part):
            trans = "".join(RU_MAP.get(char, char) for char in part)
            annotated_html += f'<span class="yomu-word" data-word="{part}"><ruby>{part}<rt>{trans}</rt></ruby></span>'
        else:
            annotated_html += part
            
    return annotated_html

def process_arabic_text(text: str) -> str:
    """
    Lightweight Arabic transliteration (Word-level to preserve cursive connections).
    """
    annotated_html = ""
    arabic_pattern = re.compile(r'([\u0600-\u06FF]+)')
    parts = arabic_pattern.split(text)
    
    for part in parts:
        if not part:
            continue
        if arabic_pattern.match(part):
            trans = "".join(AR_MAP.get(char, char) for char in part)
            annotated_html += f'<span class="yomu-word" data-word="{part}"><ruby>{part}<rt>{trans}</rt></ruby></span>'
        else:
            annotated_html += part
            
    return annotated_html

def process_balinese_text(text: str) -> str:
    """
    Advanced Balinese transliteration handling Adeg-adeg and Pangangge (Word-level).
    """
    annotated_html = ""
    bali_pattern = re.compile(r'([\u1B00-\u1B7F]+)')
    parts = bali_pattern.split(text)
    
    for part in parts:
        if not part:
            continue
        if bali_pattern.match(part):
            trans = ""
            i = 0
            while i < len(part):
                char = part[i]
                char_trans = BALI_MAP.get(char, "")
                
                if not char_trans:
                    trans += char
                    i += 1
                    continue

                next_char = part[i+1] if i + 1 < len(part) else ""
                
                if next_char == '\u1B44': # Adeg-adeg
                    trans += char_trans[:-1] if char_trans.endswith('a') else char_trans
                    i += 2 # Skip adeg-adeg processing so we don't output anything for it
                elif next_char in ['\u1B35', '\u1B36', '\u1B37', '\u1B38', '\u1B39', '\u1B3E', '\u1B40']: # Vowels
                    vowel = BALI_MAP.get(next_char, 'a')
                    trans += (char_trans[:-1] if char_trans.endswith('a') else char_trans) + vowel
                    i += 2
                else:
                    trans += char_trans
                    i += 1
            
            # Wrap the whole original word (including adeg-adeg and vowels) in ruby
            annotated_html += f'<span class="yomu-word" data-word="{part}"><ruby>{part}<rt>{trans}</rt></ruby></span>'
        else:
            annotated_html += part
            
    return annotated_html

async def explain_text(text: str, context: str = "") -> str:
    """
    Uses Gemini to explain the grammar and meaning of the text.
    """
    if not client:
        return "Gemini API key not configured."
    
    prompt = f"""
    Analyze the following target word/phrase:
    [[ {text} ]]
    
    Surrounding Context (use this to determine the exact meaning and provide previous/next sentence nuance):
    "{context}"
    
    Provide a direct, highly concise linguistic analysis for a language learner. 
    Do NOT include any greetings, introductory phrases, or chatty sentences (e.g., do not say "Here is the analysis" or "I am yomu!"). Get straight to the analysis.
    
    Format the output EXACTLY like this:
    <strong>Meaning:</strong> [Direct English meaning, using the surrounding context for accuracy]<br>
    <strong>Grammar:</strong> [Grammar/parts of speech breakdown relative to the context]<br>
    <strong>Synonyms:</strong> [2-3 relevant synonyms of the target word/phrase in its original script, with parenthesized reading/pronunciation and its rough English meaning. Example: 暴走 (bousou - runaway/out of control)]<br>
    <strong>Antonyms:</strong> [1-2 relevant antonyms of the target word/phrase in its original script, with parenthesized reading/pronunciation and its rough English meaning, if applicable]<br>
    <strong>Related Words:</strong> [1-2 other vocabulary words related structurally, conceptually, or sharing semantic roots, with parenthesized reading/pronunciation and their rough English meanings]<br>
    <strong>Usage Example:</strong> [Short example sentence using the target word/phrase]
    
    Keep the total response extremely brief (under 120 words).
    Use ONLY the following HTML tags for formatting: <strong>, <br>, <em>.
    """
    
    try:
        # Using the newer SDK method with a current model
        response = client.models.generate_content(
            model='gemini-flash-latest',
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
            return "<strong>Resource Exhausted</strong><br>The free tier limit for Gemini Flash-latest has been reached. Try again in a moment."
            
        return f"Could not generate explanation: {error_msg}"


def get_mock_annotation(text: str) -> str:



    """
    Fallback mock function.
    """
    return text.replace("漢字", "<ruby>漢字<rt>かんじ</rt></ruby>")
