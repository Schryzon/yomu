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

# Arabic Transliteration — Tashkeel-aware with emphatic consonant distinction and Persian/Urdu support
AR_CONSONANTS = {
    'ب': 'b', 'ت': 't', 'ث': 'th', 'ج': 'j', 'ح': 'ḥ', 'خ': 'kh',
    'د': 'd', 'ذ': 'dh', 'ر': 'r', 'ز': 'z', 'س': 's', 'ش': 'sh',
    'ص': 'ṣ', 'ض': 'ḍ', 'ط': 'ṭ', 'ظ': 'ẓ', 'ع': "'", 'غ': 'gh',
    'ف': 'f', 'ق': 'q', 'ك': 'k', 'ل': 'l', 'م': 'm', 'ن': 'n',
    'ه': 'h', 'و': 'w', 'ي': 'y',
    # Persian, Urdu, Pashto, Kurdish extensions
    'پ': 'p', 'چ': 'ch', 'ژ': 'zh', 'گ': 'g',
    'ٹ': 'ṭ', 'ڈ': 'ḍ', 'ڑ': 'ṛ', 'ں': 'n', 'ھ': 'h', 'ے': 'e', 'ی': 'y',
}

AR_SPECIAL = {
    'ا': 'ā', 'أ': 'a', 'إ': 'i', 'آ': 'ā', 'ٱ': 'a',  # alef variants
    'ة': 'h',   # ta marbuta
    'ء': "'",   # hamza
    'ؤ': "'",   # hamza on waw
    'ئ': "'",   # hamza on ya
    'ى': 'ā',   # alef maqsura
}

# Tashkeel diacritics (short vowels, shadda, sukun, tanwin)
AR_TASHKEEL = {
    '\u064E': 'a',    # fatha
    '\u064F': 'u',    # damma
    '\u0650': 'i',    # kasra
    '\u0651': None,   # shadda (handled specially)
    '\u0652': '',     # sukun
    '\u064B': 'an',   # tanwin fath
    '\u064C': 'un',   # tanwin damm
    '\u064D': 'in',   # tanwin kasr
    '\u0670': 'ā',    # dagger alef
}

# Sun letters — al- assimilates before these
AR_SUN_LETTERS = set('تثدذرزسشصضطظلن')


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

    # Smart language detection logic
    if target_lang == "auto":
        if len(text.strip()) == 0:
            return text

        # Unicode heuristics first (faster and more reliable than langdetect for CJK)
        has_hiragana = bool(re.search(r'[\u3040-\u309F]', text))
        has_katakana = bool(re.search(r'[\u30A0-\u30FF]', text))
        has_han = bool(re.search(r'[\u4E00-\u9FFF]', text))

        if has_hiragana or has_katakana:
            # Kana present = definitely Japanese
            target_lang = "ja"
        elif has_han:
            # Pure Han only — langdetect is unreliable here, use confidence threshold
            try:
                langs = detect_langs(text)
                top = langs[0]
                if top.lang == 'ja':
                    target_lang = "ja"
                elif top.lang.startswith('zh') and top.prob < 0.8:
                    # Low confidence Chinese on Han-only text = probably Japanese
                    target_lang = "ja"
                elif top.lang.startswith('zh'):
                    target_lang = "zh"
                else:
                    target_lang = "ja"  # default for ambiguous Han
            except:
                target_lang = "ja"
        elif re.search(r'[\u1B00-\u1B7F]', text):
            target_lang = "ban"
        else:
            # No CJK/Balinese — use langdetect for Arabic/Russian/Hindi/etc
            try:
                langs = detect_langs(text)
                top_lang = langs[0].lang
                if top_lang == 'ar':
                    target_lang = "ar"
                elif top_lang == 'ru':
                    target_lang = "ru"
                elif top_lang == 'hi':
                    target_lang = "hi"
                else:
                    target_lang = "ja"  # fallback
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
            return process_cyrillic_text(text)
        elif target_lang == 'hi':
            return process_devanagari_text(text)
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


# Slavic Cyrillic Transliteration — Comprehensive coverage of all Cyrillic letters
RU_MAP = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'ye', 'ё': 'yo', 'ж': 'zh',
    'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o',
    'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts',
    'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'Ye', 'Ё': 'Yo', 'Ж': 'Zh',
    'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O',
    'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U', 'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts',
    'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch', 'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
    # Ukrainian & Belarusian letters
    'ґ': 'g', 'Ґ': 'G', 'є': 'ye', 'Є': 'Ye', 'і': 'i', 'І': 'I', 'ї': 'yi', 'Ї': 'Yi',
    'ў': 'w', 'Ў': 'W',
    # Serbian & Macedonian letters
    'ђ': 'dj', 'Ђ': 'Dj', 'ј': 'j', 'Ј': 'J', 'љ': 'lj', 'Љ': 'Lj', 'њ': 'nj', 'Њ': 'Nj',
    'ћ': 'ch', 'Ћ': 'Ch', 'џ': 'dzh', 'Џ': 'Dzh', 'ѕ': 'dz', 'Ѕ': 'Dz',
    # Old Church Slavonic & Archaic letters
    'ѣ': 'e', 'Ѣ': 'E', 'ѳ': 'f', 'Ѳ': 'F', 'ѵ': 'i', 'Ѵ': 'I',
}

# Vowels and soft/hard signs that trigger е/Е → ye (otherwise е/Е → e after consonants)
RU_VOWELS = set('аеёиоуыэюяєіїАЕЁИОУЫЭЮЯЄІЇ')
RU_SIGNS = set('ъьЪЬ')

# Devanagari Transliteration — Fully comprehensive for Sanskrit, Hindi, Marathi, and Konkani
HI_VOWELS = {
    'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo',
    'ऋ': 'ri', 'ॠ': 'ree', 'ऌ': 'lri', 'ॡ': 'lree',
    'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au',
    'ॲ': 'ae', 'ऑ': 'o', 'ऎ': 'e', 'ऒ': 'o',
}

HI_CONSONANTS = {
    'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
    'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
    'ट': 'ṭ', 'ठ': 'ṭh', 'ड': 'ḍ', 'ढ': 'ḍh', 'ण': 'ṇ',
    'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
    'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
    'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v',
    'श': 'sh', 'ष': 'sh', 'स': 's', 'ह': 'h',
    # Marathi/Sanskrit/Dravidian extensions
    'ळ': 'ḷ', 'ऴ': 'zh', 'ऩ': 'n', 'ऱ': 'ṟ',
}

# Nukta consonants (borrowed phonemes from Persian/Arabic)
HI_NUKTA = {
    'क़': 'q', 'ख़': 'kh', 'ग़': 'gh', 'ज़': 'z',
    'ड़': 'ṛ', 'ढ़': 'ṛh', 'फ़': 'f',
}

# Vowel signs (matras)
HI_MATRAS = {
    'ा': 'aa', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo',
    'ृ': 'ri', 'ॄ': 'ree', 'ॢ': 'lri', 'ॣ': 'lree',
    'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au',
    'ॅ': 'ae', 'ॉ': 'o', 'ॆ': 'e', 'ॊ': 'o',
}

# Modifiers (anusvara, chandrabindu, visarga)
HI_MODIFIERS = {
    'ं': 'n',   # anusvara
    'ँ': 'n',   # chandrabindu
    'ः': 'h',   # visarga
}

HI_HALANT = '्'       # virama
HI_NUKTA_MARK = '़'   # nukta diacritic mark

# Balinese Transliteration — Complete with independent vowels and pangangge
BALI_INDEPENDENT_VOWELS = {
    '\u1B05': 'a',   '\u1B06': 'aa',  '\u1B07': 'i',   '\u1B08': 'ii',
    '\u1B09': 'u',   '\u1B0A': 'uu',  '\u1B0B': 're',  '\u1B0C': 'ree',
    '\u1B0D': 'le',  '\u1B0E': 'lee', '\u1B0F': 'e',   '\u1B10': 'ai',
    '\u1B11': 'o',   '\u1B12': 'au',
}

BALI_CONSONANTS = {
    '\u1B13': 'ka',  '\u1B14': 'kha', '\u1B15': 'ga',  '\u1B16': 'gha', '\u1B17': 'nga',
    '\u1B18': 'ca',  '\u1B19': 'cha', '\u1B1A': 'ja',  '\u1B1B': 'jha', '\u1B1C': 'nya',
    '\u1B1D': 'tta', '\u1B1E': 'ttha','\u1B1F': 'dda', '\u1B20': 'ddha','\u1B21': 'nna',
    '\u1B22': 'ta',  '\u1B23': 'tha', '\u1B24': 'da',  '\u1B25': 'dha', '\u1B26': 'na',
    '\u1B27': 'pa',  '\u1B28': 'pha', '\u1B29': 'ba',  '\u1B2A': 'bha', '\u1B2B': 'ma',
    '\u1B2C': 'ya',  '\u1B2D': 'ra',  '\u1B2E': 'la',  '\u1B2F': 'wa',  '\u1B30': 'sha',
    '\u1B31': 'ssa', '\u1B32': 'sa',  '\u1B33': 'ha',
}

# Vowel signs that replace the inherent 'a'
BALI_VOWEL_SIGNS = {
    '\u1B35': 'aa',  # tedung (long a) — was incorrectly 'e'
    '\u1B36': 'i',   # ulu
    '\u1B37': 'ii',  # ulu sari (long i)
    '\u1B38': 'u',   # suku
    '\u1B39': 'uu',  # suku ilut (long u)
    '\u1B3A': 're',  # ra repa (vocalic r)
    '\u1B3B': 'ree', # ra repa tedung
    '\u1B3C': 'le',  # la lenga (vocalic l)
    '\u1B3D': 'lee', # la lenga tedung
    '\u1B3E': 'e',   # taling
    '\u1B3F': 'ai',  # taling repa
    '\u1B40': 'o',   # taling tedung
    '\u1B41': 'au',  # taling repa tedung
    '\u1B42': 'e',   # pepet (schwa)
    '\u1B43': 'oe',  # pepet tedung
}

# Pangangge tengenan (final consonant modifiers)
BALI_MODIFIERS = {
    '\u1B00': '',    # ulu ricem (decorative)
    '\u1B01': '',    # ulu candra
    '\u1B02': 'ng',  # cecek (final -ng)
    '\u1B03': 'r',   # surang (final -r)
    '\u1B04': 'h',   # bisah (visarga, final -h)
}

BALI_ADEG_ADEG = '\u1B44'  # vowel killer

def process_devanagari_text(text: str) -> str:
    """
    Devanagari transliteration with halant (virama) and schwa deletion.
    Handles consonant clusters, nukta consonants, matras, and modifiers.
    """
    annotated_html = ""
    devanagari_pattern = re.compile(r'([\u0900-\u097F]+)')
    parts = devanagari_pattern.split(text)
    
    for part in parts:
        if not part:
            continue
        if devanagari_pattern.match(part):
            trans = _transliterate_devanagari_word(part)
            annotated_html += f'<span class="yomu-word" data-word="{part}"><ruby>{part}<rt>{trans}</rt></ruby></span>'
        else:
            annotated_html += part
            
    return annotated_html

def _transliterate_devanagari_word(word: str) -> str:
    """
    Transliterate a single Devanagari word using a phonemic unit parser
    and applying the standard medial and final schwa deletion rules.
    """
    if not word:
        return word

    units = []
    i = 0
    while i < len(word):
        char = word[i]
        next_char = word[i + 1] if i + 1 < len(word) else ''
        
        # 1. Nukta combination
        if char in HI_CONSONANTS and next_char == HI_NUKTA_MARK:
            nukta_combo = char + next_char
            consonant = HI_NUKTA.get(nukta_combo, HI_CONSONANTS[char])
            i += 2
        elif char in HI_CONSONANTS:
            consonant = HI_CONSONANTS[char]
            i += 1
        elif char in HI_VOWELS:
            # Independent vowel
            units.append({
                'type': 'V',
                'vowel': HI_VOWELS[char],
                'modifier': ''
            })
            i += 1
            # Check for trailing modifier
            if i < len(word) and word[i] in HI_MODIFIERS:
                units[-1]['modifier'] = HI_MODIFIERS[word[i]]
                i += 1
            continue
        elif char in HI_MODIFIERS:
            # Standalone modifier
            units.append({
                'type': 'M',
                'modifier': HI_MODIFIERS[char]
            })
            i += 1
            continue
        else:
            # Pass through other symbols
            units.append({
                'type': 'OTHER',
                'char': char
            })
            i += 1
            continue
            
        # We parsed a consonant, check what follows it
        vowel = 'a' # default inherent schwa
        has_halant = False
        
        if i < len(word) and word[i] == HI_HALANT:
            vowel = '' # killed by virama
            has_halant = True
            i += 1
        elif i < len(word) and word[i] in HI_MATRAS:
            vowel = HI_MATRAS[word[i]]
            i += 1
            
        modifier = ''
        if i < len(word) and word[i] in HI_MODIFIERS:
            modifier = HI_MODIFIERS[word[i]]
            i += 1
            
        units.append({
            'type': 'CV',
            'consonant': consonant,
            'vowel': vowel,
            'has_halant': has_halant,
            'modifier': modifier
        })

    # Pass 2: Apply schwa deletion
    # Count vocalic syllables in the word to check deletion viability
    vocalic_indices = [idx for idx, u in enumerate(units) if u['type'] == 'V' or (u['type'] == 'CV' and u['vowel'] != '')]
    
    # We will keep track of active vowels at each index
    active_vowel = [False] * len(units)
    for idx in vocalic_indices:
        active_vowel[idx] = True

    # 1. Word-final schwa deletion (if there's more than one vocalic unit)
    if len(vocalic_indices) > 1:
        last_voc_idx = vocalic_indices[-1]
        last_unit = units[last_voc_idx]
        if last_unit['type'] == 'CV' and last_unit['vowel'] == 'a' and not last_unit['has_halant']:
            # Exception: keep final 'a' if last consonant is 'y' preceded by a halant unit (e.g. 'surya')
            is_surya_exception = False
            if last_unit['consonant'] == 'y' and last_voc_idx > 0:
                prev_unit = units[last_voc_idx - 1]
                if prev_unit['type'] == 'CV' and prev_unit['has_halant']:
                    is_surya_exception = True
            
            if not is_surya_exception:
                active_vowel[last_voc_idx] = False

    # 2. Medial schwa deletion (ə → ∅ / VC_CV)
    for k in range(1, len(units) - 1):
        unit = units[k]
        if unit['type'] == 'CV' and unit['vowel'] == 'a' and not unit['has_halant'] and active_vowel[k]:
            # The preceding and succeeding units must both have active vowels
            if active_vowel[k - 1] and active_vowel[k + 1]:
                active_vowel[k] = False

    # Pass 3: Assemble transliteration
    result = []
    for idx, u in enumerate(units):
        if u['type'] == 'V':
            result.append(u['vowel'])
            if u['modifier']:
                result.append(u['modifier'])
        elif u['type'] == 'CV':
            result.append(u['consonant'])
            if active_vowel[idx]:
                result.append(u['vowel'])
            if u['modifier']:
                result.append(u['modifier'])
        elif u['type'] == 'OTHER':
            result.append(u['char'])
            
    return ''.join(result)

def process_cyrillic_text(text: str) -> str:
    """
    Phonetic Cyrillic transliteration (learner-friendly).
    Context-aware: е→ye word-initially and after vowels/signs, е→e after consonants.
    """
    annotated_html = ""
    cyrillic_pattern = re.compile(r'([\u0400-\u04FF\u0500-\u052F\u2DE0-\u2DFF\uA640-\uA69F\u1C80-\u1C8F]+)')
    parts = cyrillic_pattern.split(text)
    
    for part in parts:
        if not part:
            continue
        if cyrillic_pattern.match(part):
            trans = _transliterate_cyrillic_word(part)
            annotated_html += f'<span class="yomu-word" data-word="{part}"><ruby>{part}<rt>{trans}</rt></ruby></span>'
        else:
            annotated_html += part
            
    return annotated_html

def _transliterate_cyrillic_word(word: str) -> str:
    """
    Transliterate a single Cyrillic word with context-aware е/Е handling
    and correct uppercase casing propagation for iotated vowels.
    """
    result = []
    
    # Helper to check if the word is largely uppercase to keep uppercase consistency
    is_word_uppercase = word.isupper()
    
    # Smart Ukrainian context detection:
    # If the word contains Ukrainian-specific letters (і, І, ї, Ї, є, Є, ґ, Ґ),
    # we transliterate the Cyrillic 'и'/'И' as Ukrainian 'y'/'Y' instead of Russian 'i'/'I'.
    is_ukrainian = any(c in "іїєґІЇЄҐ" for c in word)
    
    for i, char in enumerate(word):
        prev_char = word[i - 1] if i > 0 else ''
        
        # Determine case propagation for iotated vowels (Е, Ё, Ю, Я, Є, Ї)
        is_uppercase_context = is_word_uppercase or (char.isupper() and i + 1 < len(word) and word[i + 1].isupper())
        
        # Ukrainian context 'и' / 'И' handling
        if is_ukrainian:
            if char == 'и':
                result.append('y')
                continue
            elif char == 'И':
                result.append('Y')
                continue
        
        # Context-aware е/Е handling
        if char == 'е':
            if i == 0 or prev_char in RU_VOWELS or prev_char in RU_SIGNS:
                result.append('ye')
            else:
                result.append('e')
            continue
        elif char == 'Е':
            if i == 0 or prev_char in RU_VOWELS or prev_char in RU_SIGNS:
                result.append('YE' if is_uppercase_context else 'Ye')
            else:
                result.append('E')
            continue
            
        # Standard iotated vowels casing handling
        iotated_map = {
            'ё': 'yo', 'ю': 'yu', 'я': 'ya', 'є': 'ye', 'ї': 'yi',
            'Ё': 'Yo', 'Ю': 'Yu', 'Я': 'Ya', 'Є': 'Ye', 'Ї': 'Yi'
        }
        
        if char in iotated_map:
            trans = iotated_map[char]
            # Ukrainian 'ї' / 'Ї' middle-of-word rule
            if is_ukrainian and char in ['ї', 'Ї'] and i > 0:
                trans = 'i' if char == 'ї' else 'I'
                
            if char.isupper():
                result.append(trans.upper() if is_uppercase_context else trans)
            else:
                result.append(trans)
            continue
            
        # Standard mapping
        result.append(RU_MAP.get(char, char))
        
    return ''.join(result)

def process_arabic_text(text: str) -> str:
    """
    Arabic transliteration with tashkeel (diacritics) support.
    Handles shadda (gemination), tanwin, emphatic consonants, and al- assimilation.
    """
    annotated_html = ""
    arabic_pattern = re.compile(r'([\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]+)')
    parts = arabic_pattern.split(text)
    
    for part in parts:
        if not part:
            continue
        if arabic_pattern.match(part):
            trans = _transliterate_arabic_word(part)
            annotated_html += f'<span class="yomu-word" data-word="{part}"><ruby>{part}<rt>{trans}</rt></ruby></span>'
        else:
            annotated_html += part
            
    return annotated_html

def _transliterate_arabic_word(word: str) -> str:
    """
    Transliterate a single Arabic/Persian/Urdu word with tashkeel awareness and compound prefix parsing.
    """
    if not word:
        return word

    prefix_trans = []
    i = 0

    # We only parse prefixes if they are followed by a definite article 'ال' (al-) or double lam 'لل' (lil-).
    # This prevents false positives on root letters (e.g. 'ب' in 'بيت' or 'و' in 'ولد').
    
    # Helper to check if a definite article starts at index k
    def is_article_at(k):
        if k < len(word):
            # Check for 'ال' / 'ٱل' / 'أل'
            if k + 1 < len(word) and word[k] in ['ا', 'ٱ', 'أ'] and word[k+1] == 'ل':
                return 'al', k + 2
            # Check for 'لل'
            if k + 1 < len(word) and word[k] == 'ل' and word[k+1] == 'ل':
                return 'lil', k + 2
        return None, k

    # Scan for conjunction 'و' or 'ف'
    if i < len(word) and word[i] in ['و', 'ف']:
        conj_char = word[i]
        idx = i + 1
        while idx < len(word) and word[idx] in AR_TASHKEEL:
            idx += 1
        
        art_type, next_idx = is_article_at(idx)
        has_prep_after = False
        prep_idx = idx
        if prep_idx < len(word) and word[prep_idx] in ['ب', 'ل']:
            prep_idx += 1
            while prep_idx < len(word) and word[prep_idx] in AR_TASHKEEL:
                prep_idx += 1
            art_type_after, next_idx_after = is_article_at(prep_idx)
            if art_type_after:
                has_prep_after = True
                
        if art_type or has_prep_after:
            prefix_trans.append("wa-" if conj_char == 'و' else "fa-")
            i = idx

    # Scan for preposition 'ب' or 'ل'
    if i < len(word) and word[i] in ['ب', 'ل']:
        prep_char = word[i]
        idx = i + 1
        while idx < len(word) and word[idx] in AR_TASHKEEL:
            idx += 1
            
        # If preposition is 'ل' (li-), and next char is 'ل', this is the definite article lam!
        if prep_char == 'ل' and idx < len(word) and word[idx] == 'ل':
            prefix_trans.append("li-")
            i = idx
        else:
            art_type, next_idx = is_article_at(idx)
            if art_type:
                prefix_trans.append("bi-" if prep_char == 'ب' else "li-")
                i = idx

    # Scan for definite article 'ال', 'لل', or single lam 'ل' after a preposition
    is_single_lam_art = (i < len(word) and word[i] == 'ل' and len(prefix_trans) > 0 and prefix_trans[-1] == "li-")
    art_type, next_idx = is_article_at(i)
    
    if art_type == 'al' or is_single_lam_art:
        idx = next_idx if not is_single_lam_art else i + 1
        while idx < len(word) and word[idx] in AR_TASHKEEL:
            idx += 1
        if idx < len(word):
            next_char = word[idx]
            if next_char in AR_SUN_LETTERS:
                sun_trans = AR_CONSONANTS.get(next_char, next_char)
                prefix_trans.append(f"an-" if sun_trans == 'n' else f"a{sun_trans}-")
                i = idx
            else:
                prefix_trans.append("al-")
                i = next_idx if not is_single_lam_art else i + 1
        else:
            prefix_trans.append("al-")
            i = next_idx if not is_single_lam_art else i + 1
    elif art_type == 'lil':
        idx = next_idx
        while idx < len(word) and word[idx] in AR_TASHKEEL:
            idx += 1
        if idx < len(word):
            next_char = word[idx]
            if next_char in AR_SUN_LETTERS:
                sun_trans = AR_CONSONANTS.get(next_char, next_char)
                prefix_trans.append(f"li-a{sun_trans}-")
                i = idx
            else:
                prefix_trans.append("lil-")
                i = next_idx
        else:
            prefix_trans.append("lil-")
            i = next_idx

    result = []
    if prefix_trans:
        result.append(''.join(prefix_trans))

    while i < len(word):
        char = word[i]

        # Context-aware ta marbuta 'ة': 'h' if preceded by a vowel/fatha, 'ah' if unvocalized
        if char == 'ة':
            if result and result[-1] in ['a', 'i', 'u', 'ā', 'ī', 'ū']:
                result.append('h')
            else:
                result.append('ah')
            i += 1
            continue

        # Rule-based word-initial alif: 'ا' at start of remaining word transliterates as 'a' (or empty if followed by diacritic)
        if char == 'ا' and i == 0:
            if i + 1 < len(word) and word[i + 1] in AR_TASHKEEL:
                base_trans = ""
            else:
                base_trans = "a"
            i += 1
            result.append(base_trans)
            continue

        if char in AR_CONSONANTS or char in AR_SPECIAL:
            base_trans = AR_CONSONANTS.get(char, AR_SPECIAL.get(char, char))
            i += 1

            # Collect diacritics
            diacritics = []
            has_shadda = False
            while i < len(word) and word[i] in AR_TASHKEEL:
                if word[i] == '\u0651': # Shadda
                    has_shadda = True
                else:
                    diacritics.append(word[i])
                i += 1

            # Heuristic for unvocalized long vowels (ya -> ī, waw -> ū)
            if not diacritics and not has_shadda and result:
                last_segment = result[-1]
                # Check if the last character in the result is a consonant
                if last_segment and last_segment[-1].lower() not in set("aeiouāīū'"):
                    if char == 'ي':
                        base_trans = 'ī'
                    elif char == 'و':
                        base_trans = 'ū'

            if has_shadda:
                result.append(base_trans + base_trans)
            else:
                result.append(base_trans)

            for d in diacritics:
                v = AR_TASHKEEL.get(d)
                if v:
                    result.append(v)
            continue

        if char in AR_TASHKEEL:
            v = AR_TASHKEEL.get(char)
            if v:
                result.append(v)
            i += 1
            continue

        result.append(char)
        i += 1

    text = ''.join(result)

    # Fix vocalization sequences and endings
    text = text.replace('aā', 'ā')
    text = text.replace('anā', 'an')
    text = text.replace('iy', 'ī')
    text = text.replace('uw', 'ū')

    # Deduplicate sun letters under shadda assimilation
    for char in AR_SUN_LETTERS:
        if char in AR_CONSONANTS:
            trans = AR_CONSONANTS[char]
            bad_seq = f"a{trans}-{trans}{trans}"
            good_seq = f"a{trans}-{trans}"
            text = text.replace(bad_seq, good_seq)

    return text

def process_balinese_text(text: str) -> str:
    """
    Balinese transliteration with independent vowels, complete pangangge coverage,
    adeg-adeg (virama), and final consonant modifiers.
    """
    annotated_html = ""
    bali_pattern = re.compile(r'([\u1B00-\u1B7F]+)')
    parts = bali_pattern.split(text)
    
    for part in parts:
        if not part:
            continue
        if bali_pattern.match(part):
            trans = _transliterate_balinese_word(part)
            annotated_html += f'<span class="yomu-word" data-word="{part}"><ruby>{part}<rt>{trans}</rt></ruby></span>'
        else:
            annotated_html += part
            
    return annotated_html

def _transliterate_balinese_word(word: str) -> str:
    """
    Transliterate a single Balinese word with adeg-adeg, vowel signs, and modifiers.
    """
    trans = ""
    i = 0
    
    while i < len(word):
        char = word[i]
        next_char = word[i + 1] if i + 1 < len(word) else ""
        
        # Independent vowels (word-initial)
        if char in BALI_INDEPENDENT_VOWELS:
            trans += BALI_INDEPENDENT_VOWELS[char]
            i += 1
            continue
        
        # Pangangge tengenan (final consonant modifiers like cecek, surang, bisah)
        if char in BALI_MODIFIERS:
            trans += BALI_MODIFIERS[char]
            i += 1
            continue
        
        # Consonants
        if char in BALI_CONSONANTS:
            base = BALI_CONSONANTS[char]
            # Strip inherent 'a' for combining
            bare = base[:-1] if base.endswith('a') else base
            i += 1
            
            if i < len(word):
                following = word[i]
                
                # Adeg-adeg: kill inherent vowel → bare consonant
                if following == BALI_ADEG_ADEG:
                    trans += bare
                    i += 1
                # Vowel sign: replaces inherent 'a'
                elif following in BALI_VOWEL_SIGNS:
                    trans += bare + BALI_VOWEL_SIGNS[following]
                    i += 1
                else:
                    # Inherent 'a'
                    trans += base
            else:
                trans += base
            continue
        
        # Adeg-adeg appearing standalone (edge case — skip)
        if char == BALI_ADEG_ADEG:
            i += 1
            continue
        
        # Vowel signs appearing standalone (edge case)
        if char in BALI_VOWEL_SIGNS:
            trans += BALI_VOWEL_SIGNS[char]
            i += 1
            continue
        
        # Unrecognized — pass through
        trans += char
        i += 1
    
    # Phonotactic adjustment: nya before ja or ca becomes n in Latin script
    trans = trans.replace('nyj', 'nj')
    trans = trans.replace('nyc', 'nc')
    
    return trans

async def explain_text(text: str, context: str = "", native_lang: str = "English") -> str:
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
    
    IMPORTANT: First, identify the language of the target word/phrase. This could be ANY language — Japanese, Chinese, Arabic, Cyrillic, Devanagari, Balinese, Korean, Thai, Vietnamese, Indonesian, or any other. Adjust your analysis accordingly.
    
    Provide a direct, highly concise linguistic analysis for a language learner. 
    ALL explanations, meanings, synonyms, and antonyms MUST be provided in the user's native language: {native_lang}.
    Do NOT include any greetings, introductory phrases, or chatty sentences (e.g., do not say "Here is the analysis" or "I am yomu!"). Get straight to the analysis.
    
    Format the output EXACTLY like this:
    <strong>Language:</strong> [Detected language of the word/phrase]<br>
    <strong>Meaning:</strong> [Direct {native_lang} meaning, using the surrounding context for accuracy]<br>
    <strong>Reading:</strong> [Pronunciation/reading in the standard romanization system for this language, e.g. romaji for Japanese, pinyin for Chinese, transliteration for Arabic/Cyrillic/Devanagari, etc.]<br>
    <strong>Grammar:</strong> [Grammar/parts of speech breakdown relative to the context, in {native_lang}]<br>
    <strong>Synonyms:</strong> [2-3 relevant synonyms in original script, with parenthesized reading/pronunciation and rough {native_lang} meaning]<br>
    <strong>Antonyms:</strong> [1-2 relevant antonyms in original script, with parenthesized reading/pronunciation and rough {native_lang} meaning, if applicable]<br>
    <strong>Related Words:</strong> [1-2 other related vocabulary words with parenthesized reading/pronunciation and English meanings]<br>
    <strong>Usage Example:</strong> [Short example sentence using the target word/phrase]
    
    Keep the total response extremely brief (under 130 words).
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
