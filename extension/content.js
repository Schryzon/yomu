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
        startProcessing(textNodesToProcess);
    }
}

// 2. Auto-Process
function startProcessing(nodes) {
    widgetState = 'progress';
    widget.className = 'yomu-progress';
    widget.innerText = ''; // clear text for progress bar
    widget.style.display = 'flex';

    // Mock processing - replacing one node to show behavior
    // In reality, we'd send the text chunks to the backend
    console.log("yōmu! found target text. Processing in background...");
    
    chrome.runtime.sendMessage({ action: 'process_text', payload: { nodeCount: nodes.length } }, (response) => {
        if (response && response.status === 'success') {
            // Mock backend response handling: manually annotate one node for demonstration
            if (nodes.length > 0) {
                // Just for skeleton: wrap a random node with a mock ruby tag to test CSS
                const testNode = nodes[0];
                if (testNode.parentNode) {
                    const span = document.createElement('span');
                    span.className = 'yomu-annotated';
                    span.innerHTML = `<ruby>${testNode.nodeValue}<rt>よむ</rt></ruby>`;
                    testNode.parentNode.replaceChild(span, testNode);
                }
            }
            setReadyState();
        }
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
    // Small delay to allow dynamic content (like React/Vue) to render
    setTimeout(scanPage, 1000);
});
