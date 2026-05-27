// yomu! content script

// State
let widgetState = 'hidden'; // hidden, progress, ready, active
const widget = document.createElement('div');
widget.id = 'yomu-widget';
widget.innerText = 'yōmu!';

const tooltip = document.createElement('div');
tooltip.id = 'yomu-tooltip';
tooltip.style.display = 'none';

document.body.appendChild(widget);
document.body.appendChild(tooltip);


// Broad Regex for any alphabetic character from any target script (u flag required)
// Uses modern Unicode Property Escapes to completely and robustly match standard & extended blocks
// for Japanese (Hiragana/Katakana/Han), Chinese (Han), Arabic, Cyrillic (Russian), Devanagari (Hindi), and Balinese.
const TARGET_REGEX = /([\p{scx=Hiragana}\p{scx=Katakana}\p{scx=Han}\p{scx=Arabic}\p{scx=Cyrillic}\p{scx=Devanagari}\p{scx=Balinese}])/u;

// Helper to check if node is inside a ruby tag
function isInsideRuby(node) {
    let current = node.parentNode;
    while (current && current !== document.body) {
        if (current.tagName && current.tagName.toLowerCase() === 'ruby') {
            return true;
        }
        current = current.parentNode;
    }
    return false;
}

// Page-level language detection (multi-signal approach)
function detect_page_language() {
    // Signal 1: HTML lang attribute (strongest — set by the page itself)
    const html_lang = document.documentElement.lang?.toLowerCase() || '';
    if (html_lang.startsWith('ja')) return 'ja';
    if (html_lang.startsWith('zh')) return 'zh';
    if (html_lang.startsWith('ar')) return 'ar';
    if (html_lang.startsWith('ru')) return 'ru';
    if (html_lang.startsWith('hi')) return 'hi';

    // Signal 2: URL heuristics (e.g. ja.wikipedia.org, zh.m.wikipedia.org)
    const hostname = window.location.hostname;
    if (hostname.startsWith('ja.')) return 'ja';
    if (hostname.startsWith('zh.')) return 'zh';
    if (hostname.startsWith('ar.')) return 'ar';
    if (hostname.startsWith('ru.')) return 'ru';
    if (hostname.startsWith('hi.')) return 'hi';

    // Signal 3: Page-wide kana scan — if kana exists anywhere on the page, it's Japanese
    const body_text = document.body.innerText.substring(0, 5000);
    const has_kana = /[\u3040-\u309F\u30A0-\u30FF]/.test(body_text);
    const has_han = /[\u4E00-\u9FFF]/.test(body_text);
    if (has_kana && has_han) return 'ja';

    return 'auto'; // truly ambiguous — let backend decide
}

// Helper to safely parse and set HTML via DOMParser (bypassing innerHTML warnings)
function setSafeHTML(element, htmlString) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(htmlString, 'text/html');
    element.textContent = '';
    while (doc.body.firstChild) {
        element.appendChild(doc.body.firstChild);
    }
}

// Strict DOM Sanitizer for LLM outputs to prevent XSS
function setSafeAnnotationHTML(element, htmlString) {
    const ALLOWED_TAGS = ['ruby', 'rt', 'span', 'b', 'i', 'strong', 'em', 'br'];
    
    function sanitizeNode(node) {
        if (node.nodeType === Node.TEXT_NODE) {
            return document.createTextNode(node.textContent);
        }
        
        if (node.nodeType !== Node.ELEMENT_NODE) {
            return null;
        }
        
        const tagName = node.tagName.toLowerCase();
        if (!ALLOWED_TAGS.includes(tagName)) {
            // Instead of dropping it entirely, we could just extract its text, 
            // but for security it's safer to just return a text node of its content
            return document.createTextNode(node.textContent);
        }
        
        const cleanNode = document.createElement(tagName);
        
        // Only allow specific classes, drop all other attributes
        if (tagName === 'span' && node.hasAttribute('class')) {
            const classes = node.getAttribute('class');
            if (classes.includes('yomu-word')) {
                cleanNode.className = 'yomu-word';
                if (node.hasAttribute('data-word')) {
                    cleanNode.setAttribute('data-word', node.getAttribute('data-word'));
                }
            }
        }
        
        node.childNodes.forEach(child => {
            const cleanChild = sanitizeNode(child);
            if (cleanChild) {
                cleanNode.appendChild(cleanChild);
            }
        });
        
        return cleanNode;
    }

    const parser = new DOMParser();
    const doc = parser.parseFromString(htmlString, 'text/html');
    element.textContent = '';
    
    doc.body.childNodes.forEach(child => {
        const safeChild = sanitizeNode(child);
        if (safeChild) {
            element.appendChild(safeChild);
        }
    });
}

// 1. Dynamic Detection
function scanPage() {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
    let node;
    const allTargetNodes = [];

    while ((node = walker.nextNode())) {
        const text = node.nodeValue.trim();

        // Check if text contains any letter-like characters and isn't already inside a ruby tag
        if (text.length > 0 && TARGET_REGEX.test(text) && !isInsideRuby(node)) {
            allTargetNodes.push(node);
        }
    }

    if (allTargetNodes.length > 0) {
        console.log(`yōmu! found ${allTargetNodes.length} target nodes document-wide.`);

        // Process in chunks to avoid overwhelming the backend/API
        const CHUNK_SIZE = 50;
        for (let i = 0; i < allTargetNodes.length; i += CHUNK_SIZE) {
            const chunk = allTargetNodes.slice(i, i + CHUNK_SIZE);
            startProcessing(chunk);
        }
    }
}

// 2. Process with Backend
function startProcessing(nodes) {
    widgetState = 'progress';
    widget.className = 'yomu-progress';
    widget.innerText = 'yōmu!'; // Keep the text for the pulsating gray state

    widget.style.display = 'flex';

    console.log(`yōmu! found ${nodes.length} target nodes. Batch processing...`);

    // BATCHING: Join all text nodes with a safe delimiter to avoid API rate limits
    const DELIMITER = "\n|||\n";
    const batchText = nodes.map(n => n.nodeValue).join(DELIMITER);

    const page_lang = detect_page_language();

    chrome.runtime.sendMessage({
        action: 'process_text',
        payload: { text: batchText, page_lang: page_lang }
    }, (response) => {
        if (response && response.status === 'success' && response.data.annotated_html) {
            // Split the response back into array
            const annotatedParts = response.data.annotated_html.split("|||");

            nodes.forEach((node, index) => {
                if (index < annotatedParts.length) {
                    let annotatedText = annotatedParts[index].trim();
                    // Only replace if it actually contains ruby tags to avoid unnecessary DOM updates
                    if (annotatedText && annotatedText.includes('<ruby>')) {
                        const span = document.createElement('span');
                        span.className = 'yomu-annotated';
                        setSafeAnnotationHTML(span, annotatedText);

                        // Add click listener for Deep Analysis on specific words
                        span.addEventListener('click', (e) => {
                            const targetNode = e.target.closest('.yomu-word') || e.target.closest('ruby');
                            if (targetNode) {
                                e.stopPropagation();
                                const clickedWord = targetNode.getAttribute('data-word') || targetNode.textContent.trim();
                                showExplanation(clickedWord, targetNode);
                            }
                        });

                        if (node.parentNode) {
                            node.parentNode.replaceChild(span, node);
                        }

                    }
                }
            });
        }

        setReadyState();
    });
}

// 3. Activation & Subtlety
function setReadyState() {
    widgetState = 'ready';
    widget.className = 'yomu-ready';
    widget.innerText = 'yōmu!';

}

function createRipple(x, y) {
    const ripple = document.createElement('div');
    ripple.className = 'yomu-ripple';

    // Position ripple based on click coordinates
    ripple.style.left = `${x - 24}px`; // center on widget (48/2)
    ripple.style.top = `${y - 24}px`;

    document.body.appendChild(ripple);

    // Remove ripple after animation (matches 0.8s CSS duration)
    setTimeout(() => {
        ripple.remove();
    }, 800);
}

widget.addEventListener('click', (e) => {
    if (widgetState === 'ready') {
        // Activate
        widgetState = 'active';
        widget.className = 'yomu-active';
        createRipple(e.clientX, e.clientY);
        document.body.classList.add('yomu-active-annotations');
    } else if (widgetState === 'active') {
        // Deactivate
        widgetState = 'ready';
        widget.className = 'yomu-ready';
        document.body.classList.remove('yomu-active-annotations');
    }
});

// 4. Deep Analysis (Gemini Integration)
function escapeHTML(str) {
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function sanitizeHTML(str) {
    const escaped = escapeHTML(str);
    
    // Allow only specific safe formatting tags
    return escaped
        .replace(/&lt;br&gt;/g, '<br>')
        .replace(/&lt;b&gt;/g, '<b>')
        .replace(/&lt;\/b&gt;/g, '</b>')
        .replace(/&lt;strong&gt;/g, '<strong>')
        .replace(/&lt;\/strong&gt;/g, '</strong>')
        .replace(/&lt;i&gt;/g, '<i>')
        .replace(/&lt;\/i&gt;/g, '</i>')
        .replace(/&lt;em&gt;/g, '<em>')
        .replace(/&lt;\/em&gt;/g, '</em>');
}

function showExplanation(text, anchorElement) {
    const rect = anchorElement.getBoundingClientRect();
    tooltip.style.left = `${rect.left + window.scrollX}px`;
    tooltip.style.top = `${rect.bottom + window.scrollY + 10}px`;
    tooltip.style.display = 'block';
    setSafeHTML(tooltip, `
        <div style="display: flex; align-items: center; gap: 12px; padding: 4px 0;">
            <div style="
                width: 18px;
                height: 18px;
                border: 2px solid rgba(129, 140, 248, 0.15);
                border-top-color: #818cf8;
                border-radius: 50%;
                animation: yomu-spin 0.8s linear infinite;
                flex-shrink: 0;
            "></div>
            <div style="font-size: 0.85rem; opacity: 0.85; font-weight: 700; color: #818cf8; letter-spacing: 0.5px;">yōmu! is analyzing...</div>
        </div>
    `);

    // Extract surrounding paragraph/sentence context for the linguistic engine
    const parentBlock = anchorElement.closest('p, div, li, td, h1, h2, h3, h4, h5, h6, blockquote') || anchorElement.parentNode;
    const surroundingContext = parentBlock ? parentBlock.textContent.trim().substring(0, 500) : "";
    const combinedContext = `[Page Title: ${document.title}] Surrounding text: "${surroundingContext}"`;

    chrome.storage.sync.get({ nativeLang: 'English' }, (result) => {
        chrome.runtime.sendMessage({
            action: 'explain_text',
            payload: { text: text, context: combinedContext, native_lang: result.nativeLang }
        }, (response) => {
            if (response && response.status === 'success') {
                const safeExplanation = sanitizeHTML(response.data.explanation);
                setSafeHTML(tooltip, `
                    <div style="font-weight: bold; color: #818cf8; margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px;">Deep Analysis (${result.nativeLang})</div>
                    <div style="line-height: 1.6;">${safeExplanation}</div>
                    <div style="margin-top: 12px; font-size: 0.7rem; opacity: 0.5; text-align: right;">Powered by Gemini Flash-latest</div>
                `);
            } else {
                setSafeHTML(tooltip, '<span style="color: #ef4444;">Analysis currently unavailable.</span>');
            }
        });
    });
}

// Close tooltip on outside click
document.addEventListener('click', (e) => {
    if (!tooltip.contains(e.target) && !e.target.classList.contains('yomu-annotated')) {
        tooltip.style.display = 'none';
    }
});


// 5. Dynamic Content & Theme Detection
let scanTimeout;

function detectTheme() {
    const bodyStyle = window.getComputedStyle(document.body);
    let bgColor = bodyStyle.backgroundColor;
    if (bgColor === 'rgba(0, 0, 0, 0)' || bgColor === 'transparent') {
        bgColor = window.getComputedStyle(document.documentElement).backgroundColor;
    }
    const rgb = bgColor.match(/\d+/g);
    if (!rgb || rgb.length < 3) return 'dark';
    const brightness = (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255;
    return brightness > 0.5 ? 'light' : 'dark';
}

function updateThemeColors() {
    const theme = detectTheme();
    const rtColor = theme === 'light' ? '#4f46e5' : '#2dd4bf';
    document.documentElement.style.setProperty('--yomu-rt-color', rtColor);
    
    if (theme === 'light') {
        widget.classList.add('yomu-page-light');
        widget.classList.remove('yomu-page-dark');
    } else {
        widget.classList.add('yomu-page-dark');
        widget.classList.remove('yomu-page-light');
    }
    console.log(`yōmu! theme: ${theme}`);
}

let isExtensionEnabled = true;

const observer = new MutationObserver((mutations) => {
    if (!isExtensionEnabled) return;
    clearTimeout(scanTimeout);
    scanTimeout = setTimeout(() => {
        const hasRelevantChanges = mutations.some(m => {
            if (m.addedNodes.length > 0) return true;
            if (m.type === 'characterData') {
                return !m.target.parentElement?.closest('.yomu-annotated');
            }
            return false;
        });
        
        if (hasRelevantChanges) {
            console.log("yōmu! scanning procedural content...");
            scanPage();
        }
    }, 2000);
});

function stripAnnotations() {
    const annotatedNodes = document.querySelectorAll('span.yomu-annotated');
    annotatedNodes.forEach(span => {
        // yomu-annotated > span.yomu-word > ruby
        // The original text was just the base text of the ruby.
        // Easiest is to extract the text from the ruby, ignoring rt.
        const rubyTags = span.querySelectorAll('ruby');
        if (rubyTags.length > 0) {
            let originalText = '';
            span.childNodes.forEach(child => {
                if (child.tagName && child.tagName.toLowerCase() === 'span' && child.classList.contains('yomu-word')) {
                    const ruby = child.querySelector('ruby');
                    if (ruby) {
                        // Get base text by cloning and removing rt
                        const clone = ruby.cloneNode(true);
                        const rt = clone.querySelector('rt');
                        if (rt) rt.remove();
                        originalText += clone.textContent;
                    }
                } else {
                    originalText += child.textContent;
                }
            });
            const textNode = document.createTextNode(originalText);
            span.parentNode.replaceChild(textNode, span);
        }
    });
    
    widget.style.display = 'none';
    widgetState = 'hidden';
    widget.className = '';
    document.body.classList.remove('yomu-active-annotations');
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'toggle_yomu') {
        isExtensionEnabled = request.enabled;
        if (isExtensionEnabled) {
            scanPage();
        } else {
            stripAnnotations();
        }
    }
});

window.addEventListener('load', () => {
    chrome.storage.sync.get({ yomuEnabled: true }, (result) => {
        isExtensionEnabled = result.yomuEnabled;
        
        setTimeout(() => {
            updateThemeColors();
            if (isExtensionEnabled) {
                scanPage();
            }
            
            observer.observe(document.body, { 
                childList: true, 
                subtree: true, 
                characterData: true 
            });
            
            const themeObserver = new MutationObserver(updateThemeColors);
            themeObserver.observe(document.body, { 
                attributes: true, 
                attributeFilter: ['class', 'style'] 
            });
        }, 1000);
    });
});

