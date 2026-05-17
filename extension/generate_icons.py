import os
import subprocess
import sys

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try:
    from PIL import Image
except ImportError:
    print("Pillow not found, installing...")
    install("Pillow")
    from PIL import Image

def generate_icons():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(base_dir)
    source_image_path = os.path.join(root_dir, "yomu-logo.png")
    icons_dir = os.path.join(base_dir, "icons")
    
    if not os.path.exists(source_image_path):
        print(f"Error: Could not find source image at {source_image_path}")
        return

    os.makedirs(icons_dir, exist_ok=True)
    
    sizes = [16, 48, 128]
    try:
        with Image.open(source_image_path) as img:
            # Force convert to RGBA to preserve transparency
            img = img.convert("RGBA")
            
            for size in sizes:
                # Use LANCZOS resampling for the highest quality downscaling
                resized_img = img.resize((size, size), Image.Resampling.LANCZOS)
                output_path = os.path.join(icons_dir, f"icon{size}.png")
                resized_img.save(output_path, "PNG")
                print(f"Successfully generated {output_path}")
    except Exception as e:
        print(f"Error processing image: {e}")

if __name__ == "__main__":
    generate_icons()
