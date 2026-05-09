import sys
import shutil
import os

def build(browser):
    extension_dir = "extension"
    target_manifest = os.path.join(extension_dir, "manifest.json")
    
    if browser == "chrome":
        source_manifest = os.path.join(extension_dir, "manifest.chrome.json")
    elif browser == "firefox":
        source_manifest = os.path.join(extension_dir, "manifest.firefox.json")
    else:
        print("❌ Unknown browser. Use 'chrome' or 'firefox'.")
        return

    if not os.path.exists(source_manifest):
        print(f"❌ Source manifest not found: {source_manifest}")
        return

    try:
        shutil.copy2(source_manifest, target_manifest)
        print(f"✅ Successfully prepared manifest for {browser.capitalize()}.")
        print(f"📍 Updated: {target_manifest}")
    except Exception as e:
        print(f"❌ Error during build: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python build_ext.py [chrome|firefox]")
    else:
        build(sys.argv[1].lower())
