document.getElementById('scan-now').addEventListener('click', () => {
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
        chrome.scripting.executeScript({
            target: {tabId: tabs[0].id},
            function: () => {
                if (typeof scanPage === 'function') {
                    scanPage();
                } else {
                    location.reload();
                }
            }
        });
    });
    document.getElementById('status-text').innerText = 'Scanning for new text...';
});

document.getElementById('open-demo').addEventListener('click', () => {
    chrome.tabs.create({ url: 'https://yomu-api-447937177163.asia-southeast2.run.app/' });
});
