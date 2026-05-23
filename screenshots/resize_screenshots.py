import os
import glob
from PIL import Image

def process_images():
    # We will aim for 1280x800, which is the high-res standard for Chrome Web Store.
    TARGET_W = 1280
    TARGET_H = 800
    
    images = glob.glob("*.png") + glob.glob("*.jpg")
    
    for img_path in images:
        if "_store" in img_path:
            continue
            
        try:
            img = Image.open(img_path)
            orig_w, orig_h = img.size
            
            # Figure out scaling ratio so we don't stretch the image
            ratio = min(TARGET_W / orig_w, TARGET_H / orig_h)
            new_w = int(orig_w * ratio)
            new_h = int(orig_h * ratio)
            
            # Resize it cleanly
            resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # Create a 1280x800 transparent canvas
            # (Chrome handles transparent borders fine, or you could change (255,255,255,0) to a solid color)
            canvas = Image.new("RGBA", (TARGET_W, TARGET_H), (255, 255, 255, 0))
            
            # Calculate where to paste to center it
            offset_x = (TARGET_W - new_w) // 2
            offset_y = (TARGET_H - new_h) // 2
            
            canvas.paste(resized, (offset_x, offset_y))
            
            # Save it
            new_name = f"{os.path.splitext(img_path)[0]}_store.png"
            canvas.save(new_name, "PNG")
            
            print(f"Success: {img_path} ({orig_w}x{orig_h}) -> {new_name} ({TARGET_W}x{TARGET_H})")
            
        except Exception as e:
            print(f"Failed to process {img_path}: {e}")

if __name__ == "__main__":
    process_images()
