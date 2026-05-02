// yomu! background service worker
// Currently acts as a mock backend router

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'process_text') {
        console.log("yōmu! backend received text processing request", request.payload);
        
        // Mock processing delay to show progress bar
        setTimeout(() => {
            console.log("yōmu! backend finished processing");
            // In a real scenario, this would return the annotated HTML mapping.
            // For the skeleton, we just signal completion.
            sendResponse({ status: 'success', message: 'Text processed.' });
        }, 2000); 

        return true; // Keep message channel open for async response
    }
});
