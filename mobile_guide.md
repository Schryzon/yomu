# yōmu! Mobile Extension Guide

Supporting mobile users is a key part of yōmu!'s mission to make reading accessible everywhere. Here is how we bridge the gap for mobile browsers.

## 1. Safari for iOS
Apple allows web extensions to run on Safari for iPhone and iPad. 

### How to adapt:
1. **Convert with Xcode**: You can use the `xcrun safari-web-extension-converter` tool on a Mac to convert your existing extension folder into an Xcode project.
2. **Review UI**: Ensure the popup and settings pages use responsive CSS (which we've already started improving).
3. **Publish**: Distribute via the App Store.

## 2. Firefox for Android
Firefox is one of the few Android browsers that officially supports a curated list of extensions.

### How to adapt:
1. **Compatibility**: Most Chrome/Firefox desktop extensions work out of the box if they don't use complex window management.
2. **Manifest**: Use your existing `manifest.firefox.json`.
3. **Testing**: Test on an Android device with Firefox Nightly or the stable version if your extension is in the "Recommended" list.

## 3. PWA (Progressive Web App)
For users who cannot install extensions (like Chrome on Android), we provide the **Web Demo as a PWA**.

### Features enabled:
- **Offline Shell**: Instant interface loading via registered service workers (implemented).
- **Home Screen Icon**: Native OS installation via PWA manifest configuration (implemented).
- **Theming**: Integrated theme-color for a seamless standalone OS app experience.

## 4. Design Considerations
- **Touch Targets**: All interactive elements in the extension UI should be at least 44x44 pixels.
- **CPU Usage**: Be mindful of background processes on mobile to preserve battery life.
