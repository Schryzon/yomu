// yomu! content script

// State
let widgetState = 'hidden'; // hidden, progress, ready, active
const widget = document.createElement('div');
widget.id = 'yomu-widget';
widget.innerText = 'yōmu! (ヨォム)';

const tooltip = document.createElement('div');
tooltip.id = 'yomu-tooltip';
tooltip.style.display = 'none';

document.body.appendChild(widget);
document.body.appendChild(tooltip);


// Regex for Japanese, Chinese, Arabic, Russian, and Hindi (Devanagari)
const TARGET_REGEX = /[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF\u0600-\u06FF\u0400-\u04FF\u0900-\u097F]/;



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
    let foundTargetText = false;
    const blockTags = new Set(['p', 'div', 'article', 'section', 'main', 'li', 'blockquote', 'td']);
    const blocks = new Map();

    while ((node = walker.nextNode())) {
        const text = node.nodeValue.trim();

        if (text.length > 0 && TARGET_REGEX.test(text) && !isInsideRuby(node)) {
            // Find the closest block-level container
            let block = node.parentNode;
            while (block && block !== document.body) {
                if (block.tagName && blockTags.has(block.tagName.toLowerCase())) {
                    break;
                }
                block = block.parentNode;
            }
            if (!block) block = document.body;

            if (!blocks.has(block)) {
                blocks.set(block, { length: 0, nodes: [] });
            }
            blocks.get(block).length += text.length;
            blocks.get(block).nodes.push(node);
            foundTargetText = true;
        }
    }

    if (foundTargetText) {
        // Find the block container with the most Japanese text (this is almost always the main article/description!)
        let bestBlock = null;
        let maxLength = 0;
        for (const blockData of blocks.values()) {
            if (blockData.length > maxLength) {
                maxLength = blockData.length;
                bestBlock = blockData;
            }
        }
        
        // Process up to 20 text nodes from the winning block
        startProcessing(bestBlock.nodes.slice(0, 20)); 
    }
}

// 2. Process with Backend
function startProcessing(nodes) {
    widgetState = 'progress';
    widget.className = 'yomu-progress';
    widget.innerText = 'yōmu! (ヨォム)'; // Keep the text for the pulsating gray state

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
    widget.innerText = 'yōmu! (ヨォム)';

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
function showExplanation(text, anchorElement) {
    const rect = anchorElement.getBoundingClientRect();
    tooltip.style.left = `${rect.left + window.scrollX}px`;
    tooltip.style.top = `${rect.bottom + window.scrollY + 10}px`;
    tooltip.style.display = 'block';
    tooltip.innerHTML = '<em>Analyzing with Gemini...</em>';

    chrome.runtime.sendMessage({
        action: 'explain_text',
        payload: { text: text, context: document.title }
    }, (response) => {
        if (response && response.status === 'success') {
            tooltip.innerHTML = `
                <div style="font-weight: bold; color: #60a5fa; margin-bottom: 5px;">Deep Analysis</div>
                <div>${response.data.explanation}</div>
                <div style="margin-top: 10px; font-size: 0.7rem; opacity: 0.6; text-align: right;">Powered by Gemini 2.0 Flash</div>

            `;
        } else {
            tooltip.innerHTML = '<span style="color: #ef4444;">Error generating analysis.</span>';
        }
    });
}

// Close tooltip on outside click
document.addEventListener('click', (e) => {
    if (!tooltip.contains(e.target) && !e.target.classList.contains('yomu-annotated')) {
        tooltip.style.display = 'none';
    }
});


// 5. Dynamic Content (MutationObserver)
let scanTimeout;
const observer = new MutationObserver((mutations) => {
    // Debounce scanning to avoid performance hits
    clearTimeout(scanTimeout);
    scanTimeout = setTimeout(() => {
        // Only scan if new text nodes might have been added
        const hasNewContent = mutations.some(m => m.addedNodes.length > 0);
        if (hasNewContent) {
            console.log("yōmu! detecting new content...");
            scanPage();
        }
    }, 2000);
});

// Run detection on load and start observing
window.addEventListener('load', () => {
    setTimeout(() => {
        scanPage();
        observer.observe(document.body, { childList: true, subtree: true });
    }, 1000);
});

