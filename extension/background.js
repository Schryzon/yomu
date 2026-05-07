// yomu! background service worker
// Connects the extension to the FastAPI backend

const API_URL = "https://yomu-api-447937177163.asia-southeast2.run.app/api/annotate"; // Point to live Cloud Run service

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'process_text') {
        console.log("yōmu! processing request:", request.payload);

        fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: request.payload.text,
                target_lang: 'auto'
            })
        })
        .then(response => response.json())
        .then(data => {
            console.log("yōmu! backend responded:", data);
            sendResponse({ status: 'success', data: data });
        })
        .catch(error => {
            console.error("yōmu! backend error:", error);
            sendResponse({ status: 'error', message: error.message });
        });

        return true; // Keep message channel open for async response
    }
});
