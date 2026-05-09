#!/bin/bash

BROWSER=$1

if [ -z "$BROWSER" ]; then
    echo "Usage: ./build.sh [chrome|firefox]"
    exit 1
fi

case $BROWSER in
    chrome)
        cp extension/manifest.chrome.json extension/manifest.json
        echo "✅ Prepared manifest for Chrome"
        ;;
    firefox)
        cp extension/manifest.firefox.json extension/manifest.json
        echo "✅ Prepared manifest for Firefox"
        ;;
    *)
        echo "❌ Unknown browser: $BROWSER"
        exit 1
        ;;
esac
