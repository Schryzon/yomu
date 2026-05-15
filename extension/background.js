// yomu! background service worker
// Connects the extension to the FastAPI backend

const BASE_URL = "https://yomu-447937177163.asia-southeast2.run.app/api";

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'process_text') {
        fetch(`${BASE_URL}/annotate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: request.payload.text,
                target_lang: 'auto'
            })
        })
        .then(response => response.json())
        .then(data => sendResponse({ status: 'success', data: data }))
        .catch(error => sendResponse({ status: 'error', message: error.message }));
        return true;
    }

    if (request.action === 'explain_text') {
        fetch(`${BASE_URL}/explain`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: request.payload.text,
                context: request.payload.context
            })
        })
        .then(response => response.json())
        .then(data => sendResponse({ status: 'success', data: data }))
        .catch(error => sendResponse({ status: 'error', message: error.message }));
        return true;
    }
});

