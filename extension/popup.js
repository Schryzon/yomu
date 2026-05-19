    const scanBtn = document.getElementById('scan-now');
    const statusText = document.getElementById('status-text');

    scanBtn.addEventListener('click', () => {
    scanBtn.disabled = true;
    scanBtn.innerText = 'Scanning...';

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
    
    const setStatus = (text) => {
        statusText.textContent = '';
        const dot = document.createElement('div');
        dot.className = 'status-dot';
        statusText.appendChild(dot);
        statusText.appendChild(document.createTextNode(' ' + text));
    };

    setStatus('Scanning for new text...');
    
    setTimeout(() => {
        scanBtn.disabled = false;
        scanBtn.innerText = 'Re-scan Page';
        setStatus('Ready to enhance your reading.');
    }, 2000);
});

document.getElementById('open-demo').addEventListener('click', () => {
    chrome.tabs.create({ url: 'https://yomu-447937177163.asia-southeast2.run.app/' });
});
