// yomu! content script

// State
let widgetState = 'hidden'; // hidden, progress, ready, active
const widget = document.createElement('div');
widget.id = 'yomu-widget';
widget.innerText = 'yō';
document.body.appendChild(widget);

// Regex for Japanese (Kanji/Hiragana/Katakana), Chinese (Hanzi), Arabic
const TARGET_REGEX = /[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF\u0600-\u06FF]/;

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
    let textNodesToProcess = [];

    while ((node = walker.nextNode())) {
        const text = node.nodeValue.trim();
        if (text.length > 0 && TARGET_REGEX.test(text) && !isInsideRuby(node)) {
            foundTargetText = true;
            textNodesToProcess.push(node);
        }
    }

    if (foundTargetText) {
        // For the hackathon, we'll process nodes in chunks to avoid overloading the API
        // but for now, we'll just demonstrate the first few meaningful ones
        startProcessing(textNodesToProcess.slice(0, 5)); 
    }
}

// 2. Process with Backend
function startProcessing(nodes) {
    widgetState = 'progress';
    widget.className = 'yomu-progress';
    widget.innerText = ''; // clear text for progress bar
    widget.style.display = 'flex';

    console.log(`yōmu! found ${nodes.length} target nodes. Processing...`);
    
    // Process each node (in a real app, we'd batch these better)
    let processedCount = 0;
    nodes.forEach(node => {
        const originalText = node.nodeValue;
        
        chrome.runtime.sendMessage({ 
            action: 'process_text', 
            payload: { text: originalText } 
        }, (response) => {
            processedCount++;
            
            if (response && response.status === 'success' && response.data.annotated_html) {
                if (node.parentNode) {
                    const span = document.createElement('span');
                    span.className = 'yomu-annotated';
                    span.innerHTML = response.data.annotated_html;
                    node.parentNode.replaceChild(span, node);
                }
            }

            if (processedCount === nodes.length) {
                setReadyState();
            }
        });
    });
}

// 3. Activation & Subtlety
function setReadyState() {
    widgetState = 'ready';
    widget.className = 'yomu-ready';
    widget.innerText = 'yō';
}

function createRipple(x, y) {
    const ripple = document.createElement('div');
    ripple.className = 'yomu-ripple';
    
    // Position ripple based on click coordinates
    ripple.style.left = `${x - 24}px`; // center on widget (48/2)
    ripple.style.top = `${y - 24}px`;
    
    document.body.appendChild(ripple);
    
    // Remove ripple after animation
    setTimeout(() => {
        ripple.remove();
    }, 500);
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

// Run detection on load
window.addEventListener('load', () => {
    setTimeout(scanPage, 1000);
});
