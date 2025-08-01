import os
import sys

# Try to import cairosvg for SVG to PNG conversion
try:
    import cairosvg
    CAIROSVG_AVAILABLE = True
except ImportError:
    CAIROSVG_AVAILABLE = False
    print("CairoSVG not available, trying alternative methods...")

# Try to import Pillow for image processing
try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    print("Pillow not available, trying alternative methods...")

# Try to import wand (ImageMagick wrapper) as another alternative
try:
    from wand.image import Image as WandImage
    WAND_AVAILABLE = True
except ImportError:
    WAND_AVAILABLE = False
    print("Wand (ImageMagick) not available, trying alternative methods...")

def convert_svg_to_png_with_cairosvg(svg_path, png_path):
    """Convert SVG to PNG using CairoSVG"""
    try:
        cairosvg.svg2png(url=svg_path, write_to=png_path)
        print(f"Successfully converted {svg_path} to {png_path} using CairoSVG")
        return True
    except Exception as e:
        print(f"Error converting with CairoSVG: {e}")
        return False

def convert_svg_to_png_with_wand(svg_path, png_path):
    """Convert SVG to PNG using Wand (ImageMagick)"""
    try:
        with WandImage(filename=svg_path) as img:
            img.format = 'png'
            img.save(filename=png_path)
        print(f"Successfully converted {svg_path} to {png_path} using Wand/ImageMagick")
        return True
    except Exception as e:
        print(f"Error converting with Wand: {e}")
        return False

def create_fallback_png(png_path, width=800, height=600, is_seal=False):
    """Create a simple fallback PNG when all conversion methods fail"""
    if not PILLOW_AVAILABLE:
        print("Cannot create fallback PNG: Pillow not available")
        return False
    
    try:
        # Create a simple gold-colored image as fallback
        if is_seal:
            # Create a circular seal
            img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
            # Draw a gold circle
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)
            center = width // 2
            radius = min(width, height) // 2 - 10
            # Gold color
            gold_color = (249, 212, 35, 255)
            draw.ellipse((center-radius, center-radius, center+radius, center+radius), fill=gold_color)
            # Save the image
            img.save(png_path, 'PNG')
        else:
            # Create a patterned background
            img = Image.new('RGBA', (width, height), (255, 255, 255, 255))
            # Add some gold-colored elements
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)
            # Gold color with transparency
            gold_color = (249, 212, 35, 100)
            # Draw some decorative elements
            for i in range(0, width, 100):
                draw.rectangle((i, 0, i+50, height), fill=gold_color)
            # Save the image
            img.save(png_path, 'PNG')
        
        print(f"Created fallback PNG at {png_path}")
        return True
    except Exception as e:
        print(f"Error creating fallback PNG: {e}")
        return False

def main():
    # Base directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    images_dir = os.path.join(base_dir, 'static', 'images')
    
    # SVG files to convert
    svg_files = [
        {'name': 'certificate-pattern.svg', 'width': 800, 'height': 600, 'is_seal': False},
        {'name': 'certificate_seal.svg', 'width': 200, 'height': 200, 'is_seal': True}
    ]
    
    for svg_file in svg_files:
        svg_path = os.path.join(images_dir, svg_file['name'])
        # Create PNG filename by replacing .svg with .png
        png_file = os.path.splitext(svg_file['name'])[0] + '.png'
        png_path = os.path.join(images_dir, png_file)
        
        if os.path.exists(svg_path):
            print(f"Converting {svg_file['name']} to PNG...")
            
            # Try conversion methods in order of preference
            success = False
            
            if CAIROSVG_AVAILABLE and not success:
                success = convert_svg_to_png_with_cairosvg(svg_path, png_path)
            
            if WAND_AVAILABLE and not success:
                success = convert_svg_to_png_with_wand(svg_path, png_path)
            
            # If all conversion methods fail, create a fallback PNG
            if not success:
                print("All conversion methods failed, creating fallback PNG...")
                create_fallback_png(png_path, svg_file['width'], svg_file['height'], svg_file['is_seal'])
        else:
            print(f"SVG file not found: {svg_path}")

if __name__ == "__main__":
    main()