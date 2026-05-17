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


// Broad Regex for any alphabetic character from any script (u flag required)
// Updated to explicitly match Japanese, Chinese, Arabic, Cyrillic, Devanagari, and Balinese scripts.
// This prevents the widget from auto-appearing on purely Latin/English websites.
const TARGET_REGEX = /([\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF\u0600-\u06FF\u0400-\u04FF\u0900-\u097F\u1B00-\u1B7F])/u;

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

    chrome.runtime.sendMessage({
        action: 'process_text',
        payload: { text: batchText }
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
                        span.innerHTML = annotatedText;

                        // Add click listener for Deep Analysis
                        span.addEventListener('click', (e) => {
                            e.stopPropagation();
                            showExplanation(node.nodeValue, span);
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
function sanitizeHTML(str) {
    const temp = document.createElement('div');
    temp.textContent = str;
    let sanitized = temp.innerHTML;
    
    // Allow only specific safe formatting tags
    return sanitized
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
    tooltip.innerHTML = '<div style="font-style: italic; opacity: 0.7;">yōmu! is analyzing...</div>';

    chrome.runtime.sendMessage({
        action: 'explain_text',
        payload: { text: text, context: document.title }
    }, (response) => {
        if (response && response.status === 'success') {
            const safeExplanation = sanitizeHTML(response.data.explanation);
            tooltip.innerHTML = `
                <div style="font-weight: bold; color: #818cf8; margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px;">Deep Analysis</div>
                <div style="line-height: 1.6;">${safeExplanation}</div>
                <div style="margin-top: 12px; font-size: 0.7rem; opacity: 0.5; text-align: right;">Powered by Gemini Flash-latest</div>
            `;
        } else {
            tooltip.innerHTML = '<span style="color: #ef4444;">Analysis currently unavailable.</span>';
        }
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
    console.log(`yōmu! theme: ${theme}`);
}

const observer = new MutationObserver((mutations) => {
    clearTimeout(scanTimeout);
    scanTimeout = setTimeout(() => {
        const hasRelevantChanges = mutations.some(m => {
            if (m.addedNodes.length > 0) return true;
            if (m.type === 'characterData') {
                // Ignore if the change happened inside a yomu annotation
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

window.addEventListener('load', () => {
    setTimeout(() => {
        updateThemeColors();
        scanPage();
        
        // Watch for structure changes AND text content changes
        observer.observe(document.body, { 
            childList: true, 
            subtree: true, 
            characterData: true 
        });
        
        // Watch for theme toggles
        const themeObserver = new MutationObserver(updateThemeColors);
        themeObserver.observe(document.body, { 
            attributes: true, 
            attributeFilter: ['class', 'style'] 
        });
    }, 1000);
});

