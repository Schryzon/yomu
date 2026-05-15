# yōmu! Browser Extension

The yōmu! extension is a Manifest V3 reading layer that seamlessly integrates with any website.

## Overview
The extension operates in several phases:
1. **Detection**: Scans the DOM for foreign scripts using a broad Unicode-aware regex (`\p{L}/u`).
2. **Batching**: Collects text nodes and sends them in chunks to the backend to ensure performance and stability.
3. **Injection**: Wraps target text in `<ruby>` tags with the pronunciation guides returned by the API.
4. **Analysis**: Provides a "Deep Analysis" tooltip powered by Gemini 2.0 when an annotated word is clicked.

## Key Files
- `manifest.json`: Configuration for the extension permissions and scripts.
- `content.js`: The primary engine that handles DOM scanning, theme detection, and procedural text updates.
- `styles.css`: Glassmorphic UI styles for the floating widget and annotations.
- `popup.html`: The control panel for the extension.

## Development
To load the extension in developer mode:
1. Open Chrome/Edge and go to `extensions://`.
2. Enable "Developer mode".
3. Click "Load unpacked" and select this directory.

#JuaraVibeCoding
