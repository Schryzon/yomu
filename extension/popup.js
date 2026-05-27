document.addEventListener('DOMContentLoaded', () => {
    const scanBtn = document.getElementById('scan-now');
    const statusText = document.getElementById('status-text');
    const yomuToggle = document.getElementById('yomu-toggle');
    const nativeLangSelect = document.getElementById('native-lang');

    // Load saved settings
    chrome.storage.sync.get({ yomuEnabled: true, nativeLang: 'English' }, (result) => {
        yomuToggle.checked = result.yomuEnabled;
        if (result.nativeLang) {
            nativeLangSelect.value = result.nativeLang;
        }
    });

    // Save toggle state and notify active tab
    yomuToggle.addEventListener('change', (e) => {
        const isEnabled = e.target.checked;
        chrome.storage.sync.set({ yomuEnabled: isEnabled });
        
        // Notify content script in active tab
        chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
            chrome.tabs.sendMessage(tabs[0].id, { action: 'toggle_yomu', enabled: isEnabled });
        });
    });

    // Save native language preference
    nativeLangSelect.addEventListener('change', (e) => {
        chrome.storage.sync.set({ nativeLang: e.target.value });
    });

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
});
